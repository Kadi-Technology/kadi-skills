// KADI LAN Multiplayer · cliente de navegador (ruta A): descubrimiento "misma red" + WebRTC DataChannel P2P
// con salida de relevo por WebSocket. Módulo ES sin dependencias. Protocolo: references/protocolo.md.
//
//   import { createLanClient } from './lan-client.js';
//   const lan = createLanClient({ url: 'wss://senal.example.com/ws', game: 'mi-juego-v1', alias: 'Ana' });
//   await lan.connect();
//   lan.on('peers', list => pintarRivales(list));              // [{ id, alias, state: 'idle'|'searching'|'busy' }]
//   lan.onInvite(inv => confirmar(inv.from.alias) ? inv.accept() : inv.decline());
//   lan.onMatch(match => {                                      // llega por cola, invitación o sala con código
//     match.onMessage(msg => juego.recibir(msg));
//     match.onState(s => ui.estado(s));                         // { state: 'open'|'reconnecting'|'closed', transport: 'p2p'|'relay' }
//     match.send({ t: 'hola' });
//   });
//   lan.findRival().catch(e => ui.aviso(e.code));               // 'timeout' | 'cancelled' | 'signal-lost' ...
//   lan.invite(idDelRival).catch(e => ui.aviso(e.code));        // 'declined' | 'timeout' | 'busy' | 'not-found' ...
//
// Por defecto iceServers = [] (sin STUN/TURN): solo candidatos "host", o sea solo la LAN. Si WebRTC no conecta
// (aislamiento de clientes del WiFi, mDNS bloqueado, navegador sin WebRTC) pasa solo al relevo por WebSocket.

const DEFAULTS = {
  url: '', game: 'mi-juego', alias: '', pin: '',
  iceServers: undefined,          // undefined = los que mande el servidor ([] por defecto)
  p2pTimeoutMs: 8000,             // sin DataChannel abierto en este tiempo -> relevo
  restartGraceMs: 2500,           // tras una pérdida, tiempo para recuperar (ICE restart) antes de pasar a relevo
  connectTimeoutMs: 8000, reconnectBaseMs: 500, reconnectMaxMs: 8000, maxReconnects: 40,
  forceRelay: false,              // útil para probar la salida de emergencia
  WebSocketImpl: globalThis.WebSocket,
  RTCPeerConnectionImpl: globalThis.RTCPeerConnection,
};
const defaultUrl = () => typeof location === 'undefined' ? '' : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
const codeError = (code, message = code) => Object.assign(new Error(message), { code });
function deferred() {
  const d = {}; d.promise = new Promise((res, rej) => { d.resolve = res; d.reject = rej; });
  d.promise.catch(() => {});      // quien solo usa onMatch no recibe "unhandled rejection" al cancelar
  return d;
}

