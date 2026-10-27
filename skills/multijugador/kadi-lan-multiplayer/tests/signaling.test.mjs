// Pruebas del servidor de señalización: node --test tests/signaling.test.mjs
// Simulan "redes" distintas con la cabecera x-forwarded-for (trustProxy activo). IPs de documentación (RFC 5737).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createSignalingServer, networkKey, normalizeIp, isPrivateIp } from '../templates/signaling-server.mjs';

const WebSocket = createRequire(new URL('../templates/package.json', import.meta.url))('ws');
const WIFI_A = '203.0.113.10';   // casa de Ana: dos dispositivos
const WIFI_B = '198.51.100.9';   // otra red
const base = { port: 0, host: '127.0.0.1', trustProxy: true, log: () => {} };
const T = { timeout: 15000 };

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function boot(extra = {}) {
  const srv = await createSignalingServer({ ...base, ...extra });
  srv.url = `ws://127.0.0.1:${srv.port}/ws`;
  return srv;
}

// Cliente de prueba: cola de mensajes sin leer + bitácora completa.
class Client {
  constructor(ws) {
    this.ws = ws; this.unread = []; this.log = []; this.wake = null; this.closed = null;
    ws.on('message', raw => { const m = JSON.parse(raw.toString()); this.unread.push(m); this.log.push(m); this.wake?.(); });
    ws.on('close', code => { this.closed = code; this.wake?.(); });
    ws.on('error', () => {});
  }
  send(o) { this.ws.send(typeof o === 'string' ? o : JSON.stringify(o)); }
  async wait(pred, ms = 2000) {
    const f = typeof pred === 'string' ? m => m.type === pred : pred, end = Date.now() + ms;
    for (;;) {
      const i = this.unread.findIndex(f);
      if (i >= 0) return this.unread.splice(0, i + 1).pop();
      if (Date.now() > end) throw new Error('Tiempo agotado esperando mensaje; recibidos: ' + this.log.map(m => m.type).join(','));
      await new Promise(r => { this.wake = r; setTimeout(r, 25); });
    }
  }
  async none(pred, ms = 150) {
    const f = typeof pred === 'string' ? m => m.type === pred : pred;
    await sleep(ms);
    assert.equal(this.unread.find(f), undefined, 'no debía llegar ' + JSON.stringify(this.unread.find(f)));
  }
  lastPeers() { return [...this.log].reverse().find(m => m.type === 'peers')?.peers ?? []; }
  async closeCode(ms = 2000) { const end = Date.now() + ms; while (this.closed === null && Date.now() < end) await sleep(20); return this.closed; }
  close() { this.ws.close(); }
}
async function join(srv, { ip = WIFI_A, game = 'demo-v1', alias = 'Jugador', ...extra } = {}) {
  const ws = new WebSocket(srv.url, { headers: { 'x-forwarded-for': ip } });
  await new Promise((res, rej) => { ws.once('open', res); ws.once('error', rej); ws.once('unexpected-response', (_q, r) => rej(new Error('HTTP ' + r.statusCode))); });
  const c = new Client(ws);
  c.send({ type: 'hello', v: 1, game, alias, ...extra });
  c.welcome = await c.wait(m => m.type === 'welcome' || m.type === 'error');
  c.id = c.welcome.id;
  return c;
}
const rejected = (srv, headers) => new Promise(res => {
  const ws = new WebSocket(srv.url, { headers });
  ws.once('unexpected-response', (_q, r) => res(r.statusCode)); ws.once('open', () => { ws.close(); res(101); }); ws.once('error', () => {});
});

