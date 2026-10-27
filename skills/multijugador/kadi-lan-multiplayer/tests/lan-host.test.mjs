// Pruebas de la ruta B (lan-host-mdns.mjs): DNS-SD/mDNS, anuncio y descubrimiento UDP, HTTP seguro, PIN y partida con el host
// como autoridad o como simple relevo. Todo en 127.0.0.1: no necesita multicast ni red real. node --test tests/lan-host.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import dgram from 'node:dgram';
import net from 'node:net';
import { EventEmitter } from 'node:events';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import {
  createLanHost, buildMdnsResponse, buildMdnsQuery, parseDns, answerKinds, encodeName, startMdnsResponder,
  startUdpAnnouncer, discoverLanHosts, buildAnnounce, parseAnnounce, lanAddresses,
} from '../templates/lan-host-mdns.mjs';
import { createLanClient } from '../templates/lan-client.js';
import { createGuestSession } from '../templates/game-session.js';

const WS = createRequire(new URL('../templates/package.json', import.meta.url))('ws');
const FIXTURE = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures', 'public');
const T = { timeout: 20000 };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 3000, what = 'condición') {
  const end = Date.now() + ms;
  for (;;) { const v = await fn(); if (v) return v; if (Date.now() > end) throw new Error('Tiempo agotado: ' + what); await sleep(15); }
}

const P = { instance: 'Mesa de Ana', serviceType: '_kadigame._tcp', hostname: 'mesa-de-ana', port: 8787, ips: ['192.168.1.20', '10.0.0.7'], txt: { v: '1', game: 'demo-v1', path: '/ws', pin: '1' } };

test('DNS-SD: la respuesta mDNS se puede decodificar y trae PTR, SRV, TXT y A correctos', () => {
  const dns = parseDns(buildMdnsResponse(P));
  assert.equal(dns.response, true);
  const by = t => dns.answers.filter(a => a.type === t);
  assert.equal(by(12)[0].name, '_kadigame._tcp.local'); assert.equal(by(12)[0].data, 'Mesa de Ana._kadigame._tcp.local');
  assert.deepEqual(by(33)[0].data, { priority: 0, weight: 0, port: 8787, target: 'mesa-de-ana.local' });
  assert.deepEqual(by(16)[0].data, ['v=1', 'game=demo-v1', 'path=/ws', 'pin=1']);
  assert.deepEqual(by(1).map(a => a.data), ['192.168.1.20', '10.0.0.7']);
  assert.ok(dns.answers.every(a => a.ttl === 120));
  assert.equal(parseDns(buildMdnsResponse({ ...P, ttl: 0 })).answers[0].ttl, 0, 'ttl 0 = adiós');
  assert.equal(parseDns(buildMdnsResponse(P, ['a'])).answers.length, 2);
  assert.throws(() => encodeName('x'.repeat(64) + '.local'), /Etiqueta DNS/);
  assert.throws(() => parseDns(Buffer.alloc(4)), /corto/);
});

test('DNS-SD: answerKinds contesta solo lo que se pregunta, sin distinguir mayúsculas', () => {
  const q = (name, type) => parseDns(buildMdnsQuery(name, type)).questions;
  assert.deepEqual(answerKinds(q('_KadiGame._tcp.local', 12), P).sort(), ['a', 'ptr', 'srv', 'txt']);
  assert.deepEqual(answerKinds(q('Mesa de Ana._kadigame._tcp.local', 33), P).sort(), ['a', 'srv', 'txt']);
  assert.deepEqual(answerKinds(q('mesa-de-ana.local', 1), P), ['a']);
  assert.deepEqual(answerKinds(q('mesa-de-ana.local', 28), P), [], 'AAAA no se contesta');
  assert.deepEqual(answerKinds(q('_otra._tcp.local', 12), P), []);
});

