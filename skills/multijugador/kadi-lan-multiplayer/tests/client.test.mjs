// Pruebas de lan-client.js contra el servidor de señalización real. Node no trae WebRTC, así que el RTCPeerConnection
// es un doble (FakeRTC) que negocia SDP/ICE de verdad a través del servidor y abre un DataChannel en memoria.
// Lo que NO cubre: el motor WebRTC real de un navegador (ver references/seguridad-y-pruebas.md, prueba manual de dos dispositivos).
// node --test tests/client.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createSignalingServer } from '../templates/signaling-server.mjs';
import { createLanClient } from '../templates/lan-client.js';
import { bindAuthoritativeMatch } from '../templates/game-session.js';

const WS = createRequire(new URL('../templates/package.json', import.meta.url))('ws');
const WIFI_A = '203.0.113.10', WIFI_B = '198.51.100.9';
const T = { timeout: 20000 };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 3000, what = 'condición') {
  const end = Date.now() + ms;
  for (;;) { const v = await fn(); if (v) return v; if (Date.now() > end) throw new Error('Tiempo agotado: ' + what); await sleep(15); }
}

// --- doble de WebRTC -----------------------------------------------------------------------------
function fakeRtc({ connect = true, restartOk = true } = {}) {
  const reg = new Map(); let seq = 0;
  const rtc = { pcs: [], configs: [], restartOk, connect };
  class DC {
    constructor(label) { this.label = label; this.readyState = 'connecting'; this.bufferedAmount = 0; this.peer = null; }
    send(text) { if (this.readyState !== 'open') throw new Error('canal cerrado'); const p = this.peer; queueMicrotask(() => p.readyState === 'open' && p.onmessage?.({ data: text })); }
    close() { if (this.readyState === 'closed') return; this.readyState = 'closed'; this.onclose?.(); const p = this.peer; if (p && p.readyState !== 'closed') { p.readyState = 'closed'; p.onclose?.(); } }
  }
  class PC {
    constructor(cfg) { this.id = ++seq; reg.set(this.id, this); rtc.pcs.push(this); rtc.configs.push(cfg); this.connectionState = 'new'; this.ice = []; this.offers = 0; }
    createDataChannel(label) { return (this.dc = new DC(label)); }
    async createOffer(opts) { this.offers++; return { type: 'offer', sdp: `fake-offer ${this.id}${opts?.iceRestart ? ' restart' : ''}` }; }
    async createAnswer() { return { type: 'answer', sdp: `fake-answer ${this.id}${this.restartPending ? ' restart' : ''}` }; }
    async setLocalDescription(d) {
      this.localDescription = d;
      if (d.type === 'offer' && !this.candSent) {
        this.candSent = true;
        queueMicrotask(() => this.onicecandidate?.({ candidate: { candidate: 'candidate:1 1 udp 2122260223 192.168.1.5 50000 typ host', toJSON() { return { candidate: this.candidate }; } } }));
      }
    }
    async setRemoteDescription(d) {
      this.remote = d; this.remoteId = Number(/fake-\w+ (\d+)/.exec(d.sdp)[1]); const restart = d.sdp.includes('restart');
      if (d.type === 'offer') this.restartPending = restart;
      if (d.type === 'answer' && rtc.connect) {
        const guest = reg.get(this.remoteId);
        if (!restart) {                                     // primera negociación: crea y abre el canal en la otra punta
          const gdc = new DC(this.dc.label); this.dc.peer = gdc; gdc.peer = this.dc; guest.dc = gdc;
          guest.ondatachannel?.({ channel: gdc });
          setTimeout(() => { for (const [pc, ch] of [[this, this.dc], [guest, gdc]]) { pc.state('connected'); ch.readyState = 'open'; ch.onopen?.(); } }, 5);
        } else if (rtc.restartOk) { setTimeout(() => { this.state('connected'); guest.state('connected'); }, 5); }
      }
    }
    async addIceCandidate(c) { this.ice.push(c); }
    state(s) { this.connectionState = s; this.onconnectionstatechange?.(); }
    close() { this.connectionState = 'closed'; this.dc?.close(); }
  }
  rtc.PC = PC;
  return rtc;
}