export function createLanClient(options = {}) {
  const o = { ...DEFAULTS, ...options };
  if (!o.url) o.url = defaultUrl();
  const listeners = new Map(), messageHandlers = new Set();
  const on = (ev, fn) => { if (!listeners.has(ev)) listeners.set(ev, new Set()); listeners.get(ev).add(fn); return () => listeners.get(ev).delete(fn); };
  const emit = (ev, ...a) => { for (const fn of [...(listeners.get(ev) || [])]) { try { fn(...a); } catch (e) { console.error('[lan-client]', ev, e); } } };

  const S = { ws: null, status: 'idle', me: null, info: { iceServers: [], limits: { maxRelayBytes: 4096, queueTimeoutMs: 60000 }, relayOnly: false },
    peers: [], match: null, welcomed: false, intentional: false, attempts: 0, retryTimer: null, incoming: new Map(),
    pending: { find: null, invite: null, join: null, room: null } };

  const setStatus = status => { if (S.status !== status) { S.status = status; emit('status', status); } };
  const sendWs = obj => { const ws = S.ws; if (!ws || ws.readyState !== 1) return false; ws.send(JSON.stringify(obj)); return true; };
  const ctx = {
    o, sendWs, messageHandlers,
    iceServers: () => o.iceServers ?? S.info.iceServers ?? [],
    maxBytes: () => S.info.limits?.maxRelayBytes ?? 4096,
  };

  // --- conexión con el servidor de señalización ---------------------------------------------------
  function connect() {
    if (S.status === 'online') return Promise.resolve(S.me);
    if (S.connecting) return S.connecting.promise;
    S.intentional = false;
    S.connecting = deferred();
    open();
    return S.connecting.promise;
  }
  function open() {
    let ws;
    try { ws = new o.WebSocketImpl(o.url); } catch (e) { return failConnect(codeError('connect-failed', String(e.message || e))); }
    S.ws = ws;
    setStatus(S.welcomed ? 'reconnecting' : 'connecting');
    const guard = S.guard = S.welcomed ? null : setTimeout(() => { if (S.ws === ws && !S.welcomedThis) { try { ws.close(); } catch {} failConnect(codeError('connect-timeout')); } }, o.connectTimeoutMs);
    S.welcomedThis = false;
    ws.onopen = () => ws.send(JSON.stringify({ type: 'hello', v: 1, game: o.game, alias: o.alias, pin: o.pin || undefined, resume: S.me?.resume }));
    ws.onmessage = ev => { let m; try { m = JSON.parse(typeof ev.data === 'string' ? ev.data : String(ev.data)); } catch { return; } if (m && typeof m.type === 'string') onServer(m); };
    ws.onerror = () => {};
    ws.onclose = () => { clearTimeout(guard); if (S.ws !== ws) return; S.ws = null; onClosed(); };
  }
  function failConnect(err) {
    const c = S.connecting; S.connecting = null; S.intentional = true; setStatus('closed');
    if (S.ws) { try { S.ws.close(); } catch {} S.ws = null; }
    c?.reject(err);
  }
  function onClosed() {
    for (const k of ['find', 'invite', 'join', 'room']) rejectPending(k, codeError('signal-lost'));
    if (S.intentional) return setStatus('closed');
    if (!S.welcomed) return failConnect(codeError('connect-failed'));
    if (S.attempts >= o.maxReconnects) { setStatus('closed'); emit('error', { code: 'gave-up', message: 'Sin conexión con el servidor.' }); return; }
    setStatus('reconnecting');
    const delay = Math.min(o.reconnectMaxMs, o.reconnectBaseMs * 2 ** S.attempts++) * (0.75 + Math.random() * 0.5);
    S.retryTimer = setTimeout(open, delay);
  }
  function rejectPending(k, err) { const d = S.pending[k]; if (d) { S.pending[k] = null; d.reject(err); } }
  function resolvePending(k, v) { const d = S.pending[k]; if (d) { S.pending[k] = null; d.resolve(v); } }

  function onServer(m) {
    switch (m.type) {
      case 'welcome': {
        clearTimeout(S.guard); S.me = { id: m.id, alias: m.alias, resume: m.resume }; S.welcomed = S.welcomedThis = true; S.attempts = 0;
        S.info = { iceServers: m.iceServers || [], limits: m.limits || S.info.limits, relayOnly: !!m.relayOnly };
        setStatus('online');
        if (S.connecting) { const c = S.connecting; S.connecting = null; c.resolve(S.me); }
        if (m.resumed) emit('resumed', m);
        else if (S.match && S.match.transportName === 'relay') S.match._end('signal-lost');   // el servidor ya no recuerda el relevo
        if (m.resumed && m.match && !S.match) sendWs({ type: 'leave-match', matchId: m.match.matchId }); // reconexión tras recargar: no hay P2P que recuperar
        break;
      }
      case 'peers': S.peers = m.peers; emit('peers', m.peers); break;
      case 'queued': emit('queue', { state: 'searching', timeoutMs: m.timeoutMs }); break;
      case 'queue-ended': emit('queue', { state: 'idle', reason: m.reason }); rejectPending('find', codeError(m.reason)); break;
      case 'invite-sent': if (S.pending.invite) S.pending.invite.inviteId = m.inviteId; emit('invite-sent', m); break;
      case 'invited': {
        const inv = { inviteId: m.inviteId, from: m.from, expiresAt: Date.now() + m.timeoutMs,
          accept: () => { S.incoming.delete(m.inviteId); return sendWs({ type: 'invite-accept', inviteId: m.inviteId }); },
          decline: () => { S.incoming.delete(m.inviteId); return sendWs({ type: 'invite-decline', inviteId: m.inviteId }); } };
        S.incoming.set(m.inviteId, inv); emit('invite', inv); break;
      }
      case 'invite-ended': {
        S.incoming.delete(m.inviteId); emit('invite-ended', m);
        const p = S.pending.invite;
        if (p && (m.inviteId === null || m.inviteId === p.inviteId)) rejectPending('invite', codeError(m.reason));
        break;
      }
      case 'room-created': resolvePending('room', { code: m.code, ttlMs: m.ttlMs }); emit('room-created', m); break;
      case 'room-closed': emit('room-closed', m); break;
      case 'matched': onMatched(m); break;
      case 'signal': if (S.match?.id === m.matchId) S.match._onSignal(m.kind, m.data); break;
      case 'relay-ready': if (S.match?.id === m.matchId) S.match._activateRelay(); break;
      case 'relay': if (S.match?.id === m.matchId) S.match._deliver(m.data); break;
      case 'peer-status': if (S.match?.id === m.matchId) S.match._peerStatus(m.status); break;
      case 'match-ended': if (S.match?.id === m.matchId) S.match._end(m.reason); break;
      case 'error':
        emit('error', m);
        if (m.ref === 'queue') rejectPending('find', codeError(m.code, m.message));
        if (m.ref === 'room-join') rejectPending('join', codeError(m.code, m.message));
        if (m.ref === 'room-create') rejectPending('room', codeError(m.code, m.message));
        if (m.ref === 'hello' && S.connecting) failConnect(codeError(m.code, m.message));
        break;
      default: break;
    }
  }
  function onMatched(m) {
    if (S.match) S.match._dispose('replaced');
    const match = new Match(ctx, m);
    S.match = match;
    match.onState(s => { if (s.state === 'closed') { if (S.match === match) S.match = null; emit('match-ended', { matchId: match.id, reason: s.reason }); } });
    emit('match', match);
    for (const k of ['find', 'invite', 'join']) resolvePending(k, match);
    match._start();
  }

  // --- API pública ----------------------------------------------------------------------------------
  return {
    connect, on,
    onMatch: fn => on('match', fn), onInvite: fn => on('invite', fn), onPeers: fn => on('peers', fn),
    findRival() {
      if (S.pending.find) return S.pending.find.promise;
      if (S.match) return Promise.reject(codeError('in-match'));
      const d = S.pending.find = deferred();
      if (!sendWs({ type: 'queue' })) rejectPending('find', codeError('offline'));
      return d.promise;
    },
    cancelFind() { if (!sendWs({ type: 'dequeue' })) rejectPending('find', codeError('cancelled')); },
    invite(peerId) {
      if (S.pending.invite) return Promise.reject(codeError('busy'));
      if (S.match) return Promise.reject(codeError('in-match'));
      const d = S.pending.invite = deferred(); d.inviteId = null;
      if (!sendWs({ type: 'invite', to: peerId })) rejectPending('invite', codeError('offline'));
      return d.promise;
    },
    cancelInvite() { sendWs({ type: 'invite-cancel' }); },
    createRoom() {                      // el rival entra con joinRoom(code) desde cualquier red; llega por onMatch
      if (S.pending.room) return S.pending.room.promise;
      const d = S.pending.room = deferred();
      if (!sendWs({ type: 'room-create' })) rejectPending('room', codeError('offline'));
      return d.promise;
    },
    cancelRoom() { sendWs({ type: 'room-cancel' }); },
    joinRoom(code) {
      if (S.pending.join) return Promise.reject(codeError('busy'));
      const d = S.pending.join = deferred();
      if (!sendWs({ type: 'room-join', code: String(code || '').trim().toUpperCase() })) rejectPending('join', codeError('offline'));
      return d.promise;
    },
    leaveMatch() { S.match?.close(); },
    send: obj => S.match ? S.match.send(obj) : false,                       // atajo al emparejamiento actual
    onMessage(fn) { messageHandlers.add(fn); return () => messageHandlers.delete(fn); },
    close() {
      S.intentional = true; clearTimeout(S.retryTimer);
      S.match?.close(); sendWs({ type: 'bye' });
      if (S.ws) { try { S.ws.close(); } catch {} }
      setStatus('closed');
    },
    get status() { return S.status; }, get me() { return S.me; }, get peers() { return S.peers; }, get match() { return S.match; },
    get invites() { return [...S.incoming.values()]; },
    diagnostics: () => ({ status: S.status, transport: S.match?.transport ?? 'none', fallbackReason: S.match?.fallbackReason ?? null, iceServers: ctx.iceServers().length, relayOnly: S.info.relayOnly }),
  };
}