test('responder mDNS: se anuncia al arrancar, contesta consultas por multicast o unicast e ignora basura y respuestas', T, async () => {
  const sent = [];
  class Sock extends EventEmitter { bind(_p, cb) { cb(); } addMembership() {} setMulticastTTL() {} setMulticastLoopback() {} send(b, port, addr) { sent.push({ b, port, addr }); } close() {} }
  const sock = new Sock(), r = startMdnsResponder(P, { socket: sock });
  assert.equal(sent.length, 1, 'anuncio inicial'); assert.equal(sent[0].addr, '224.0.0.251'); assert.equal(sent[0].port, 5353);
  const rinfo = { address: '192.168.1.50', port: 49152 };
  sock.emit('message', buildMdnsQuery('_kadigame._tcp.local', 12), rinfo);
  assert.equal(sent.length, 2); assert.equal(sent[1].addr, '224.0.0.251');
  assert.equal(parseDns(sent[1].b).answers.length, 5);
  const uni = buildMdnsQuery('mesa-de-ana.local', 1); uni.writeUInt16BE(0x8001, uni.length - 2);
  sock.emit('message', uni, rinfo);
  assert.deepEqual([sent[2].addr, sent[2].port], ['192.168.1.50', 49152], 'bit unicast: contesta solo al que preguntó');
  sock.emit('message', buildMdnsQuery('_otra._tcp.local', 12), rinfo);
  sock.emit('message', Buffer.from('basura'), rinfo);
  sock.emit('message', buildMdnsResponse(P), rinfo);   // otra respuesta mDNS: no se contesta
  assert.equal(sent.length, 3);
  r.stop(); await sleep(80);
  assert.equal(parseDns(sent.at(-1).b).answers[0].ttl, 0, 'al parar manda el adiós');
});

test('anuncio UDP y descubrimiento: la app encuentra el host sin que el datagrama lleve IP ni PIN', T, async () => {
  const tmp = dgram.createSocket('udp4'); await new Promise(r => tmp.bind(0, '127.0.0.1', r));
  const discoveryPort = tmp.address().port; tmp.close();
  const seen = []; const finder = discoverLanHosts({ discoveryPort, bindAddress: '127.0.0.1', timeoutMs: 800, game: 'demo-v1', onFound: h => seen.push(h) });
  const ann = startUdpAnnouncer({ name: 'Mesa de Ana', game: 'demo-v1', port: 8787, pin: true, discoveryPort, broadcastAddresses: ['127.0.0.1'], intervalMs: 80, getPlayers: () => 1 });
  const other = startUdpAnnouncer({ name: 'Otro', game: 'otro-juego', port: 9000, discoveryPort, broadcastAddresses: ['127.0.0.1'], intervalMs: 80 });
  const hosts = await finder; ann.stop(); other.stop();
  assert.equal(hosts.length, 1, 'filtra por juego y no duplica');
  assert.deepEqual({ ...hosts[0] }, { name: 'Mesa de Ana', game: 'demo-v1', address: '127.0.0.1', port: 8787, players: 1, pin: true, url: 'http://127.0.0.1:8787/', wsUrl: 'ws://127.0.0.1:8787/ws' });
  assert.equal(seen.length, 1);
  const pkt = buildAnnounce({ name: 'X', game: 'g', port: 1, pin: true }).toString();
  assert.doesNotMatch(pkt, /\d+\.\d+\.\d+\.\d+/, 'el datagrama no lleva IP'); assert.equal(JSON.parse(pkt).pin, true);
});

test('parseAnnounce rechaza anuncios falsos, enormes o de fuera de la LAN', () => {
  const ok = { kadi: 'lan-host', v: 1, name: 'Mesa', game: 'demo-v1', port: 8787, path: '/ws', players: 0, pin: false };
  const mk = o => Buffer.from(JSON.stringify({ ...ok, ...o }));
  assert.ok(parseAnnounce(mk({}), '192.168.1.9'));
  assert.equal(parseAnnounce(mk({}), '203.0.113.5'), null, 'IP pública: se ignora');
  assert.equal(parseAnnounce(mk({ kadi: 'otra-cosa' }), '192.168.1.9'), null);
  assert.equal(parseAnnounce(mk({ port: 70000 }), '192.168.1.9'), null);
  assert.equal(parseAnnounce(mk({ game: '../etc' }), '192.168.1.9'), null);
  assert.equal(parseAnnounce(mk({ name: 'x'.repeat(2000) }), '192.168.1.9'), null);
  assert.equal(parseAnnounce(Buffer.from('{no json'), '192.168.1.9'), null);
  assert.equal(parseAnnounce(mk({ path: '/../../x' }), '192.168.1.9').wsUrl, 'ws://192.168.1.9:8787/ws', 'el path se sanea');
});