// --- utilidades de prueba --------------------------------------------------------------------------
async function boot(extra = {}) {
  const calls = { relay: 0 };
  const srv = await createSignalingServer({ port: 0, host: '127.0.0.1', trustProxy: true, log: () => {}, hooks: { onRelayFrame: () => { calls.relay++; return false; } }, ...extra });
  srv.url = `ws://127.0.0.1:${srv.port}/ws`; srv.calls = calls; srv.clients = [];
  const orig = srv.close; srv.close = async () => { srv.clients.forEach(c => c.close()); await orig(); };
  return srv;
}
async function client(srv, { ip = WIFI_A, alias = 'Jugador', rtc, ...extra } = {}) {
  const sockets = [];
  const WebSocketImpl = class extends WS { constructor(url) { super(url, { headers: { 'x-forwarded-for': ip } }); sockets.push(this); } };
  const c = createLanClient({ url: srv.url, game: 'demo-v1', alias, WebSocketImpl, RTCPeerConnectionImpl: rtc ? rtc.PC : null, p2pTimeoutMs: 300, restartGraceMs: 200, reconnectBaseMs: 30, reconnectMaxMs: 100, ...extra });
  c.sockets = sockets; c.matches = []; c.onMatch(m => { m.log = []; m.inbox = []; m.onState(s => m.log.push(s)); m.onMessage(x => m.inbox.push(x)); c.matches.push(m); });
  await c.connect(); srv.clients.push(c);
  return c;
}
async function pair(srv, rtc, optsA = {}, optsB = {}) {
  const a = await client(srv, { rtc, alias: 'Ana', ...optsA }), b = await client(srv, { rtc, alias: 'Beto', ...optsB });
  const [ma, mb] = await Promise.all([a.findRival(), b.findRival()]);
  return { a, b, ma, mb };
}
const open = m => until(() => m.state === 'open', 3000, 'estado open');

test('P2P feliz: cola 1v1, DataChannel sin STUN/TURN, ICE de LAN y mensajes sin tocar el relevo', T, async () => {
  const srv = await boot(), rtc = fakeRtc();
  try {
    const { a, b, ma, mb } = await pair(srv, rtc);
    assert.equal(ma.role, 'host'); assert.equal(mb.role, 'guest'); assert.equal(ma.peer.alias, 'Beto'); assert.equal(mb.peer.alias, 'Ana');
    assert.equal(a.matches[0], ma, 'onMatch recibe el mismo objeto');
    await open(ma); await open(mb);
    assert.equal(ma.transport, 'p2p'); assert.equal(mb.transport, 'p2p');
    assert.deepEqual(rtc.configs.map(c => c.iceServers), [[], []], 'LAN: sin servidores STUN ni TURN');
    assert.equal(ma.send({ t: 'hola', n: 1 }), true);
    assert.equal(mb.send({ t: 'eco', n: 2 }), true);
    await until(() => mb.inbox.length && ma.inbox.length);
    assert.deepEqual(mb.inbox[0], { t: 'hola', n: 1 }); assert.deepEqual(ma.inbox[0], { t: 'eco', n: 2 });
    await until(() => rtc.pcs.find(p => p.ice.length), 1000, 'candidato ICE recibido');
    assert.equal(srv.calls.relay, 0, 'nada pasó por el servidor');
    assert.equal(ma.send({ blob: 'x'.repeat(5000) }), false, 'tope de tamaño');
    assert.equal(a.diagnostics().transport, 'p2p');
    const dcB = rtc.pcs[1]; dcB.dc.onmessage({ data: '{no json' }); dcB.dc.onmessage({ data: 42 }); // basura entrante: se descarta
    assert.equal(mb.inbox.length, 1);
  } finally { await srv.close(); }
});