test('networkKey: agrupa por IPv4, por /64 de IPv6 y trata las privadas como una sola red local', () => {
  assert.equal(networkKey(normalizeIp('::ffff:203.0.113.10')), networkKey('203.0.113.10'));
  assert.equal(networkKey('2001:db8:1:2:aaaa::1'), networkKey('2001:db8:1:2:bbbb::9'), 'mismo /64 = mismo WiFi');
  assert.notEqual(networkKey('2001:db8:1:3::1'), networkKey('2001:db8:1:2::1'));
  assert.notEqual(networkKey('203.0.113.10'), networkKey('198.51.100.9'));
  for (const p of ['192.168.1.20', '10.0.0.5', '172.16.4.4', '127.0.0.1', '::1', 'fe80::1', 'fd12:3456::1']) { assert.ok(isPrivateIp(p), p); assert.equal(networkKey(p), 'priv'); }
  for (const p of ['203.0.113.10', '8.8.8.8', '172.32.0.1', '2001:db8::1']) assert.equal(isPrivateIp(p), false, p);
  assert.equal(normalizeIp('no-es-ip'), null);
});

test('agrupación por red: dos dispositivos de la misma IP se ven; otra red y otro juego no', T, async () => {
  const srv = await boot();
  try {
    const a = await join(srv, { alias: 'Ana-móvil' });
    const b = await join(srv, { alias: 'Ana-laptop' });
    const c = await join(srv, { ip: WIFI_B, alias: 'Vecino' });
    const d = await join(srv, { game: 'otro-juego', alias: 'OtroJuego' });
    await a.wait(m => m.type === 'peers' && m.peers.length === 1);
    assert.deepEqual(a.lastPeers().map(p => p.alias), ['Ana-laptop']);
    assert.deepEqual(b.lastPeers().map(p => p.alias), ['Ana-móvil']);
    await sleep(100);
    assert.deepEqual(c.lastPeers(), [], 'la otra red no ve a nadie');
    assert.deepEqual(d.lastPeers(), [], 'otro juego queda aparte');
    assert.equal(a.lastPeers()[0].state, 'idle');
    // Privacidad: ningún mensaje de control contiene una dirección IP.
    for (const cl of [a, b, c, d]) for (const m of cl.log) assert.doesNotMatch(JSON.stringify(m), /\d{1,3}(\.\d{1,3}){3}/, 'sin IPs en ' + m.type);
    assert.equal(b.welcome.groupSize, 2, 'el segundo dispositivo entra a un grupo de dos');
    c.close(); await a.wait(m => m.type === 'peers' && m.peers.length === 1, 500).catch(() => {});
    assert.equal(a.lastPeers().length, 1, 'que se vaya otra red no afecta al grupo');
  } finally { await srv.close(); }
});

test('sin trustProxy la cabecera x-forwarded-for se ignora (no se puede suplantar otra red)', T, async () => {
  const srv = await boot({ trustProxy: false });
  try {
    const a = await join(srv, { ip: WIFI_A }), b = await join(srv, { ip: WIFI_B });
    await a.wait(m => m.type === 'peers' && m.peers.length === 1);
    assert.equal(b.lastPeers().length === 1 || (await b.wait(m => m.type === 'peers' && m.peers.length === 1)).peers.length === 1, true);
  } finally { await srv.close(); }
});

test('cola 1v1: empareja a dos de la misma red y deja esperando al de otra', T, async () => {
  const srv = await boot();
  try {
    const a = await join(srv), b = await join(srv), c = await join(srv, { ip: WIFI_B }), e = await join(srv);
    a.send({ type: 'queue' }); await a.wait('queued');
    c.send({ type: 'queue' }); await c.wait('queued');
    await c.none('matched', 200);          // sola en su red: no se empareja con A
    b.send({ type: 'queue' });
    const ma = await a.wait('matched'), mb = await b.wait('matched');
    assert.equal(ma.matchId, mb.matchId);
    assert.equal(ma.role, 'host'); assert.equal(mb.role, 'guest');
    assert.equal(ma.peer.id, b.id); assert.equal(mb.peer.id, a.id);
    assert.equal(ma.transport, 'p2p'); assert.deepEqual(ma.iceServers, [], 'LAN: sin STUN/TURN');
    e.send({ type: 'queue' }); await e.wait('queued');
    await e.none('matched', 200);          // A y B ya están ocupados; E espera
    await e.wait(m => m.type === 'peers' && m.peers.some(p => p.id === a.id && p.state === 'busy'));
    const d = await join(srv, { ip: WIFI_B }); d.send({ type: 'queue' });
    assert.equal((await c.wait('matched')).peer.id, d.id, 'C y D (misma red) sí se emparejan');
  } finally { await srv.close(); }
});

