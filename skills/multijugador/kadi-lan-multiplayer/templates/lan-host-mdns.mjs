// KADI LAN Multiplayer · host LAN totalmente offline (ruta B).
//
// Un dispositivo (PC, portátil, Raspberry Pi) corre este proceso Node. Sin internet y sin servidor externo:
//   - Sirve la página del juego por http:// desde la propia LAN (evita el bloqueo de contenido mixto: una página
//     https:// no puede abrir ws://IP-local) y el WebSocket del juego en /ws.
//   - Reutiliza signaling-server.mjs en modo "todos en un grupo" + relevo: lobby, cola 1v1, invitaciones, salas y PIN.
//   - Si le pasas un motor (engine), el host es la AUTORIDAD (patrón del servidor del juego de referencia de KADI: valida, resuelve y reparte vistas);
//     si no, solo retransmite y el cliente con rol "host" es la autoridad.
//   - Se anuncia por mDNS/DNS-SD (_kadigame._tcp.local) y por broadcast UDP, y muestra URL + QR en la terminal.
//
// Los NAVEGADORES NO PUEDEN descubrir mDNS ni UDP por sí solos: los jugadores entran escaneando el QR o escribiendo la
// URL (http://IP:puerto/). Una app de escritorio o móvil (Electron, React Native, nativa) sí puede descubrir: usa
// discoverLanHosts() (Node/Electron) o NsdManager (Android) / NWBrowser (iOS).
// Dependencia: ws (vía signaling-server.mjs). Opcional: qrcode-terminal (solo para pintar el QR).
import dgram from 'node:dgram';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createSignalingServer, isPrivateIp } from './signaling-server.mjs';
import { createHostAuthority } from './game-session.js';