test('lanAddresses: solo IPv4 privadas y externas, con su dirección de broadcast', () => {
  const ifs = {
    lo: [{ family: 'IPv4', address: '127.0.0.1', netmask: '255.0.0.0', internal: true }],
    wifi: [{ family: 'IPv4', address: '192.168.1.20', netmask: '255.255.255.0', internal: false }, { family: 'IPv6', address: 'fe80::1', internal: false }],
    nube: [{ family: 'IPv4', address: '203.0.113.9', netmask: '255.255.255.0', internal: false }],
    hotspot: [{ family: 4, address: '10.0.12.1', netmask: '255.255.0.0', internal: false }],
  };
  assert.deepEqual(lanAddresses(ifs).map(a => [a.address, a.broadcast]), [['192.168.1.20', '192.168.1.255'], ['10.0.12.1', '10.0.255.255']]);
});

// --- host completo ---------------------------------------------------------------------------------------------
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
const open = [];                       // los clientes se cierran al terminar: si no, reintentarían conectarse para siempre
test.afterEach(() => { while (open.length) open.pop().close(); });
async function lanClient(lan, extra = {}) {
  const sockets = [];
  const WebSocketImpl = class extends WS { constructor(url) { super(url); sockets.push(this); } };
  const c = createLanClient({ url: `ws://127.0.0.1:${lan.port}/ws`, game: 'demo-v1', WebSocketImpl, RTCPeerConnectionImpl: null, ...extra });
  c.sockets = sockets; open.push(c); await c.connect(); return c;
}
// Patrón recomendado: cablear el juego DENTRO de onMatch, antes de que lleguen los primeros mensajes del host.
function wireGuest(c) {
  c.onMatch(m => {
    m.g = createGuestSession({ send: x => m.send(x) });
    m.onMessage(x => m.g.receive(x));
    m.onState(s => { if (s.state === 'open' && s.resumed) m.g.resync(); });   // tras una reconexión, pide el estado completo
  });
}
const boot = (extra = {}) => createLanHost({ name: 'Mesa de Ana', game: 'demo-v1', port: 0, host: '127.0.0.1', announce: { mdns: false, udp: false },
  addresses: [{ address: '192.168.1.20' }], log: () => {}, ...extra });

test('HTTP del host: sirve la página, /info sin IPs, rechaza traversal, métodos y expone solo URLs privadas', T, async () => {
  const lan = await boot({ publicDir: FIXTURE, pin: '4821' });
  try {
    assert.deepEqual(lan.urls, [`http://192.168.1.20:${lan.port}/`]);
    const base = `http://127.0.0.1:${lan.port}`;
    const home = await fetch(base + '/'); const html = await home.text();
    assert.equal(home.status, 200); assert.match(home.headers.get('content-type'), /text\/html/); assert.match(html, /Juego de prueba/);
    assert.equal(home.headers.get('x-content-type-options'), 'nosniff'); assert.match(home.headers.get('content-security-policy'), /frame-ancestors 'none'/);
    assert.match(home.headers.get('content-security-policy'), new RegExp(`connect-src 'self' ws://127.0.0.1:${lan.port}`));
    assert.match(await (await fetch(base + '/app.js')).text(), /__fixture/);
    for (const bad of ['/..%2f..%2fpackage.json', '/%2e%2e/%2e%2e/package.json', '/%00', '/no-existe.html', '/%E0%A4%A']) assert.equal((await fetch(base + bad)).status, 404, bad);
    assert.equal((await fetch(base + '/', { method: 'POST' })).status, 405);
    const info = await (await fetch(base + '/info')).json();
    assert.deepEqual(info, { kadi: 'lan-host', v: 1, name: 'Mesa de Ana', game: 'demo-v1', players: 0, pin: true, mode: 'relay', ws: '/ws' });
    assert.doesNotMatch(JSON.stringify(info), /4821|\d+\.\d+\.\d+\.\d+/, 'ni el PIN ni IPs');
    assert.equal((await (await fetch(base + '/healthz')).json()).ok, true);
  } finally { await lan.stop(); }
});