test('cola: timeout y cancelación sacan de la cola y no dejan fantasmas', T, async () => {
  const srv = await boot({ queueTimeoutMs: 250 });
  try {
    const a = await join(srv), b = await join(srv);
    a.send({ type: 'queue' }); await a.wait('queued');
    assert.equal((await a.wait('queue-ended')).reason, 'timeout');
    b.send({ type: 'queue' }); await b.wait('queued');
    await a.none('matched', 100);          // A ya no estaba en la cola
    b.send({ type: 'dequeue' });
    assert.equal((await b.wait('queue-ended')).reason, 'cancelled');
    a.send({ type: 'queue' });
    await a.none('matched', 150);          // B canceló: A espera sola
    assert.equal(srv.stats().waiting, 1);
  } finally { await srv.close(); }
});

test('invitación: aceptar crea el emparejamiento; rechazar, cancelar y timeout liberan a ambos', T, async () => {
  const srv = await boot({ inviteTimeoutMs: 300 });
  try {
    const a = await join(srv, { alias: 'Ana' }), b = await join(srv, { alias: 'Beto' }), far = await join(srv, { ip: WIFI_B });
    await a.wait(m => m.type === 'peers' && m.peers.length === 1);
    // aceptar
    a.send({ type: 'invite', to: b.id });
    const sent = await a.wait('invite-sent'), got = await b.wait('invited');
    assert.equal(got.from.alias, 'Ana'); assert.equal(sent.inviteId, got.inviteId);
    b.send({ type: 'invite-accept', inviteId: got.inviteId });
    const ma = await a.wait('matched'), mb = await b.wait('matched');
    assert.equal(ma.kind, 'invite'); assert.equal(ma.role, 'host'); assert.equal(mb.role, 'guest'); assert.equal(ma.matchId, mb.matchId);
    a.send({ type: 'leave-match', matchId: ma.matchId });
    assert.equal((await a.wait('match-ended')).reason, 'left');
    assert.equal((await b.wait('match-ended')).reason, 'peer-left');
    // rechazar
    b.send({ type: 'invite', to: a.id }); const g2 = await a.wait('invited');
    a.send({ type: 'invite-decline', inviteId: g2.inviteId });
    assert.equal((await b.wait('invite-ended')).reason, 'declined');
    // cancelar
    a.send({ type: 'invite', to: b.id }); await b.wait('invited');
    a.send({ type: 'invite-cancel' });
    assert.equal((await b.wait('invite-ended')).reason, 'cancelled');
    // timeout
    a.send({ type: 'invite', to: b.id }); await b.wait('invited');
    assert.equal((await a.wait(m => m.type === 'invite-ended' && m.reason === 'timeout', 1500)).reason, 'timeout');
    // otra red: no existe para ti; ocupado: rechazo inmediato
    a.send({ type: 'invite', to: far.id });
    assert.equal((await a.wait('invite-ended')).reason, 'not-found');
    a.send({ type: 'invite', to: a.id });
    assert.equal((await a.wait('invite-ended')).reason, 'self');
    a.send({ type: 'invite', to: b.id }); const g3 = await b.wait('invited'); b.send({ type: 'invite-accept', inviteId: g3.inviteId });
    await a.wait('matched'); await b.wait('matched');
    const z = await join(srv); z.send({ type: 'invite', to: a.id });
    assert.equal((await z.wait('invite-ended')).reason, 'busy');
  } finally { await srv.close(); }
});

