// KADI LAN Multiplayer · servidor de señalización (ruta A) y base del host LAN (ruta B).
//
// Qué hace:
//   - Agrupa a los clientes por IP pública (mismo NAT = mismo WiFi) y juego. Nadie ve a quien esté en otro grupo.
//   - Cola 1v1 ("buscar rival"), invitaciones (aceptar, rechazar, cancelar, timeout) y salas con código.
//   - Relevo de SDP/ICE entre los dos jugadores emparejados (WebRTC DataChannel).
//   - Salida si WebRTC falla: relevo de los mensajes del juego por este mismo WebSocket.
//   - Límites: tamaño de mensaje, tasa por conexión, conexiones por IP, tamaño de grupo, intentos de código.
// No guarda nada en disco, no registra IPs y nunca las envía a otros clientes (el grupo es un HMAC con sal aleatoria).
// Dependencia única: ws. Node >= 20. Protocolo: references/protocolo.md.
import http from 'node:http';
import fs from 'node:fs';
import net from 'node:net';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

export const PROTOCOL_VERSION = 1;
const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // sin 0/O/1/I para que el código se dicte sin errores
const GAME_RE = /^[A-Za-z0-9._-]{1,48}$/;
const CODE_RE = /^[A-Z0-9]{5}$/;
const TYPES = new Set(['hello', 'bye', 'ping', 'queue', 'dequeue', 'invite', 'invite-cancel', 'invite-accept',
  'invite-decline', 'room-create', 'room-cancel', 'room-join', 'signal', 'relay-open', 'relay', 'leave-match']);

export const DEFAULTS = {
  port: 8787, host: '0.0.0.0',
  // Detrás de un proxy/CDN: trustProxy=true toma la IP real de clientIpHeader (la entrada número proxyHops contando desde el final).
  // originSecret: si se define, el proxy debe enviar x-origin-secret (el navegador no puede); /healthz queda abierto.
  trustProxy: false, proxyHops: 1, clientIpHeader: 'x-forwarded-for', originSecret: '', allowedOrigins: [],
  groupBy: 'ip',            // 'ip' = por red (ruta A); 'all' = todos en un grupo (ruta B: el host ya es la LAN)
  pin: '',                  // PIN opcional que debe enviar cada hello (ruta B)
  maxPeers: 2000, maxGroupSize: 32, maxConnsPerIp: 40,
  maxMessageBytes: 16384,   // tope de cualquier mensaje (ws cierra la conexión con 1009 si se excede)
  maxRelayBytes: 4096,      // tope del campo data de un relay
  ctlBurst: 20, ctlPerSec: 8, relayBurst: 120, relayPerSec: 60,
  queueTimeoutMs: 60000, inviteTimeoutMs: 20000, roomTtlMs: 300000, resumeGraceMs: 15000, helloTimeoutMs: 5000,
  heartbeatMs: 20000,
  codeFailLimit: 8, codeFailWindowMs: 60000,
  allowRemoteCandidates: false, // false descarta candidatos srflx/relay: solo viaja la IP de LAN (o su nombre mDNS)
  iceServers: [],               // [] = sin STUN/TURN: candidatos host, solo LAN
  relayOnly: false,             // true (ruta B): los emparejamientos nacen en modo relevo, sin WebRTC
  version: 'dev',
  httpHandler: null,            // (req, res) => true si lo atendió (lo usa el host LAN para servir la página del juego)
  hooks: null,                  // { onMatch(m, io), onRelayFrame(m, fromId, data, io) => bool, onPeerStatus(m, id, status, io), onMatchEnd(m, reason) }
  log: (...a) => console.log(...a),
};