test('invitar a un rival visible: aceptar, rechazar, cancelar y timeout', T, async () => {
  const srv = await boot({ inviteTimeoutMs: 300 }), rtc = fakeRtc();
  try {
    const a = await client(srv, { rtc, alias: 'Ana' }), b = await client(srv, { rtc, alias: 'Beto' }), far = await client(srv, { rtc, ip: WIFI_B });
    await until(() => a.peers.length === 1 && b.peers.length === 1, 2000, 'ver rivales');
    assert.equal(a.peers[0].alias, 'Beto'); assert.equal(far.peers.length, 0);
    const got = []; b.onInvite(inv => got.push(inv));
    // rechazar
    let p = a.invite(b.me.id); await until(() => got.length === 1);
    assert.equal(got[0].from.alias, 'Ana'); got[0].decline();
    await assert.rejects(p, { code: 'declined' });
    // cancelar
    p = a.invite(b.me.id); await until(() => got.length === 2); a.cancelInvite();
    await assert.rejects(p, { code: 'cancelled' });
    // timeout
    p = a.invite(b.me.id); await assert.rejects(p, { code: 'timeout' });
    // otra red: no existe
    await assert.rejects(a.invite(far.me.id), { code: 'not-found' });
    // aceptar
    p = a.invite(b.me.id); await until(() => got.length === 4); got[3].accept();
    const [ma, mb] = [await p, await until(() => b.matches[0])];
    assert.equal(ma.kind, 'invite'); assert.equal(ma.role, 'host'); assert.equal(mb.role, 'guest');
    await open(ma); await open(mb);
    await assert.rejects(a.findRival(), { code: 'in-match' });
  } finally { await srv.close(); }
});

test('buscar rival: timeout y cancelación rechazan la promesa y liberan la cola', T, async () => {
  const srv = await boot({ queueTimeoutMs: 250 });
  try {
    const a = await client(srv), b = await client(srv);
    const queue = []; a.on('queue', q => queue.push(q.state + (q.reason ? ':' + q.reason : '')));
    await assert.rejects(a.findRival(), { code: 'timeout' });
    const p = b.findRival(); await until(() => srv.stats().waiting === 1, 1000, 'B esperando'); b.cancelFind();
    await assert.rejects(p, { code: 'cancelled' });
    assert.equal(srv.stats().waiting, 0);
    assert.deepEqual(queue, ['searching', 'idle:timeout']);
  } finally { await srv.close(); }
});

test('salida si WebRTC falla: sin conexión P2P pasa solo al relevo y el juego sigue', T, async () => {
  const srv = await boot(), rtc = fakeRtc({ connect: false });
  try {
    const { ma, mb } = await pair(srv, rtc);
    await open(ma); await open(mb);
    assert.equal(ma.transport, 'relay'); assert.equal(mb.transport, 'relay');
    assert.equal(ma.fallbackReason, 'p2p-timeout');
    ma.send({ t: 'x', n: 1 }); mb.send({ t: 'y', n: 2 });
    await until(() => ma.inbox.length && mb.inbox.length);
    assert.deepEqual(mb.inbox[0], { t: 'x', n: 1 }); assert.deepEqual(ma.inbox[0], { t: 'y', n: 2 });
    assert.ok(srv.calls.relay >= 2, 'los mensajes viajaron por el servidor');
    assert.equal(ma.log.at(-1).transport, 'relay');
  } finally { await srv.close(); }
});

test('sin WebRTC en el navegador o con forceRelay se usa el relevo desde el principio', T, async () => {
  const srv = await boot();
  try {
    const { ma, mb } = await pair(srv, null);
    await open(ma); await open(mb);
    assert.equal(ma.transport, 'relay'); assert.ok(['no-webrtc', 'peer-request'].includes(ma.fallbackReason));
    ma.send({ ok: 1 }); await until(() => mb.inbox.length); assert.deepEqual(mb.inbox[0], { ok: 1 });
  } finally { await srv.close(); }
  const s2 = await boot(), rtc = fakeRtc();
  try {
    const { ma, mb } = await pair(s2, rtc, { forceRelay: true }, { forceRelay: true });
    await open(ma); await open(mb);
    assert.equal(ma.transport, 'relay'); assert.equal(ma.fallbackReason, 'forced');
  } finally { await s2.close(); }
});