test('PIN de la mesa: sin él o con uno incorrecto no se entra', T, async () => {
  const lan = await boot({ pin: '4821' });
  try {
    await assert.rejects(lanClient(lan, { pin: '0000' }), { code: 'bad-pin' });
    await assert.rejects(lanClient(lan), { code: 'bad-pin' });
    const ok = await lanClient(lan, { pin: '4821' }); assert.equal(ok.status, 'online'); ok.close();
  } finally { await lan.stop(); }
});

test('host con autoridad (patrón del servidor de referencia sobre la LAN): partida completa por WebSocket, revancha y abandono', T, async () => {
  const lan = await boot({ engine: ttt, mode: 'sequential', authority: { graceMs: 150 }, pin: '4821' });
  try {
    const a = await lanClient(lan, { pin: '4821', alias: 'Ana' }), b = await lanClient(lan, { pin: '4821', alias: 'Beto' });
    wireGuest(a); wireGuest(b);
    const [ma, mb] = await Promise.all([a.findRival(), b.findRival()]);
    await until(() => ma.state === 'open' && mb.state === 'open', 2000, 'relevo abierto');
    assert.equal(ma.transport, 'relay'); assert.equal(mb.transport, 'relay');
    const ga = ma.g, gb = mb.g;
    await until(() => ga.view && gb.view, 2000, 'estado inicial');
    assert.deepEqual([ga.view.seat, gb.view.seat], [0, 1]); assert.equal(ga.view.online[1], true);
    const move = async (g, cell, mine) => { g.input({ cell }); await until(() => mine().view.state.board[cell] !== null || mine().view.rejected, 2000, 'jugada'); };
    gb.input({ cell: 0 }); await until(() => gb.view.rejected, 2000, 'rechazo fuera de turno');
    assert.equal(gb.view.rejected.reason, 'not-your-turn');
    for (const [g, cell] of [[ga, 4], [gb, 0], [ga, 1], [gb, 2], [ga, 7]]) await move(g, cell, () => g);
    await until(() => ga.view.over && gb.view.over, 2000, 'fin');
    assert.equal(ga.view.winner, 'you'); assert.equal(gb.view.winner, 'rival');
    assert.equal(lan.signaling.stats().matches, 1);
    ga.rematch(); gb.rematch();
    await until(() => ga.view.gameNo === 2 && gb.view.gameNo === 2, 2000, 'revancha');
    assert.deepEqual([ga.view.seat, gb.view.seat], [1, 0], 'asientos intercambiados'); assert.deepEqual(ga.view.wins, [1, 0]);
    // Beto pierde la conexión (se cae el WiFi) y no vuelve a tiempo: Ana gana por abandono
    b.sockets.at(-1).terminate();
    await until(() => ga.view.end === 'forfeit' || ga.view.online[1] === false, 2000, 'rival desconectado');
    await until(() => ga.view.end === 'forfeit', 2000, 'abandono'); assert.equal(ga.view.winner, 'you'); assert.deepEqual(ga.view.wins, [2, 0]);
  } finally { await lan.stop(); }
});

test('host sin motor (solo relevo): los mensajes pasan tal cual y el cliente "host" puede ser la autoridad', T, async () => {
  const lan = await boot();
  try {
    assert.equal((await (await fetch(`http://127.0.0.1:${lan.port}/info`)).json()).mode, 'relay');
    const a = await lanClient(lan, { alias: 'Ana' }), b = await lanClient(lan, { alias: 'Beto' });
    const [ma, mb] = await Promise.all([a.findRival(), b.findRival()]);
    await until(() => ma.state === 'open' && mb.state === 'open');
    assert.equal(ma.role, 'host'); assert.equal(mb.role, 'guest');
    const inA = [], inB = []; ma.onMessage(m => inA.push(m)); mb.onMessage(m => inB.push(m));
    ma.send({ t: 'estado', n: 1 }); mb.send({ t: 'input', n: 2 });
    await until(() => inA.length && inB.length);
    assert.deepEqual(inB[0], { t: 'estado', n: 1 }); assert.deepEqual(inA[0], { t: 'input', n: 2 });
    assert.equal(ma.send({ blob: 'x'.repeat(5000) }), false);
  } finally { await lan.stop(); }
});