// --- IP y grupos -------------------------------------------------------------------------------
export function normalizeIp(raw) {
  let ip = String(raw ?? '').trim().replace(/^\[|\]$/g, '').replace(/%.*$/, '');
  const mapped = ip.match(/^::ffff:(\d{1,3}(?:\.\d{1,3}){3})$/i);
  if (mapped) ip = mapped[1];
  return net.isIP(ip) ? ip.toLowerCase() : null;
}
function hextets(ip) { // IPv6 válida -> 8 enteros
  let v4 = null;
  const m = ip.match(/^(.*:)(\d+\.\d+\.\d+\.\d+)$/);
  if (m) { const p = m[2].split('.').map(Number); v4 = [(p[0] << 8) | p[1], (p[2] << 8) | p[3]]; ip = m[1] + '0:0'; }
  const [a, b] = ip.split('::');
  const head = a ? a.split(':') : [], tail = b === undefined ? [] : (b ? b.split(':') : []);
  const fill = b === undefined ? [] : Array(8 - head.length - tail.length).fill('0');
  const all = [...head, ...fill, ...tail].map(h => parseInt(h || '0', 16));
  if (v4) { all[6] = v4[0]; all[7] = v4[1]; }
  return all;
}
export function isPrivateIp(ip) {
  if (net.isIPv4(ip)) {
    const [a, b] = ip.split('.').map(Number);
    return a === 10 || a === 127 || a === 0 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 169 && b === 254);
  }
  if (net.isIPv6(ip)) { const h = hextets(ip); return ip === '::1' || (h[0] & 0xfe00) === 0xfc00 || (h[0] & 0xffc0) === 0xfe80; }
  return false;
}
// Clave de red: IPv4 pública exacta; IPv6 pública por /64 (los equipos de un mismo WiFi comparten prefijo);
// direcciones privadas = "priv" (el servidor está en la misma red privada que ellos).
export function networkKey(ip) {
  if (!ip) return 'unknown';
  if (isPrivateIp(ip)) return 'priv';
  if (net.isIPv6(ip)) return 'v6:' + hextets(ip).slice(0, 4).map(h => h.toString(16)).join(':');
  return 'v4:' + ip;
}
const safeEqual = (a, b) => {
  const x = Buffer.from(String(a ?? '')), y = Buffer.from(String(b ?? ''));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
};
const cleanAlias = (s, fallback) => {
  const t = String(s ?? '').replace(/[\u0000-\u001f\u007f<>]/g, '').replace(/\s+/g, ' ').trim().slice(0, 24);
  return t || fallback;
};