export const MDNS_GROUP = '224.0.0.251', MDNS_PORT = 5353, DISCOVERY_PORT = 41234;
const GAME_RE = /^[A-Za-z0-9._-]{1,48}$/;
const label = s => String(s ?? '').replace(/[\u0000-\u001f\u007f.]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 48);
const slug = s => label(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'kadi-host';

// --- direcciones de la LAN ------------------------------------------------------------------------------
// Solo IPv4 privadas: nunca se anuncia ni se muestra una IP pública.
export function lanAddresses(interfaces = os.networkInterfaces()) {
  const out = [];
  for (const [iface, list] of Object.entries(interfaces)) {
    for (const a of list || []) {
      if ((a.family === 'IPv4' || a.family === 4) && !a.internal && isPrivateIp(a.address)) {
        const ip = a.address.split('.').map(Number), mask = (a.netmask || '255.255.255.0').split('.').map(Number);
        out.push({ iface, address: a.address, netmask: a.netmask, broadcast: ip.map((o, i) => (o | (~mask[i] & 255)) & 255).join('.') });
      }
    }
  }
  return out;
}

// --- mDNS / DNS-SD mínimo (RFC 6762/6763), sin dependencias --------------------------------------------------
export function encodeName(name) {
  const parts = [];
  for (const l of String(name).replace(/\.$/, '').split('.')) {
    const b = Buffer.from(l, 'utf8');
    if (!b.length || b.length > 63) throw new Error('Etiqueta DNS no válida: ' + l);
    parts.push(Buffer.from([b.length]), b);
  }
  parts.push(Buffer.from([0]));
  return Buffer.concat(parts);
}
const rr = (name, type, cls, ttl, rdata) => {
  const h = Buffer.alloc(10); h.writeUInt16BE(type, 0); h.writeUInt16BE(cls, 2); h.writeUInt32BE(ttl, 4); h.writeUInt16BE(rdata.length, 8);
  return Buffer.concat([encodeName(name), h, rdata]);
};
// p = { instance, serviceType: '_kadigame._tcp', hostname, port, ips: ['192.168.x.y'], txt: { game, path, v }, ttl }
export function dnsNames(p) {
  const service = `${p.serviceType}.local`;
  return { service, instance: `${label(p.instance)}.${service}`, host: `${p.hostname}.local` };
}
export function buildMdnsResponse(p, kinds = ['ptr', 'srv', 'txt', 'a']) {
  const n = dnsNames(p), ttl = p.ttl ?? 120, recs = [];
  if (kinds.includes('ptr')) recs.push(rr(n.service, 12, 1, ttl, encodeName(n.instance)));
  if (kinds.includes('srv')) { const d = Buffer.alloc(6); d.writeUInt16BE(0, 0); d.writeUInt16BE(0, 2); d.writeUInt16BE(p.port, 4); recs.push(rr(n.instance, 33, 0x8001, ttl, Buffer.concat([d, encodeName(n.host)]))); }
  if (kinds.includes('txt')) {
    const strs = Object.entries(p.txt || {}).map(([k, v]) => Buffer.from(`${k}=${v}`, 'utf8').subarray(0, 255));
    recs.push(rr(n.instance, 16, 0x8001, ttl, strs.length ? Buffer.concat(strs.map(s => Buffer.concat([Buffer.from([s.length]), s]))) : Buffer.from([0])));
  }
  if (kinds.includes('a')) for (const ip of p.ips || []) recs.push(rr(n.host, 1, 0x8001, ttl, Buffer.from(ip.split('.').map(Number))));
  const head = Buffer.alloc(12); head.writeUInt16BE(0x8400, 2); head.writeUInt16BE(recs.length, 6);
  return Buffer.concat([head, ...recs]);
}
function readName(buf, off) {
  const labels = []; let next = -1, hops = 0;
  for (;;) {
    if (off >= buf.length || hops > 20) throw new Error('DNS truncado');
    const len = buf[off];
    if (len === 0) { off++; break; }
    if ((len & 0xc0) === 0xc0) { if (next < 0) next = off + 2; off = ((len & 0x3f) << 8) | buf[off + 1]; hops++; continue; }
    labels.push(buf.toString('utf8', off + 1, off + 1 + len)); off += 1 + len;
  }
  return [labels.join('.'), next >= 0 ? next : off];
}
export function parseDns(buf) {
  if (buf.length < 12) throw new Error('Paquete DNS demasiado corto');
  const flags = buf.readUInt16BE(2), qd = buf.readUInt16BE(4), total = buf.readUInt16BE(6) + buf.readUInt16BE(8) + buf.readUInt16BE(10);
  let off = 12; const questions = [], answers = [];
  for (let i = 0; i < qd; i++) { const [name, o] = readName(buf, off); questions.push({ name, type: buf.readUInt16BE(o), unicast: !!(buf.readUInt16BE(o + 2) & 0x8000) }); off = o + 4; }
  for (let i = 0; i < total; i++) {
    const [name, o] = readName(buf, off), type = buf.readUInt16BE(o), ttl = buf.readUInt32BE(o + 4), len = buf.readUInt16BE(o + 8), d = o + 10;
    let data;
    if (type === 1) data = [...buf.subarray(d, d + 4)].join('.');
    else if (type === 12) data = readName(buf, d)[0];
    else if (type === 33) data = { priority: buf.readUInt16BE(d), weight: buf.readUInt16BE(d + 2), port: buf.readUInt16BE(d + 4), target: readName(buf, d + 6)[0] };
    else if (type === 16) { data = []; for (let q = d; q < d + len;) { const l = buf[q]; if (l) data.push(buf.toString('utf8', q + 1, q + 1 + l)); q += 1 + l; } }
    else data = buf.subarray(d, d + len).toString('hex');
    answers.push({ name, type, ttl, data }); off = d + len;
  }
  return { response: !!(flags & 0x8000), questions, answers };
}
export function buildMdnsQuery(name, type = 12) {
  const head = Buffer.alloc(12); head.writeUInt16BE(1, 4);
  const tail = Buffer.alloc(4); tail.writeUInt16BE(type, 0); tail.writeUInt16BE(1, 2);
  return Buffer.concat([head, encodeName(name), tail]);
}
// Qué registros hay que contestar a estas preguntas (nombres sin distinguir mayúsculas).
export function answerKinds(questions, p) {
  const n = dnsNames(p), kinds = new Set();
  for (const q of questions) {
    const name = q.name.toLowerCase(), any = q.type === 255;
    if (name === n.service.toLowerCase() && (q.type === 12 || any)) ['ptr', 'srv', 'txt', 'a'].forEach(k => kinds.add(k));
    else if (name === n.instance.toLowerCase() && (q.type === 33 || q.type === 16 || any)) ['srv', 'txt', 'a'].forEach(k => kinds.add(k));
    else if (name === n.host.toLowerCase() && (q.type === 1 || any)) kinds.add('a');
  }
  return [...kinds];
}
// Responde consultas mDNS y se anuncia al arrancar. Mejor esfuerzo: si el puerto 5353 está tomado o la red no permite
// multicast, devuelve { ok:false } y el host sigue con broadcast UDP + QR. `socket` se puede inyectar (pruebas).
export function startMdnsResponder(p, { socket, port = MDNS_PORT, group = MDNS_GROUP, onError = () => {} } = {}) {
  const sock = socket || dgram.createSocket({ type: 'udp4', reuseAddr: true });
  const send = (buf, toPort = port, toAddr = group) => { try { sock.send(buf, toPort, toAddr); } catch (e) { onError(e); } };
  const announce = () => send(buildMdnsResponse(p));
  let timers = [];
  sock.on('error', e => onError(e));
  sock.on('message', (msg, rinfo) => {
    let dns; try { dns = parseDns(msg); } catch { return; }
    if (dns.response || !dns.questions.length) return;
    const kinds = answerKinds(dns.questions, p);
    if (!kinds.length) return;
    const uni = dns.questions.some(q => q.unicast);
    send(buildMdnsResponse(p, kinds), uni ? rinfo.port : port, uni ? rinfo.address : group);
  });
  sock.bind(port, () => {
    try { for (const ip of p.ips || []) sock.addMembership(group, ip); sock.setMulticastTTL(255); sock.setMulticastLoopback(true); } catch (e) { onError(e); }
    announce(); timers = [setTimeout(announce, 1000), setTimeout(announce, 3000)];
  });
  return {
    announce,
    stop() { timers.forEach(clearTimeout); try { send(buildMdnsResponse({ ...p, ttl: 0 })); } catch {} setTimeout(() => { try { sock.close(); } catch {} }, 50); }, // ttl 0 = "adiós"
  };
}

// --- anuncio por broadcast UDP y descubrimiento (apps de escritorio/móvil) ----------------------------------------
// El datagrama NO lleva la IP: quien escucha toma la dirección de origen. Tampoco lleva el PIN, solo si existe.
export function buildAnnounce({ name, game, port, players = 0, pin = false }) {
  return Buffer.from(JSON.stringify({ kadi: 'lan-host', v: 1, name: label(name), game, port, path: '/ws', players, pin: !!pin }));
}
export function parseAnnounce(buf, address) {
  if (!buf || buf.length > 1024) return null;
  let m; try { m = JSON.parse(buf.toString('utf8')); } catch { return null; }
  if (!m || m.kadi !== 'lan-host' || m.v !== 1 || typeof m.name !== 'string' || !GAME_RE.test(String(m.game))) return null;
  if (!Number.isInteger(m.port) || m.port < 1 || m.port > 65535 || !isPrivateIp(address)) return null; // solo anuncios que vienen de la LAN
  return { name: label(m.name), game: m.game, address, port: m.port, players: Number(m.players) || 0, pin: !!m.pin,
    url: `http://${address}:${m.port}/`, wsUrl: `ws://${address}:${m.port}${/^\/\w+$/.test(m.path) ? m.path : '/ws'}` };
}
export function startUdpAnnouncer({ name, game, port, getPlayers = () => 0, pin = false, discoveryPort = DISCOVERY_PORT, broadcastAddresses, intervalMs = 2000 }) {
  const sock = dgram.createSocket({ type: 'udp4', reuseAddr: true });
  const targets = broadcastAddresses || [...new Set(lanAddresses().map(a => a.broadcast))];
  let timer = null;
  sock.bind(0, () => {
    try { sock.setBroadcast(true); } catch {}
    const tick = () => { const pkt = buildAnnounce({ name, game, port, players: getPlayers(), pin }); for (const t of targets) { try { sock.send(pkt, discoveryPort, t); } catch {} } };
    tick(); timer = setInterval(tick, intervalMs); timer.unref?.();
  });
  sock.on('error', () => {});
  return { stop() { clearInterval(timer); try { sock.close(); } catch {} } };
}
// Para apps de escritorio/móvil con acceso a UDP. Devuelve los hosts vistos durante timeoutMs.
export function discoverLanHosts({ timeoutMs = 3000, discoveryPort = DISCOVERY_PORT, bindAddress = '0.0.0.0', game, onFound } = {}) {
  return new Promise(resolve => {
    const sock = dgram.createSocket({ type: 'udp4', reuseAddr: true }), found = new Map();
    const done = () => { try { sock.close(); } catch {} resolve([...found.values()]); };
    sock.on('error', done);
    sock.on('message', (msg, rinfo) => {
      const h = parseAnnounce(msg, rinfo.address);
      if (!h || (game && h.game !== game)) return;
      const key = `${h.address}:${h.port}`;
      if (!found.has(key)) { found.set(key, h); onFound?.(h); } else found.set(key, h);
    });
    sock.bind(discoveryPort, bindAddress);
    setTimeout(done, timeoutMs);
  });
}

// --- HTTP: página del juego + /info ----------------------------------------------------------------------------
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon', '.wasm': 'application/wasm', '.txt': 'text/plain; charset=utf-8' };
function httpHandler({ publicDir, info }) {
  const root = publicDir ? path.resolve(publicDir) : null;
  return (req, res) => {
    const u = new URL(req.url, 'http://local'), host = String(req.headers.host || '');
    const sec = {
      'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer', 'x-frame-options': 'DENY',
      'content-security-policy': `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' ${/^[\w.\-\[\]:]+$/.test(host) ? 'ws://' + host : ''}; base-uri 'none'; frame-ancestors 'none'`,
    };
    if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405, { 'content-type': 'application/json', ...sec }); res.end('{"error":"Método no permitido."}'); return true; }
    if (u.pathname === '/info') { res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...sec }); res.end(JSON.stringify(info())); return true; }
    if (!root) { res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8', ...sec }); res.end('Host LAN de KADI listo. Conecta el cliente del juego a /ws.\n'); return true; }
    let rel; try { rel = decodeURIComponent(u.pathname); } catch { rel = '/\0'; }
    if (rel === '/' || rel === '') rel = '/index.html';
    const file = path.resolve(root, '.' + rel);
    if (rel.includes('\0') || !file.startsWith(root + path.sep)) { res.writeHead(404, { 'content-type': 'application/json', ...sec }); res.end('{"error":"No encontrado."}'); return true; }
    fs.stat(file, (err, st) => {
      if (err || !st.isFile()) { res.writeHead(404, { 'content-type': 'application/json', ...sec }); return res.end('{"error":"No encontrado."}'); }
      res.writeHead(200, { 'content-type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream', 'content-length': st.size, 'cache-control': 'no-cache', ...sec });
      if (req.method === 'HEAD') return res.end();
      fs.createReadStream(file).pipe(res);
    });
    return true;
  };
}