// --- un emparejamiento 1v1: DataChannel P2P con salida a relevo ---------------------------------------
class Match {
  constructor(ctx, info) {
    this.ctx = ctx; this.id = info.matchId; this.role = info.role; this.kind = info.kind; this.peer = info.peer;
    this.state = 'connecting'; this._everOpen = false; this.fallbackReason = null; this.transportName = 'none';
    this._serverTransport = info.transport; this._ice = info.iceServers;
    this._pc = null; this._dc = null; this._dcOpen = false; this._relay = false; this._relayAsked = false; this._closed = false;
    this._pendingIce = []; this._remoteSet = false; this._p2pTimer = null; this._lossTimer = null;
    this._h = { message: new Set(), state: new Set(), peer: new Set() };
  }
  get transport() { return this.transportName; }
  onMessage(fn) { this._h.message.add(fn); return () => this._h.message.delete(fn); }
  onState(fn) { this._h.state.add(fn); return () => this._h.state.delete(fn); }
  onPeerStatus(fn) { this._h.peer.add(fn); return () => this._h.peer.delete(fn); }

  send(obj) {
    if (this._closed) return false;
    let text; try { text = JSON.stringify(obj); } catch { return false; }
    if (text === undefined || text.length > this.ctx.maxBytes()) return false;  // mismo tope en P2P y en relevo: el juego no cambia al caer a relevo
    if (this._relay) return this.ctx.sendWs({ type: 'relay', matchId: this.id, data: obj });
    const dc = this._dc;
    if (dc && this._dcOpen && dc.readyState === 'open' && !(dc.bufferedAmount > 1048576)) { dc.send(text); return true; }
    return false;                                                                 // reconectando: el juego pide resync al volver
  }
  close() {
    if (this._closed) return;
    this.ctx.sendWs({ type: 'leave-match', matchId: this.id });
    this._end('left');
  }