// --- servidor ----------------------------------------------------------------------------------
export async function createSignalingServer(userOptions = {}) {
  const o = { ...DEFAULTS, ...userOptions };
  const salt = crypto.randomBytes(16);
  const hex = (n = 8) => crypto.randomBytes(n).toString('hex');
  const gidOf = key => crypto.createHmac('sha256', salt).update(key).digest('hex').slice(0, 16);

  const peers = new Map(), byResume = new Map(), groups = new Map(), queues = new Map(), invites = new Map(),
    matches = new Map(), rooms = new Map(), connsByGid = new Map(), codeFails = new Map();
  let warnedProxy = false, closing = false;

  const send = (ws, obj) => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); };
  const to = (p, obj) => { if (p && p.ws) send(p.ws, obj); };
  const fail = (p, code, message, ref) => to(p, { type: 'error', code, message, ref });
  const brief = p => ({ id: p.id, alias: p.alias });
  const io = { sendTo(peerId, data) { const p = peers.get(peerId), m = p && matches.get(p.matchId); if (p && m) to(p, { type: 'relay', matchId: m.id, data }); } };
  const hook = (name, ...args) => { try { return o.hooks?.[name]?.(...args, io); } catch (e) { o.log('hook', name, e.message); } };

  function bucket(conn, kind) {
    const b = conn.buckets[kind], now = Date.now();
    b.tokens = Math.min(b.cap, b.tokens + (now - b.at) / 1000 * b.rate); b.at = now;
    if (b.tokens < 1) return false;
    b.tokens -= 1; return true;
  }
  const newBuckets = () => ({
    ctl: { cap: o.ctlBurst, rate: o.ctlPerSec, tokens: o.ctlBurst, at: Date.now() },
    rel: { cap: o.relayBurst, rate: o.relayPerSec, tokens: o.relayBurst, at: Date.now() },
  });

  // --- lista de rivales visibles ---
  const visibleState = p => (p.state === 'idle' || p.state === 'searching') ? p.state : 'busy';
  function pushPeers(gk) {
    const set = groups.get(gk);
    if (!set) return;
    for (const id of set) {
      const p = peers.get(id);
      if (!p || !p.ws) continue;
      const list = [];
      for (const oid of set) { const q = peers.get(oid); if (q && q.ws && q !== p) list.push({ id: q.id, alias: q.alias, state: visibleState(q) }); }
      to(p, { type: 'peers', peers: list });
    }
  }

  // --- cola ---
  function leaveQueue(p) {
    clearTimeout(p.queueTimer); p.queueTimer = null;
    const q = queues.get(p.gk);
    if (q) { const i = q.indexOf(p.id); if (i >= 0) q.splice(i, 1); if (!q.length) queues.delete(p.gk); }
    if (p.state === 'searching') p.state = 'idle';
  }
  function tryPair(gk) {
    const q = queues.get(gk);
    while (q && q.length >= 2) {
      const a = peers.get(q.shift()), b = peers.get(q.shift());
      if (a && a.state === 'searching' && b && b.state === 'searching') {
        clearTimeout(a.queueTimer); clearTimeout(b.queueTimer); a.queueTimer = b.queueTimer = null;
        createMatch(a, b, 'queue');
      } else { // alguno ya no estaba buscando: devuelve al válido y sigue
        for (const x of [a, b]) if (x && x.state === 'searching') q.unshift(x.id);
      }
    }
    if (q && !q.length) queues.delete(gk);
  }

  // --- invitaciones ---
  function endInvite(inv, reason) {
    if (!invites.delete(inv.id)) return;
    clearTimeout(inv.timer);
    const from = peers.get(inv.from), target = peers.get(inv.to);
    if (from && from.outInvite === inv.id) { from.outInvite = null; if (from.state === 'inviting') from.state = 'idle'; }
    if (target) target.inInvites.delete(inv.id);
    to(from, { type: 'invite-ended', inviteId: inv.id, reason });
    to(target, { type: 'invite-ended', inviteId: inv.id, reason });
    if (from) pushPeers(from.gk);
  }
  function dropInvitesOf(p, reason) {
    if (p.outInvite && invites.get(p.outInvite)) endInvite(invites.get(p.outInvite), reason);
    for (const id of [...p.inInvites]) { const inv = invites.get(id); if (inv) endInvite(inv, reason); }
  }

  // --- emparejamientos ---
  function createMatch(a, b, kind) {
    for (const p of [a, b]) { leaveQueue(p); dropInvitesOf(p, 'busy'); }
    const m = { id: hex(8), a: a.id, b: b.id, kind, relay: o.relayOnly, created: Date.now() };
    matches.set(m.id, m);
    for (const p of [a, b]) { p.state = 'matched'; p.matchId = m.id; }
    for (const [self, other, role] of [[a, b, 'host'], [b, a, 'guest']]) {
      to(self, { type: 'matched', matchId: m.id, role, kind, peer: brief(other), transport: m.relay ? 'relay' : 'p2p', iceServers: o.iceServers });
    }
    if (m.relay) for (const p of [a, b]) to(p, { type: 'relay-ready', matchId: m.id });
    pushPeers(a.gk); if (b.gk !== a.gk) pushPeers(b.gk);
    hook('onMatch', m);
    return m;
  }
  function endMatch(m, reason, byId) {
    if (!matches.delete(m.id)) return;
    for (const id of [m.a, m.b]) {
      const p = peers.get(id);
      if (!p) continue;
      p.matchId = null; if (p.state === 'matched') p.state = 'idle';
      to(p, { type: 'match-ended', matchId: m.id, reason: id === byId ? 'left' : reason });
    }
    hook('onMatchEnd', m, reason);
    for (const id of [m.a, m.b]) { const p = peers.get(id); if (p) pushPeers(p.gk); }
  }

  // --- conexión y ciclo de vida de peers ---
  function goOffline(p) {
    leaveQueue(p); dropInvitesOf(p, 'left');
    if (p.roomCode) closeRoom(p.roomCode, 'offline');
    if (p.state !== 'matched') p.state = 'idle';
    p.ws = null; p.conn = null;
    pushPeers(p.gk);
    const m = matches.get(p.matchId);
    if (m) {
      const other = peers.get(m.a === p.id ? m.b : m.a);
      to(other, { type: 'peer-status', matchId: m.id, status: 'offline' });
      hook('onPeerStatus', m, p.id, 'offline');
    }
    p.offlineTimer = setTimeout(() => removePeer(p, 'peer-lost'), o.resumeGraceMs);
  }
  function removePeer(p, reason = 'peer-left') {
    clearTimeout(p.offlineTimer); clearTimeout(p.queueTimer);
    leaveQueue(p); dropInvitesOf(p, 'left');
    if (p.roomCode) closeRoom(p.roomCode, 'offline');
    const m = matches.get(p.matchId);
    if (m) endMatch(m, reason, p.id);
    p.removed = true; peers.delete(p.id); byResume.delete(p.resume);
    if (p.conn) { p.conn.peer = null; p.conn = null; }
    const set = groups.get(p.gk);
    if (set) { set.delete(p.id); if (!set.size) groups.delete(p.gk); }
    if (p.ws) { try { p.ws.close(1000, 'bye'); } catch {} }
    pushPeers(p.gk);
  }

  function closeRoom(code, reason) {
    const r = rooms.get(code);
    if (!r) return;
    rooms.delete(code); clearTimeout(r.timer);
    const owner = peers.get(r.owner);
    if (owner) { owner.roomCode = null; if (owner.state === 'room') owner.state = 'idle'; to(owner, { type: 'room-closed', code, reason }); pushPeers(owner.gk); }
  }

  function codeLimited(gid) {
    const now = Date.now(), f = codeFails.get(gid);
    return !!f && f.until > now && f.n >= o.codeFailLimit;
  }
  function codeFailed(gid) {
    const now = Date.now(); let f = codeFails.get(gid);
    if (!f || f.until <= now) f = { n: 0, until: now + o.codeFailWindowMs };
    f.n++; codeFails.set(gid, f);
    if (codeFails.size > 5000) for (const [k, v] of codeFails) if (v.until <= now) codeFails.delete(k);
  }

  // --- manejadores de mensajes ---
  const H = {
    hello(conn, m) {
      if (conn.peer) return;
      clearTimeout(conn.helloTimer);
      const bad = (code, message) => { send(conn.ws, { type: 'error', code, message, ref: 'hello' }); conn.ws.close(4400, code); };
      if (m.v !== undefined && m.v !== PROTOCOL_VERSION) return bad('bad-version', 'Versión de protocolo no soportada.');
      const game = String(m.game ?? '');
      if (!GAME_RE.test(game)) return bad('bad-game', 'Identificador de juego no válido.');
      if (o.pin) {
        if (codeLimited(conn.gid)) return bad('rate', 'Demasiados intentos. Espera un minuto.');
        if (!safeEqual(m.pin, o.pin)) { codeFailed(conn.gid); return bad('bad-pin', 'PIN incorrecto.'); }
      }
      const gk = (o.groupBy === 'all' ? 'all' : conn.gid) + '|' + game;
      const old = typeof m.resume === 'string' ? byResume.get(m.resume) : null;
      if (old && old.ws === null && old.gk === gk) { // reanuda: conserva id, emparejamiento y estado
        clearTimeout(old.offlineTimer); old.offlineTimer = null;
        old.ws = conn.ws; old.conn = conn; conn.peer = old;
        const mt = matches.get(old.matchId);
        send(conn.ws, { type: 'welcome', v: PROTOCOL_VERSION, id: old.id, resume: old.resume, alias: old.alias, resumed: true, state: old.state,
          iceServers: o.iceServers, relayOnly: o.relayOnly, limits: limits(),
          match: mt ? { matchId: mt.id, role: mt.a === old.id ? 'host' : 'guest', peer: brief(peers.get(mt.a === old.id ? mt.b : mt.a) || { id: '', alias: '' }), transport: mt.relay ? 'relay' : 'p2p' } : null });
        if (mt) {
          const other = peers.get(mt.a === old.id ? mt.b : mt.a);
          to(other, { type: 'peer-status', matchId: mt.id, status: 'online' });
          hook('onPeerStatus', mt, old.id, 'online');
        }
        return pushPeers(old.gk);
      }
      const set = groups.get(gk) || new Set();
      if (set.size >= o.maxGroupSize) return bad('group-full', 'Hay demasiados jugadores en esta red.');
      const id = hex(8);
      const p = { id, resume: hex(16), ws: conn.ws, conn, alias: cleanAlias(m.alias, 'Jugador-' + id.slice(0, 4)), game, gid: conn.gid, gk,
        state: 'idle', matchId: null, outInvite: null, inInvites: new Set(), roomCode: null, queueTimer: null, offlineTimer: null };
      conn.peer = p; peers.set(id, p); byResume.set(p.resume, p); set.add(id); groups.set(gk, set);
      send(conn.ws, { type: 'welcome', v: PROTOCOL_VERSION, id, resume: p.resume, alias: p.alias, resumed: false, state: 'idle',
        groupSize: set.size, iceServers: o.iceServers, relayOnly: o.relayOnly, limits: limits() });
      pushPeers(gk);
    },
    bye(conn) { if (conn.peer) removePeer(conn.peer); },
    ping(conn, m) { send(conn.ws, { type: 'pong', t: m.t }); },
    queue(conn) {
      const p = conn.peer;
      if (p.state === 'searching') return;
      if (p.state !== 'idle') return fail(p, 'busy', 'Ya estás ocupado.', 'queue');
      p.state = 'searching';
      (queues.get(p.gk) || queues.set(p.gk, []).get(p.gk)).push(p.id);
      p.queueTimer = setTimeout(() => {
        if (p.state !== 'searching') return;
        leaveQueue(p); to(p, { type: 'queue-ended', reason: 'timeout' }); pushPeers(p.gk);
      }, o.queueTimeoutMs);
      to(p, { type: 'queued', timeoutMs: o.queueTimeoutMs });
      pushPeers(p.gk); tryPair(p.gk);
    },
    dequeue(conn) {
      const p = conn.peer;
      if (p.state !== 'searching') return;
      leaveQueue(p); to(p, { type: 'queue-ended', reason: 'cancelled' }); pushPeers(p.gk);
    },
    invite(conn, m) {
      const p = conn.peer, t = peers.get(String(m.to ?? ''));
      const refuse = reason => to(p, { type: 'invite-ended', inviteId: null, reason });
      if (p.state !== 'idle' && p.state !== 'searching') return refuse('busy');
      if (!t || t.ws === null || t.gk !== p.gk) return refuse('not-found');
      if (t === p) return refuse('self');
      if ((t.state !== 'idle' && t.state !== 'searching') || t.inInvites.size >= 4) return refuse('busy');
      if (p.state === 'searching') { leaveQueue(p); to(p, { type: 'queue-ended', reason: 'invite' }); }
      const inv = { id: hex(6), from: p.id, to: t.id, timer: null };
      inv.timer = setTimeout(() => endInvite(inv, 'timeout'), o.inviteTimeoutMs);
      invites.set(inv.id, inv); p.state = 'inviting'; p.outInvite = inv.id; t.inInvites.add(inv.id);
      to(p, { type: 'invite-sent', inviteId: inv.id, to: brief(t), timeoutMs: o.inviteTimeoutMs });
      to(t, { type: 'invited', inviteId: inv.id, from: brief(p), timeoutMs: o.inviteTimeoutMs });
      pushPeers(p.gk);
    },
    'invite-cancel'(conn) {
      const p = conn.peer, inv = invites.get(p.outInvite);
      if (inv) endInvite(inv, 'cancelled');
    },
    'invite-accept'(conn, m) {
      const t = conn.peer, inv = invites.get(String(m.inviteId ?? ''));
      if (!inv || inv.to !== t.id) return fail(t, 'invite-gone', 'La invitación ya no existe.', 'invite-accept');
      if (t.state !== 'idle' && t.state !== 'searching') return fail(t, 'busy', 'Ya estás ocupado.', 'invite-accept');
      const from = peers.get(inv.from);
      invites.delete(inv.id); clearTimeout(inv.timer); t.inInvites.delete(inv.id);
      if (!from || !from.ws) return fail(t, 'invite-gone', 'El rival ya no está.', 'invite-accept');
      from.outInvite = null; from.state = 'idle'; // createMatch lo pasa a "matched"
      createMatch(from, t, 'invite');
    },
    'invite-decline'(conn, m) {
      const inv = invites.get(String(m.inviteId ?? ''));
      if (inv && inv.to === conn.peer.id) endInvite(inv, 'declined');
    },
    'room-create'(conn) {
      const p = conn.peer;
      if (p.state !== 'idle') return fail(p, 'busy', 'Ya estás ocupado.', 'room-create');
      let code = '';
      for (let tries = 0; tries < 50 && (!code || rooms.has(code)); tries++) { code = ''; for (let i = 0; i < 5; i++) code += ALPHABET[crypto.randomInt(ALPHABET.length)]; }
      if (rooms.has(code)) return fail(p, 'full', 'No hay códigos libres.', 'room-create');
      const r = { code, owner: p.id, game: p.game, timer: setTimeout(() => closeRoom(code, 'timeout'), o.roomTtlMs) };
      rooms.set(code, r); p.state = 'room'; p.roomCode = code;
      to(p, { type: 'room-created', code, ttlMs: o.roomTtlMs }); pushPeers(p.gk);
    },
    'room-cancel'(conn) { if (conn.peer.roomCode) closeRoom(conn.peer.roomCode, 'cancelled'); },
    'room-join'(conn, m) {
      const p = conn.peer, code = String(m.code ?? '').toUpperCase();
      if (p.state !== 'idle' && p.state !== 'searching') return fail(p, 'busy', 'Ya estás ocupado.', 'room-join');
      if (codeLimited(p.gid)) return fail(p, 'rate', 'Demasiados códigos incorrectos. Espera un minuto.', 'room-join');
      const r = CODE_RE.test(code) ? rooms.get(code) : null, owner = r && peers.get(r.owner);
      if (!r || !owner || !owner.ws || owner === p || r.game !== p.game) { codeFailed(p.gid); return fail(p, 'room-not-found', 'La sala no existe o ya expiró.', 'room-join'); }
      rooms.delete(code); clearTimeout(r.timer); owner.roomCode = null; owner.state = 'idle';
      createMatch(owner, p, 'room');
    },
    signal(conn, m) {
      const p = conn.peer, mt = matches.get(String(m.matchId ?? ''));
      if (!mt || (mt.a !== p.id && mt.b !== p.id)) return fail(p, 'no-match', 'Emparejamiento no válido.', 'signal');
      if (o.relayOnly) return fail(p, 'relay-only', 'Este servidor solo usa relevo.', 'signal');
      const kind = m.kind, d = m.data;
      if (!['offer', 'answer', 'ice'].includes(kind) || !d || typeof d !== 'object') return fail(p, 'bad-signal', 'Señal no válida.', 'signal');
      if (kind === 'ice') {
        if (typeof d.candidate !== 'string' || d.candidate.length > 600) return fail(p, 'bad-signal', 'Candidato no válido.', 'signal');
        if (!o.allowRemoteCandidates && / typ (srflx|relay|prflx)\b/.test(d.candidate)) return; // no filtra IP pública ni de relevo
      } else if (d.type !== kind || typeof d.sdp !== 'string' || d.sdp.length > 12000) return fail(p, 'bad-signal', 'SDP no válido.', 'signal');
      to(peers.get(mt.a === p.id ? mt.b : mt.a), { type: 'signal', matchId: mt.id, from: p.id, kind, data: d });
    },
    'relay-open'(conn, m) {
      const p = conn.peer, mt = matches.get(String(m.matchId ?? ''));
      if (!mt || (mt.a !== p.id && mt.b !== p.id)) return fail(p, 'no-match', 'Emparejamiento no válido.', 'relay-open');
      mt.relay = true;
      for (const id of [mt.a, mt.b]) to(peers.get(id), { type: 'relay-ready', matchId: mt.id });
    },
    relay(conn, m) {
      const p = conn.peer, mt = matches.get(String(m.matchId ?? ''));
      if (!mt || (mt.a !== p.id && mt.b !== p.id)) return fail(p, 'no-match', 'Emparejamiento no válido.', 'relay');
      if (!mt.relay) return fail(p, 'relay-closed', 'El relevo no está abierto.', 'relay');
      if (m.data === undefined || JSON.stringify(m.data).length > o.maxRelayBytes) return fail(p, 'too-big', 'Mensaje demasiado grande.', 'relay');
      if (hook('onRelayFrame', mt, p.id, m.data) === true) return;
      const other = peers.get(mt.a === p.id ? mt.b : mt.a);
      if (other && other.ws && other.ws.bufferedAmount < 1 << 20) to(other, { type: 'relay', matchId: mt.id, data: m.data });
    },
    'leave-match'(conn, m) {
      const mt = matches.get(String(m.matchId ?? ''));
      if (mt && (mt.a === conn.peer.id || mt.b === conn.peer.id)) endMatch(mt, 'peer-left', conn.peer.id);
    },
  };
  const limits = () => ({ maxMessageBytes: o.maxMessageBytes, maxRelayBytes: o.maxRelayBytes, queueTimeoutMs: o.queueTimeoutMs, inviteTimeoutMs: o.inviteTimeoutMs });

  function onMessage(conn, raw, isBinary) {
    if (isBinary) return conn.ws.close(1003, 'binary');
    let m;
    try { m = JSON.parse(raw.toString('utf8')); } catch { return strike(conn, 'bad-json'); }
    if (!m || typeof m !== 'object' || typeof m.type !== 'string' || !TYPES.has(m.type)) return strike(conn, 'bad-type');
    if (!conn.peer && m.type !== 'hello') return strike(conn, 'no-hello');
    if (!bucket(conn, m.type === 'relay' ? 'rel' : 'ctl')) {
      send(conn.ws, { type: 'error', code: 'rate', message: 'Demasiados mensajes.', ref: m.type });
      if (++conn.rateStrikes > 100) conn.ws.close(4429, 'rate');
      return;
    }
    try { H[m.type](conn, m); } catch (e) { o.log('error en', m.type, e.message); send(conn.ws, { type: 'error', code: 'internal', message: 'Error interno.', ref: m.type }); }
  }
  function strike(conn, code) {
    send(conn.ws, { type: 'error', code, message: 'Mensaje no válido.' });
    if (++conn.strikes >= 5) conn.ws.close(4400, code);
  }

  // --- HTTP + upgrade -----------------------------------------------------------------------------
  const SEC = { 'x-content-type-options': 'nosniff', 'cache-control': 'no-store', 'referrer-policy': 'no-referrer' };
  const json = (res, status, body) => { res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', ...SEC }); res.end(JSON.stringify(body)); };
  const server = http.createServer((req, res) => {
    const path = new URL(req.url, 'http://local').pathname;
    if (path === '/healthz') return json(res, 200, { ok: true, version: o.version, protocol: PROTOCOL_VERSION, ...stats() });
    if (o.originSecret && !safeEqual(req.headers['x-origin-secret'], o.originSecret)) return json(res, 403, { error: 'Acceso solo a través del proxy autorizado.' });
    if (o.httpHandler && o.httpHandler(req, res) === true) return;
    json(res, 404, { error: 'No encontrado.' });
  });
  server.headersTimeout = 20000; server.requestTimeout = 30000;

  function clientIp(req) {
    const sock = req.socket.remoteAddress;
    if (!o.trustProxy) {
      if (!warnedProxy && req.headers[o.clientIpHeader] && isPrivateIp(normalizeIp(sock) || '')) {
        warnedProxy = true;
        o.log(`Aviso: llega ${o.clientIpHeader} pero trustProxy está desactivado; si hay un proxy, todos aparecerán como una sola red.`);
      }
      return normalizeIp(sock);
    }
    const parts = String(req.headers[o.clientIpHeader] ?? '').split(',').map(s => s.trim()).filter(Boolean);
    return normalizeIp(parts[parts.length - o.proxyHops]) || normalizeIp(sock);
  }

  const wss = new WebSocketServer({ noServer: true, maxPayload: o.maxMessageBytes, perMessageDeflate: false });
  server.on('upgrade', (req, socket, head) => {
    const refuse = (status, text) => { socket.write(`HTTP/1.1 ${status} ${text}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n`); socket.destroy(); };
    if (new URL(req.url, 'http://local').pathname !== '/ws') return refuse(404, 'Not Found');
    if (o.originSecret && !safeEqual(req.headers['x-origin-secret'], o.originSecret)) return refuse(403, 'Forbidden');
    if (o.allowedOrigins.length && !o.allowedOrigins.includes(req.headers.origin)) return refuse(403, 'Forbidden');
    if (peers.size >= o.maxPeers) return refuse(503, 'Service Unavailable');
    const gid = gidOf(networkKey(clientIp(req)));
    if ((connsByGid.get(gid) || 0) >= o.maxConnsPerIp) return refuse(429, 'Too Many Requests');
    wss.handleUpgrade(req, socket, head, ws => {
      connsByGid.set(gid, (connsByGid.get(gid) || 0) + 1);
      const conn = { ws, gid, peer: null, strikes: 0, rateStrikes: 0, buckets: newBuckets(), alive: true, helloTimer: null };
      ws._conn = conn;
      conn.helloTimer = setTimeout(() => ws.close(4408, 'hello-timeout'), o.helloTimeoutMs);
      ws.on('pong', () => { conn.alive = true; });
      ws.on('message', (raw, isBinary) => onMessage(conn, raw, isBinary));
      ws.on('error', () => {});
      ws.on('close', () => {
        clearTimeout(conn.helloTimer);
        const n = (connsByGid.get(gid) || 1) - 1; n > 0 ? connsByGid.set(gid, n) : connsByGid.delete(gid);
        const p = conn.peer;
        if (p && !p.removed && !closing && p.conn === conn) goOffline(p);
      });
    });
  });
  const heartbeat = setInterval(() => {
    for (const ws of wss.clients) {
      const conn = ws._conn;
      if (conn && !conn.alive) { ws.terminate(); continue; }
      if (conn) conn.alive = false;
      try { ws.ping(); } catch {}
    }
  }, o.heartbeatMs);
  heartbeat.unref();

  const stats = () => ({ peers: peers.size, groups: groups.size, matches: matches.size, rooms: rooms.size, waiting: [...queues.values()].reduce((n, q) => n + q.length, 0) });

  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(o.port, o.host, resolve); });
  return {
    server, wss, options: o, port: server.address().port, stats,
    async close() {
      closing = true; clearInterval(heartbeat);
      for (const p of peers.values()) { clearTimeout(p.offlineTimer); clearTimeout(p.queueTimer); }
      for (const inv of invites.values()) clearTimeout(inv.timer);
      for (const r of rooms.values()) clearTimeout(r.timer);
      for (const ws of wss.clients) ws.terminate();
      server.closeAllConnections?.();
      await new Promise(r => server.close(r));
    },
  };
}

// --- arranque por línea de comandos ----------------------------------------------------------------
// PORT, HOST, TRUST_PROXY=1, PROXY_HOPS, ORIGIN_SECRET, ALLOWED_ORIGINS (coma). El secreto se lee del entorno; no se imprime.
if (process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))) {
  const env = process.env;
  const srv = await createSignalingServer({
    port: Number(env.PORT || 8787), host: env.HOST || '0.0.0.0',
    trustProxy: env.TRUST_PROXY === '1', proxyHops: Number(env.PROXY_HOPS || 1),
    originSecret: env.ORIGIN_SECRET || '', allowedOrigins: (env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean),
    version: env.APP_VERSION || 'dev',
  });
  console.log(`Señalización KADI LAN en el puerto ${srv.port} (trustProxy=${srv.options.trustProxy}, secreto de origen=${srv.options.originSecret ? 'sí' : 'no'})`);
}