test('pérdida del P2P en plena partida: un ICE restart la recupera sin cambiar de transporte', T, async () => {
  const srv = await boot(), rtc = fakeRtc({ restartOk: true });
  try {
    const { ma, mb } = await pair(srv, rtc);
    await open(ma); await open(mb);
    const host = rtc.pcs[0];
    host.state('disconnected');
    assert.equal(ma.state, 'reconnecting');
    await until(() => ma.state === 'open', 2000, 'recuperación');
    assert.equal(ma.transport, 'p2p'); assert.equal(ma.log.at(-1).resumed, true);
    assert.ok(host.offers >= 2, 'el anfitrión renegoció con iceRestart');
    ma.send({ t: 'otra-vez' }); await until(() => mb.inbox.length); assert.deepEqual(mb.inbox[0], { t: 'otra-vez' });
  } finally { await srv.close(); }
});

test('pérdida del P2P sin recuperación: cae al relevo en plena partida y avisa con resumed=true', T, async () => {
  const srv = await boot(), rtc = fakeRtc({ restartOk: false });
  try {
    const { ma, mb } = await pair(srv, rtc);
    await open(ma); await open(mb);
    rtc.pcs[0].state('failed');
    await until(() => ma.transport === 'relay' && mb.transport === 'relay' && ma.state === 'open' && mb.state === 'open', 3000, 'paso a relevo');
    assert.equal(ma.log.at(-1).resumed, true); assert.equal(mb.log.at(-1).resumed, true);
    assert.equal(ma.fallbackReason, 'p2p-lost');
    mb.send({ t: 'sigue' }); await until(() => ma.inbox.length); assert.deepEqual(ma.inbox[0], { t: 'sigue' });
  } finally { await srv.close(); }
});

test('reconexión de la señalización: el cliente reanuda su identidad y el relevo se mantiene', T, async () => {
  const srv = await boot({ resumeGraceMs: 2000 }), rtc = fakeRtc({ connect: false });
  try {
    const { a, b, ma, mb } = await pair(srv, rtc);
    await open(ma); await open(mb);
    const id = a.me.id, statuses = [], resumed = []; a.on('status', s => statuses.push(s)); a.on('resumed', () => resumed.push(1));
    const peerStates = []; mb.onPeerStatus(s => peerStates.push(s));
    a.sockets.at(-1).terminate();                       // se cae el WiFi de A
    await until(() => peerStates.includes('offline'), 2000, 'B ve a A desconectado');
    await until(() => a.status === 'online' && resumed.length === 1, 3000, 'A vuelve');
    assert.equal(a.me.id, id, 'misma identidad'); assert.ok(statuses.includes('reconnecting'));
    await until(() => peerStates.includes('online'), 2000, 'B ve a A de vuelta');
    assert.equal(ma.state, 'open');
    mb.send({ t: 'despues' }); await until(() => ma.inbox.length); assert.deepEqual(ma.inbox[0], { t: 'despues' });
  } finally { await srv.close(); }
});

test('sala con código entre redes distintas: sin STUN cae a relevo; código malo se rechaza', T, async () => {
  const srv = await boot(), rtc = fakeRtc({ connect: false });
  try {
    const a = await client(srv, { rtc }), far = await client(srv, { rtc, ip: WIFI_B });
    const { code } = await a.createRoom();
    assert.match(code, /^[A-Z2-9]{5}$/);
    await assert.rejects(far.joinRoom('ZZZZZ'), { code: 'room-not-found' });
    const mf = await far.joinRoom(code);
    const ma = await until(() => a.matches[0]);
    assert.equal(mf.kind, 'room'); assert.equal(ma.role, 'host');
    await open(ma); await open(mf);
    assert.equal(ma.transport, 'relay');
  } finally { await srv.close(); }
});

test('cerrar el emparejamiento avisa al rival y deja volver a buscar', T, async () => {
  const srv = await boot(), rtc = fakeRtc();
  try {
    const { a, b, ma, mb } = await pair(srv, rtc);
    await open(ma); await open(mb);
    const ended = []; b.on('match-ended', e => ended.push(e.reason));
    a.leaveMatch();
    await until(() => ended.length, 1000, 'fin del emparejamiento');
    assert.deepEqual(ended, ['peer-left']); assert.equal(mb.state, 'closed'); assert.equal(ma.state, 'closed');
    assert.equal(ma.send({ x: 1 }), false);
    const [m2a, m2b] = await Promise.all([a.findRival(), b.findRival()]);
    assert.notEqual(m2a.id, ma.id); await open(m2a); await open(m2b);
  } finally { await srv.close(); }
});