  // -- ciclo de vida
  _setState(state, extra = {}) {
    const resumed = state === 'open' && this._everOpen;      // true = ya había estado abierto: el juego debe pedir resync
    if (state === 'open') this._everOpen = true;
    this.state = state;
    const s = { state, transport: this.transportName, matchId: this.id, ...(state === 'open' ? { resumed } : {}), ...extra };
    for (const fn of [...this._h.state]) { try { fn(s); } catch (e) { console.error('[lan-client] onState', e); } }
  }
  _deliver(data) {
    if (data === undefined || this._closed) return;
    for (const fn of [...this._h.message, ...this.ctx.messageHandlers]) { try { fn(data, this); } catch (e) { console.error('[lan-client] onMessage', e); } }
  }
  _peerStatus(status) { for (const fn of [...this._h.peer]) { try { fn(status); } catch (e) { console.error(e); } } }
  _dispose() {
    clearTimeout(this._p2pTimer); clearTimeout(this._lossTimer);
    try { this._dc?.close(); } catch {} try { this._pc?.close(); } catch {}
    this._dc = this._pc = null; this._dcOpen = false;
  }
  _end(reason) {
    if (this._closed) return;
    this._closed = true; this._dispose();
    this.transportName = 'none';
    this._setState('closed', { reason });
  }