test('anuncios del host: createLanHost levanta el anuncio UDP y se puede descubrir con discoverLanHosts', T, async () => {
  const tmp = dgram.createSocket('udp4'); await new Promise(r => tmp.bind(0, '127.0.0.1', r));
  const discoveryPort = tmp.address().port; tmp.close();
  const lan = await boot({ announce: { mdns: false, udp: true }, discoveryPort, broadcastAddresses: ['127.0.0.1'], pin: '9999' });
  try {
    const hosts = await discoverLanHosts({ discoveryPort, bindAddress: '127.0.0.1', timeoutMs: 600 });
    assert.equal(hosts.length, 1); assert.equal(hosts[0].port, lan.port); assert.equal(hosts[0].pin, true);
    assert.doesNotMatch(JSON.stringify(hosts), /9999/);
    assert.deepEqual(lan.status, { mdns: false, udp: true });
  } finally { await lan.stop(); }
});

// --- arranque por línea de comandos (variables de entorno) -------------------------------------------------------
async function freePort() { const s = net.createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p; } // puerto TCP libre
async function runCli(file, env, probe) {
  const child = spawn(process.execPath, [path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'templates', file)], { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = ''; child.stdout.on('data', d => { out += d; }); child.stderr.on('data', d => { out += d; });
  try { return await probe(() => out); } finally { if (child.exitCode === null) { child.kill(); await new Promise(r => child.once('exit', r)); } }
}
const fetchOk = async url => { const r = await fetch(url).catch(() => null); return r && r.ok ? r : null; };

test('CLI de lan-host-mdns.mjs: variables de entorno, módulo de motor, PIN y sin anuncios', T, async () => {
  const port = await freePort();
  await runCli('lan-host-mdns.mjs', { PORT: String(port), ANNOUNCE: 'none', PUBLIC_DIR: FIXTURE, GAME: 'demo-v1', NAME: 'Mesa CLI', PIN: '4821',
    ENGINE_MODULE: path.join(FIXTURE, '..', 'engine-tictactoe.mjs') }, async out => {
    const info = await until(() => fetchOk(`http://127.0.0.1:${port}/info`), 5000, 'el host responde').then(r => r.json());
    assert.deepEqual(info, { kadi: 'lan-host', v: 1, name: 'Mesa CLI', game: 'demo-v1', players: 0, pin: true, mode: 'authority', ws: '/ws' });
    await until(() => /PIN de la mesa/.test(out()), 3000, 'salida de la terminal');
    assert.ok(out().includes('Host LAN KADI (autoridad del host) · mDNS=false UDP=false'), 'resumen de arranque');
    assert.match(out(), /PIN de la mesa: 4821/);
  });
});

test('CLI de signaling-server.mjs: puerto, secreto de origen y /healthz', T, async () => {
  const port = await freePort();
  await runCli('signaling-server.mjs', { PORT: String(port), HOST: '127.0.0.1', ORIGIN_SECRET: 'secreto-de-prueba', TRUST_PROXY: '1' }, async out => {
    const h = await until(() => fetchOk(`http://127.0.0.1:${port}/healthz`), 5000, 'el servidor responde').then(r => r.json());
    assert.equal(h.ok, true);
    assert.equal((await fetch(`http://127.0.0.1:${port}/otra`)).status, 403);
    await until(() => /Señalización KADI LAN/.test(out()), 3000, 'salida de la terminal');
    assert.match(out(), /trustProxy=true, secreto de origen=sí/);
    assert.doesNotMatch(out(), /secreto-de-prueba/, 'el secreto no se imprime');
  });
});