async function matched(srv, extra = {}) {
  const a = await join(srv, extra), b = await join(srv, extra);
  a.send({ type: 'queue' }); b.send({ type: 'queue' });
  const ma = await a.wait('matched'), mb = await b.wait('matched');
  return { a, b, id: ma.matchId, ma, mb };
}

test('relevo de SDP/ICE: solo entre los dos jugadores, valida y descarta candidatos no-LAN', T, async () => {
  const srv = await boot();
  try {
    const { a, b, id } = await matched(srv);
    const offer = { type: 'offer', sdp: 'v=0\r\no=- 1 1 IN IP4 0.0.0.0\r\n' };
    a.send({ type: 'signal', matchId: id, kind: 'offer', data: offer });
    const got = await b.wait('signal');
    assert.equal(got.kind, 'offer'); assert.equal(got.from, a.id); assert.deepEqual(got.data, offer);
    // srflx/relay se descartan (no filtra IP pública); el host llega
    a.send({ type: 'signal', matchId: id, kind: 'ice', data: { candidate: 'candidate:1 1 udp 1677729535 203.0.113.10 5000 typ srflx raddr 0.0.0.0 rport 0' } });
    a.send({ type: 'signal', matchId: id, kind: 'ice', data: { candidate: 'candidate:2 1 udp 2122260223 192.168.1.5 50000 typ host' } });
    const ice = await b.wait('signal');
    assert.match(ice.data.candidate, / typ host$/);
    await b.none('signal', 100);
    // validaciones
    a.send({ type: 'signal', matchId: id, kind: 'offer', data: { type: 'answer', sdp: 'x' } });
    assert.equal((await a.wait('error')).code, 'bad-signal');
    a.send({ type: 'signal', matchId: id, kind: 'offer', data: { type: 'offer', sdp: 'x'.repeat(13000) } });
    assert.equal((await a.wait('error')).code, 'bad-signal');
    const intruder = await join(srv, { alias: 'Intruso' });
    intruder.send({ type: 'signal', matchId: id, kind: 'offer', data: offer });
    assert.equal((await intruder.wait('error')).code, 'no-match');
    await b.none(m => m.type === 'signal', 100);
  } finally { await srv.close(); }
});

test('salida si WebRTC falla: relay-open abre el relevo por WebSocket para ambos', T, async () => {
  const srv = await boot({ maxRelayBytes: 200 });
  try {
    const { a, b, id } = await matched(srv);
    a.send({ type: 'relay', matchId: id, data: { hola: 1 } });
    assert.equal((await a.wait('error')).code, 'relay-closed');
    b.send({ type: 'relay-open', matchId: id });
    await a.wait('relay-ready'); await b.wait('relay-ready');
    a.send({ type: 'relay', matchId: id, data: { t: 'input', n: 1 } });
    assert.deepEqual((await b.wait('relay')).data, { t: 'input', n: 1 });
    b.send({ type: 'relay', matchId: id, data: { t: 'state', n: 2 } });
    assert.deepEqual((await a.wait('relay')).data, { t: 'state', n: 2 });
    a.send({ type: 'relay', matchId: id, data: { blob: 'x'.repeat(300) } });
    assert.equal((await a.wait('error')).code, 'too-big');
    await b.none('relay', 100);
    const c = await join(srv); c.send({ type: 'relay', matchId: id, data: {} });
    assert.equal((await c.wait('error')).code, 'no-match');
  } finally { await srv.close(); }
});