  _start() {
    const { o } = this.ctx;
    if (this._serverTransport === 'relay') return;                               // el servidor ya abre el relevo (ruta B)
    if (o.forceRelay || !o.RTCPeerConnectionImpl) return this._askRelay(o.forceRelay ? 'forced' : 'no-webrtc');
    let pc;
    try { pc = new o.RTCPeerConnectionImpl({ iceServers: this._ice ?? this.ctx.iceServers() }); } catch { return this._askRelay('no-webrtc'); }
    this._pc = pc;
    pc.onicecandidate = e => { if (e.candidate) this._signal('ice', typeof e.candidate.toJSON === 'function' ? e.candidate.toJSON() : e.candidate); };
    const onConn = () => {
      const st = pc.connectionState ?? pc.iceConnectionState;
      if (st === 'connected' || st === 'completed') this._recovered();
      else if (st === 'failed' && !this._dcOpen) this._askRelay('ice-failed');   // ni siquiera llegó a abrirse: no esperes al temporizador
      else if (st === 'disconnected' || st === 'failed') this._lost(st);
    };
    pc.onconnectionstatechange = onConn; pc.oniceconnectionstatechange = onConn;
    if (this.role === 'host') { this._attach(pc.createDataChannel('game', { ordered: true })); this._offer(false); }
    else pc.ondatachannel = e => this._attach(e.channel);
    this._p2pTimer = setTimeout(() => { if (!this._dcOpen && !this._relay) this._askRelay('p2p-timeout'); }, this.ctx.o.p2pTimeoutMs);
  }
  _attach(dc) {
    this._dc = dc;
    dc.onopen = () => {
      if (this._relay || this._closed) return;
      clearTimeout(this._p2pTimer); clearTimeout(this._lossTimer); this._lossTimer = null;
      this._dcOpen = true; this.transportName = 'p2p';
      this._setState('open');
    };
    dc.onclose = () => { if (!this._closed && !this._relay) { this._dcOpen = false; this._lost('channel-closed'); } };
    dc.onmessage = e => {
      if (typeof e.data !== 'string' || e.data.length > this.ctx.maxBytes()) return;
      try { this._deliver(JSON.parse(e.data)); } catch { /* mensaje inválido: se descarta */ }
    };
  }
  async _offer(iceRestart) {
    const pc = this._pc;
    try {
      const offer = await pc.createOffer(iceRestart ? { iceRestart: true } : undefined);
      await pc.setLocalDescription(offer);
      this._signal('offer', { type: 'offer', sdp: (pc.localDescription || offer).sdp });
    } catch { if (!iceRestart) this._askRelay('offer-error'); }
  }
  _signal(kind, data) { this.ctx.sendWs({ type: 'signal', matchId: this.id, kind, data }); }
  async _onSignal(kind, data) {
    const pc = this._pc;
    if (!pc || this._relay || this._closed) return;
    try {
      if (kind === 'offer') {
        await pc.setRemoteDescription({ type: 'offer', sdp: data.sdp }); this._remoteSet = true; await this._flushIce();
        const answer = await pc.createAnswer(); await pc.setLocalDescription(answer);
        this._signal('answer', { type: 'answer', sdp: (pc.localDescription || answer).sdp });
      } else if (kind === 'answer') {
        await pc.setRemoteDescription({ type: 'answer', sdp: data.sdp }); this._remoteSet = true; await this._flushIce();
      } else if (kind === 'ice') {
        if (this._remoteSet) await pc.addIceCandidate(data).catch(() => {}); else this._pendingIce.push(data);
      }
    } catch { this._askRelay('signal-error'); }
  }
  async _flushIce() { const q = this._pendingIce; this._pendingIce = []; for (const c of q) await this._pc.addIceCandidate(c).catch(() => {}); }

  // -- pérdida y recuperación del P2P
  _lost(reason) {
    if (this._closed || this._relay || this._lossTimer || (!this._dcOpen && this.state !== 'open')) return;
    if (this.state === 'open') this._setState('reconnecting', { reason });
    if (this.role === 'host') this._offer(true);                                  // un intento de ICE restart
    this._lossTimer = setTimeout(() => { this._lossTimer = null; if (this.state !== 'open') this._askRelay('p2p-lost'); }, this.ctx.o.restartGraceMs);
  }
  _recovered() {
    if (!this._lossTimer) return;
    clearTimeout(this._lossTimer); this._lossTimer = null;
    if (this._dcOpen) this._setState('open');
  }

  // -- salida: relevo por WebSocket
  _askRelay(reason) {
    if (this._closed || this._relay || this._relayAsked) return;
    this._relayAsked = true; this.fallbackReason = reason;
    if (!this.ctx.sendWs({ type: 'relay-open', matchId: this.id })) this._end('signal-lost');
  }
  _activateRelay() {
    if (this._relay || this._closed) return;
    this._relay = true; this.fallbackReason ??= 'peer-request';
    this._dispose();
    this.transportName = 'relay';
    this._setState('open', { fallback: this.fallbackReason });
  }
}