test('errores de conexión: PIN incorrecto y servidor inexistente rechazan connect()', T, async () => {
  const srv = await boot({ pin: '4821' });
  try {
    await assert.rejects(client(srv, { pin: '0000' }), { code: 'bad-pin' });
    const ok = await client(srv, { pin: '4821' }); assert.equal(ok.status, 'online');
  } finally { await srv.close(); }
  const c = createLanClient({ url: 'ws://127.0.0.1:1/ws', game: 'demo-v1', WebSocketImpl: WS, connectTimeoutMs: 500 });
  await assert.rejects(c.connect(), err => ['connect-failed', 'connect-timeout'].includes(err.code));
});

// --- integración: lan-client + bindAuthoritativeMatch (el cableado que usa SKILL.md) ------------------------------
const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const ttt = {
  initial: () => ({ board: Array(9).fill(null), turn: 0 }),
  validate: (s, seat, i) => !Number.isInteger(i?.cell) || i.cell < 0 || i.cell > 8 || s.board[i.cell] !== null ? 'invalid' : s.turn !== seat ? 'not-your-turn' : true,
  apply: (s, seat, i) => { const board = [...s.board]; board[i.cell] = seat; return { board, turn: 1 - seat }; },
  status(s) {
    for (const [a, b, c] of LINES) if (s.board[a] !== null && s.board[a] === s.board[b] && s.board[b] === s.board[c]) return { over: true, winner: s.board[a] };
    return s.board.every(x => x !== null) ? { over: true, winner: null } : { over: false };
  },
};

test('integración: partida con autoridad del anfitrión sobre P2P que sobrevive al paso a relevo y termina con revancha', T, async () => {
  const srv = await boot(), rtc = fakeRtc({ restartOk: false });
  try {
    const a = await client(srv, { rtc, alias: 'Ana' }), b = await client(srv, { rtc, alias: 'Beto' });
    for (const c of [a, b]) c.onMatch(m => { m.game = bindAuthoritativeMatch(m, { engine: ttt, predict: true, onState: v => { m.view = v; } }); });
    const [ma, mb] = await Promise.all([a.findRival(), b.findRival()]);
    await until(() => ma.view?.online[1] && mb.view, 3000, 'los dos conectados');
    assert.equal(ma.transport, 'p2p'); assert.deepEqual([ma.view.seat, mb.view.seat], [0, 1]);
    const move = async (m, cell) => { assert.ok(m.game.guest.input({ cell }) !== null); await until(() => ma.view.confirmedState.board[cell] !== null && mb.view.confirmedState.board[cell] !== null, 2000, 'jugada confirmada en ambos'); };
    await move(ma, 4); await move(mb, 0);
    assert.deepEqual(mb.view.state.board.slice(0, 5), [1, null, null, null, 0]);
    rtc.pcs[0].state('failed');                                         // se rompe el P2P en plena partida
    await until(() => ma.transport === 'relay' && mb.transport === 'relay' && ma.state === 'open' && mb.state === 'open', 3000, 'paso a relevo');
    await until(() => ma.view.online[1] && mb.view.online[0], 2000, 'rival en línea tras el relevo');
    assert.deepEqual(mb.view.state.board.slice(0, 5), [1, null, null, null, 0], 'el estado sobrevive al cambio de transporte');
    await move(ma, 1); await move(mb, 3); await move(ma, 7);            // 1, 4, 7 -> gana la persona 0
    await until(() => ma.view.over && mb.view.over, 2000, 'fin'); assert.equal(ma.view.winner, 'you');
    ma.game.guest.rematch(); mb.game.guest.rematch();
    await until(() => ma.view.gameNo === 2 && mb.view.gameNo === 2, 2000, 'revancha');
    assert.deepEqual([ma.view.seat, mb.view.seat], [1, 0]); assert.deepEqual(ma.view.wins, [1, 0]);
  } finally { await srv.close(); }
});