test('salas con código: une a dos redes distintas, caduca y bloquea la fuerza bruta', T, async () => {
  const srv = await boot({ roomTtlMs: 300, codeFailLimit: 3 });
  try {
    const a = await join(srv), far = await join(srv, { ip: WIFI_B }), other = await join(srv, { ip: WIFI_B, game: 'otro-juego' });
    a.send({ type: 'room-create' });
    const { code } = await a.wait('room-created');
    assert.match(code, /^[A-HJ-NP-Z2-9]{5}$/, 'alfabeto sin caracteres ambiguos');
    other.send({ type: 'room-join', code });
    assert.equal((await other.wait('error')).code, 'room-not-found', 'otro juego no entra');
    far.send({ type: 'room-join', code: code.toLowerCase() });
    const mf = await far.wait('matched'), ma = await a.wait('matched');
    assert.equal(ma.kind, 'room'); assert.equal(ma.role, 'host'); assert.equal(mf.role, 'guest');
    assert.equal(mf.matchId, ma.matchId);
    // un código se usa una vez
    const late = await join(srv, { ip: WIFI_B }); late.send({ type: 'room-join', code });
    assert.equal((await late.wait('error')).code, 'room-not-found');
    // caducidad
    const e = await join(srv, { ip: '192.0.2.77' }); e.send({ type: 'room-create' }); await e.wait('room-created');
    assert.equal((await e.wait('room-closed', 1500)).reason, 'timeout');
    // fuerza bruta: tras 3 fallos desde la misma red, ni siquiera un código bueno
    const f = await join(srv, { ip: '192.0.2.88' }), g = await join(srv, { ip: '192.0.2.88' });
    for (let i = 0; i < 3; i++) { f.send({ type: 'room-join', code: 'AAAAA' }); assert.equal((await f.wait('error')).code, 'room-not-found'); }
    g.send({ type: 'room-create' }); const r = await g.wait('room-created');
    f.send({ type: 'room-join', code: r.code });
    assert.equal((await f.wait('error')).code, 'rate');
  } finally { await srv.close(); }
});

test('límites: mensaje grande, tasa, binario, JSON roto, hello obligatorio y tiempo de hello', T, async () => {
  const srv = await boot({ maxMessageBytes: 1024, ctlBurst: 5, ctlPerSec: 1, helloTimeoutMs: 200 });
  try {
    const big = await join(srv);
    big.send(JSON.stringify({ type: 'ping', pad: 'x'.repeat(4000) }));
    assert.equal(await big.closeCode(), 1009, 'tamaño excedido: cierre 1009');

    const a = await join(srv);
    for (let i = 0; i < 12; i++) a.send({ type: 'ping', t: i });
    assert.equal((await a.wait('error', 1500)).code, 'rate');

    const j = await join(srv);
    for (let i = 0; i < 5; i++) j.send('{no es json');
    assert.equal(await j.closeCode(), 4400, 'cinco mensajes inválidos cierran la conexión');

    const ws = new WebSocket(srv.url); const raw = new Client(ws);
    await new Promise(r => ws.once('open', r));
    raw.send({ type: 'queue' });
    assert.equal((await raw.wait('error')).code, 'no-hello');
    assert.equal(await raw.closeCode(1500), 4408, 'sin hello a tiempo se cierra');

    const bin = await join(srv); bin.ws.send(Buffer.from([1, 2, 3]));
    assert.equal(await bin.closeCode(), 1003);
  } finally { await srv.close(); }
});

test('límites: conexiones por IP, tamaño de grupo, hello inválido y PIN', T, async () => {
  const srv = await boot({ maxConnsPerIp: 2, maxGroupSize: 2 });
  try {
    await join(srv); await join(srv);
    assert.equal(await rejected(srv, { 'x-forwarded-for': WIFI_A }), 429, 'tercera conexión de la misma IP');
    assert.equal(await rejected(srv, { 'x-forwarded-for': WIFI_B }), 101, 'otra IP entra');
  } finally { await srv.close(); }
  const s2 = await boot({ maxGroupSize: 2 });
  try {
    await join(s2); await join(s2);
    const third = await join(s2);
    assert.equal(third.welcome.code, 'group-full');
    assert.equal(await third.closeCode(), 4400);
    const bad = await join(s2, { game: 'juego con espacios' });
    assert.equal(bad.welcome.code, 'bad-game');
  } finally { await s2.close(); }
  const s3 = await boot({ pin: '4821', codeFailLimit: 2 });
  try {
    assert.equal((await join(s3, { pin: '0000' })).welcome.code, 'bad-pin');
    assert.equal((await join(s3, { pin: '1111' })).welcome.code, 'bad-pin');
    assert.equal((await join(s3, { pin: '4821' })).welcome.code, 'rate', 'bloqueo tras fallos repetidos');
  } finally { await s3.close(); }
  const s4 = await boot({ pin: '4821' });
  try { assert.equal((await join(s4, { pin: '4821' })).welcome.type, 'welcome'); } finally { await s4.close(); }
});