// --- el host ----------------------------------------------------------------------------------------------------
// opts: { name, game, port, host, publicDir, engine, mode:'sequential'|'simultaneous', authority:{graceMs}, pin, announce:{mdns,udp},
//         discoveryPort, serviceType, addresses, broadcastAddresses, log, signalingOptions }
export async function createLanHost(opts = {}) {
  const { name = 'Mesa de juego', game = 'mi-juego-v1', port = 8787, host = '0.0.0.0', publicDir = null, engine = null, mode = 'sequential',
    authority = {}, pin = '', announce = { mdns: true, udp: true }, discoveryPort = DISCOVERY_PORT, serviceType = '_kadigame._tcp',
    broadcastAddresses, log = (...a) => console.log(...a), signalingOptions = {} } = opts;
  if (!GAME_RE.test(game)) throw new Error('game no válido');
  const sessions = new Map();
  let signaling;
  const info = () => ({ kadi: 'lan-host', v: 1, name: label(name), game, players: signaling?.stats().peers ?? 0, pin: !!pin, mode: engine ? 'authority' : 'relay', ws: '/ws' });

  const hooks = engine ? {
    onMatch(m, io) {
      const auth = createHostAuthority({ engine, mode, ...authority, send: (person, msg) => io.sendTo(person === 0 ? m.a : m.b, msg) });
      sessions.set(m.id, auth); auth.join(0); auth.join(1);
    },
    onRelayFrame(m, fromId, data) { sessions.get(m.id)?.receive(fromId === m.a ? 0 : 1, data); return true; },
    onPeerStatus(m, id, status) { const a = sessions.get(m.id); if (a) status === 'offline' ? a.leave(id === m.a ? 0 : 1) : a.join(id === m.a ? 0 : 1); },
    onMatchEnd(m) { sessions.get(m.id)?.dispose(); sessions.delete(m.id); },
  } : null;

  signaling = await createSignalingServer({
    port, host, groupBy: 'all', relayOnly: true, pin, maxGroupSize: 16, version: 'lan-host', log,
    httpHandler: httpHandler({ publicDir, info }), hooks, ...signalingOptions,
  });
  const actual = signaling.port;
  const addrs = opts.addresses || lanAddresses();
  const urls = addrs.map(a => `http://${a.address}:${actual}/`);

  const stops = [], status = { mdns: false, udp: false };
  if (announce.mdns) {
    const ips = addrs.map(a => a.address);
    if (ips.length) {
      const r = startMdnsResponder({ instance: name, serviceType, hostname: slug(name), port: actual, ips, txt: { v: '1', game, path: '/ws', pin: pin ? '1' : '0' } },
        { onError: e => log('mDNS no disponible (se sigue con UDP y QR):', e.code || e.message) });
      stops.push(() => r.stop()); status.mdns = true;
    }
  }
  if (announce.udp) {
    const u = startUdpAnnouncer({ name, game, port: actual, getPlayers: () => signaling.stats().peers, pin, discoveryPort, broadcastAddresses });
    stops.push(() => u.stop()); status.udp = true;
  }
  return {
    signaling, urls, port: actual, status, sessions,
    async stop() { stops.forEach(f => { try { f(); } catch {} }); for (const s of sessions.values()) s.dispose(); await signaling.close(); },
  };
}