test('secreto de origen y Origin: el proxy debe enviarlo; /healthz sigue abierto y no expone IPs', T, async () => {
  const srv = await boot({ originSecret: 'secreto-de-prueba', allowedOrigins: ['https://juego.example'] });
  try {
    assert.equal(await rejected(srv, { 'x-forwarded-for': WIFI_A }), 403);
    assert.equal(await rejected(srv, { 'x-forwarded-for': WIFI_A, 'x-origin-secret': 'incorrecto', origin: 'https://juego.example' }), 403);
    assert.equal(await rejected(srv, { 'x-forwarded-for': WIFI_A, 'x-origin-secret': 'secreto-de-prueba', origin: 'https://malo.example' }), 403, 'Origin fuera de la lista');
    assert.equal(await rejected(srv, { 'x-forwarded-for': WIFI_A, 'x-origin-secret': 'secreto-de-prueba', origin: 'https://juego.example' }), 101);
    const h = await fetch(`http://127.0.0.1:${srv.port}/healthz`);
    const txt = await h.text();
    assert.equal(h.status, 200); assert.equal(JSON.parse(txt).ok, true);
    assert.doesNotMatch(txt, /secreto|\d+\.\d+\.\d+\.\d+/);
    assert.equal((await fetch(`http://127.0.0.1:${srv.port}/otra`)).status, 403);
  } finally { await srv.close(); }
  const open = await boot();
  try { assert.equal((await fetch(`http://127.0.0.1:${open.port}/otra`)).status, 404); } finally { await open.close(); }
});

test('reconexión: el emparejamiento sobrevive a una caída corta con el token de reanudación y caduca si no vuelve', T, async () => {
  const srv = await boot({ resumeGraceMs: 400 });
  try {
    const { a, b, id } = await matched(srv);
    const resume = a.welcome.resume;
    a.ws.terminate();
    assert.equal((await b.wait('peer-status')).status, 'offline');
    const a2 = await join(srv, { resume });
    assert.equal(a2.welcome.resumed, true); assert.equal(a2.id, a.id);
    assert.equal(a2.welcome.match.matchId, id); assert.equal(a2.welcome.match.role, 'host');
    assert.equal((await b.wait('peer-status')).status, 'online');
    // el token no se puede usar desde otra red
    const thief = await join(srv, { ip: WIFI_B, resume });
    assert.equal(thief.welcome.resumed, false); assert.notEqual(thief.id, a.id);
    // si no vuelve a tiempo, el rival recibe el fin del emparejamiento
    a2.ws.terminate();
    await b.wait('peer-status');
    assert.equal((await b.wait('match-ended', 1500)).reason, 'peer-lost');
    assert.equal((await join(srv, { resume })).welcome.resumed, false, 'token caducado');
  } finally { await srv.close(); }
});

test('salir de la red limpia: un dispositivo que cierra desaparece de la lista tras la gracia', T, async () => {
  const srv = await boot({ resumeGraceMs: 150 });
  try {
    const a = await join(srv), b = await join(srv);
    await a.wait(m => m.type === 'peers' && m.peers.length === 1);
    b.send({ type: 'bye' });
    await a.wait(m => m.type === 'peers' && m.peers.length === 0);
    await sleep(250);
    assert.equal(srv.stats().peers, 1);
  } finally { await srv.close(); }
});