// --- arranque por línea de comandos ----------------------------------------------------------------------------------
// PORT, GAME, NAME, PUBLIC_DIR (carpeta del juego), PIN (por defecto se genera uno de 4 dígitos; PIN=none lo desactiva),
// ANNOUNCE (all | mdns | udp | none; por defecto all), ENGINE_MODULE (ruta a un módulo ESM con `export default engine`
// y opcional `export const mode`).
if (process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))) {
  const env = process.env;
  const pin = env.PIN === 'none' ? '' : (env.PIN || String(crypto.randomInt(1000, 10000)));
  let engine = null, mode = 'sequential';
  if (env.ENGINE_MODULE) { const mod = await import(pathToFileURL(path.resolve(env.ENGINE_MODULE)).href); engine = mod.default; mode = mod.mode || mode; }
  const ann = env.ANNOUNCE || 'all';
  const lan = await createLanHost({ name: env.NAME || 'Mesa de juego', game: env.GAME || 'mi-juego-v1', port: Number(env.PORT || 8787), publicDir: env.PUBLIC_DIR || null, engine, mode, pin,
    announce: { mdns: ann === 'all' || ann === 'mdns', udp: ann === 'all' || ann === 'udp' } });
  console.log(`Host LAN KADI (${engine ? 'autoridad del host' : 'relevo'}) · mDNS=${lan.status.mdns} UDP=${lan.status.udp}`);
  if (!lan.urls.length) console.log('No se encontró ninguna IP privada: conéctate a un WiFi/Ethernet o activa el punto de acceso del dispositivo.');
  for (const u of lan.urls) {
    const join = pin ? `${u}?pin=${pin}` : u;
    console.log('Entrar desde el navegador:', join);
    try { const qr = (await import('qrcode-terminal')).default; qr.generate(join, { small: true }); } catch { /* QR opcional: npm i qrcode-terminal */ }
  }
  if (pin) console.log(`PIN de la mesa: ${pin} (la página lo borra de la URL al abrirse). Cualquiera en esta red con el PIN puede jugar.`);
  console.log('Aviso: este host no cifra el tráfico (http/ws). Úsalo solo en una red de confianza.');
}
