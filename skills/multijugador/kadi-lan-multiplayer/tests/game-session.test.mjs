// Pruebas de la capa de juego: autoridad del anfitrión, predicción/reconciliación, órdenes selladas, abandono,
// revancha y lockstep (con latencia, corte, desincronización y resincronización). node --test tests/game-session.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHostAuthority, createGuestSession, createLockstep } from '../templates/game-session.js';

const clone = x => JSON.parse(JSON.stringify(x));
const sleep = ms => new Promise(r => setTimeout(r, ms));

// --- motores de ejemplo -------------------------------------------------------------------------
const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const ttt = { // por turnos, información perfecta
  initial: () => ({ board: Array(9).fill(null), turn: 0 }),
  validate: (s, seat, i) => !Number.isInteger(i?.cell) || i.cell < 0 || i.cell > 8 || s.board[i.cell] !== null ? 'invalid' : s.turn !== seat ? 'not-your-turn' : true,
  apply: (s, seat, i) => { const board = [...s.board]; board[i.cell] = seat; return { board, turn: 1 - seat }; },
  status(s) {
    for (const [a, b, c] of LINES) if (s.board[a] !== null && s.board[a] === s.board[b] && s.board[b] === s.board[c]) return { over: true, winner: s.board[a] };
    return s.board.every(x => x !== null) ? { over: true, winner: null } : { over: false };
  },
};
const claim = { // sin turnos: quien llega primero se queda la celda (sirve para probar reconciliación)
  initial: () => ({ cells: [null, null, null] }),
  validate: (s, seat, i) => Number.isInteger(i?.cell) && s.cells[i.cell] === null ? true : 'taken',
  apply: (s, seat, i) => { const cells = [...s.cells]; cells[i.cell] = seat; return { cells }; },
  status: s => s.cells.every(x => x !== null) ? { over: true, winner: s.cells.filter(x => x === 0).length > 1 ? 0 : 1 } : { over: false },
};
const BEATS = { R: 'S', S: 'P', P: 'R' };
const duel = { // órdenes selladas simultáneas (patrón del juego de referencia): al mejor de 2 rondas ganadas
  initial: () => ({ round: 1, score: [0, 0], history: [] }),
  validate: (s, seat, i) => ['R', 'P', 'S'].includes(i) ? true : 'invalid',
  resolve(s, [a, b]) {
    const score = [...s.score];
    if (BEATS[a] === b) score[0]++; else if (BEATS[b] === a) score[1]++;
    return { round: s.round + 1, score, history: [...s.history, [a, b]] };
  },
  status: s => s.score[0] >= 2 ? { over: true, winner: 0 } : s.score[1] >= 2 ? { over: true, winner: 1 } : { over: false },
};

// Red en memoria con cola: nada llega hasta flush(), así se controla el orden y la latencia.
function makeNet() {
  const q = [];
  return { push: fn => q.push(fn), flush() { let n = 0; while (q.length && n++ < 10000) q.shift()(); }, drop() { q.length = 0; }, get size() { return q.length; } };
}
function hostGame(engine, mode, { predict = false, ...opts } = {}) {
  const N = makeNet(); let g0, g1, auth; const events = [];
  auth = createHostAuthority({ engine, mode, onEvent: e => events.push(e), ...opts,
    send: (person, msg) => N.push(() => (person === 0 ? g0 : g1).receive(clone(msg))) });
  g0 = createGuestSession({ engine, predict, send: msg => N.push(() => auth.receive(0, clone(msg))) });
  g1 = createGuestSession({ engine, predict, send: msg => N.push(() => auth.receive(1, clone(msg))) });
  auth.join(0); auth.join(1); N.flush();
  return { auth, g0, g1, N, events };
}
const play = (g, input, N) => { const n = g.input(input); N.flush(); return n; };

test('autoridad del anfitrión: partida completa, el servidor valida y rechaza trampas', () => {
  const { g0, g1, N, events } = hostGame(ttt, 'sequential');
  assert.equal(g0.view.seat, 0); assert.equal(g1.view.seat, 1);
  // entradas ilegales por la vía normal: fuera de turno y celda ocupada
  assert.ok(play(g1, { cell: 0 }, N) !== undefined);
  assert.equal(g1.view.rejected.reason, 'not-your-turn'); assert.equal(g1.view.state.board[0], null);
  play(g0, { cell: 4 }, N);
  play(g1, { cell: 4 }, N); assert.equal(g1.view.rejected.reason, 'invalid', 'celda ocupada');
  // resto de la partida: 0 gana con la diagonal 0-4-8 (celdas 4, 0, 8 de la persona 0)
  play(g1, { cell: 1 }, N); play(g0, { cell: 0 }, N); play(g1, { cell: 2 }, N); play(g0, { cell: 8 }, N);
  assert.equal(g0.view.over, true); assert.equal(g0.view.winner, 'you'); assert.equal(g1.view.winner, 'rival');
  assert.deepEqual(g0.view.wins, [1, 0]); assert.deepEqual(g1.view.wins, [0, 1]);
  assert.deepEqual(events.find(e => e.type === 'over'), { type: 'over', winner: 0 });
  assert.equal(g1.input({ cell: 5 }), null, 'sin entradas tras terminar');
  assert.deepEqual(g0.view.state, g1.view.state, 'los dos ven el mismo estado final');
});

test('entradas hostiles: carga inválida, seq repetido, mensaje enorme y basura no alteran la partida ni tumban al anfitrión', () => {
  const { auth, g0, g1, N } = hostGame(ttt, 'sequential');
  auth.receive(0, { t: 'input', seq: 1, input: { cell: 'x' } }); N.flush();
  assert.equal(g0.view.rejected.reason, 'invalid');
  auth.receive(0, { t: 'input', seq: 1, input: { cell: 4 } }); N.flush();            // seq repetido: se ignora sin responder
  assert.equal(g1.view.state.board[4], null);
  auth.receive(0, { t: 'input', seq: 2, input: { cell: 4, pad: 'x'.repeat(600) } }); N.flush();
  assert.equal(g0.view.rejected.reason, 'too-big');
  auth.receive(0, 'basura'); auth.receive(0, null); auth.receive(7, { t: 'input', seq: 1 }); auth.receive(0, { t: 'otra-cosa' }); N.flush();
  auth.receive(0, { t: 'input', seq: 3, input: { __proto__: { cell: 4 }, cell: 4 } }); N.flush();
  assert.equal(g1.view.state.board[4], 0, 'una entrada válida posterior sí se aplica');
  assert.equal(({}).cell, undefined, 'sin contaminación de prototipos');
});

test('revancha: exige a los dos, intercambia asientos y el marcador sigue a la persona', () => {
  const { g0, g1, N } = hostGame(ttt, 'sequential');
  for (const [g, cell] of [[g0, 0], [g1, 3], [g0, 1], [g1, 4], [g0, 2]]) play(g, { cell }, N);
  assert.equal(g0.view.winner, 'you');
  g0.rematch(); N.flush();
  assert.equal(g1.view.rematch[1], true, 'el rival ve que pediste revancha');
  assert.equal(g0.view.over, true, 'sigue terminada hasta que acepten los dos');
  g1.rematch(); N.flush();
  assert.equal(g0.view.gameNo, 2); assert.equal(g0.view.over, false);
  assert.equal(g0.view.seat, 1); assert.equal(g1.view.seat, 0, 'asientos intercambiados');
  assert.deepEqual(g0.view.wins, [1, 0], 'la victoria sigue a la persona 0');
  assert.deepEqual(g0.view.state, ttt.initial());
  play(g1, { cell: 4 }, N); assert.equal(g0.view.state.board[4], 0);         // persona 1 ahora es el asiento 0 y mueve
  g0.rematch(); N.flush(); assert.equal(g0.view.rejected.reason, 'in-progress', 'no hay revancha a media partida');
});

test('predicción y reconciliación: se ve al instante y converge con la verdad del anfitrión', () => {
  const { g0, g1, N } = hostGame(ttt, 'sequential', { predict: true });
  g0.input({ cell: 4 });
  assert.equal(g0.view.state.board[4], 0, 'predicción local inmediata');
  assert.equal(g0.view.pending, 1); assert.equal(g0.view.confirmedState.board[4], null);
  assert.equal(g1.view.state.board[4], null, 'el rival aún no sabe nada');
  N.flush();
  assert.equal(g0.view.pending, 0); assert.equal(g0.view.confirmedState.board[4], 0); assert.equal(g1.view.state.board[4], 0);
  // jugada local inválida: ni se envía
  assert.equal(g0.input({ cell: 4 }), null);
  assert.equal(N.size, 0);
});

test('reconciliación con conflicto: dos jugadores toman la misma celda a la vez; gana el que llega primero al anfitrión', () => {
  const { g0, g1, N } = hostGame(claim, 'sequential', { predict: true });
  g1.input({ cell: 2 }); g0.input({ cell: 2 });                 // cruzados en la red
  assert.equal(g0.view.state.cells[2], 0, 'cada uno ve su predicción'); assert.equal(g1.view.state.cells[2], 1);
  N.flush();                                                    // el anfitrión procesa primero a la persona 1
  assert.equal(g1.view.state.cells[2], 1); assert.equal(g1.view.pending, 0);
  assert.equal(g0.view.state.cells[2], 1, 'la predicción de g0 se corrige a la verdad');
  assert.equal(g0.view.rejected.reason, 'taken'); assert.equal(g0.view.pending, 0);
  assert.deepEqual(g0.view.state, g1.view.state);
});

test('órdenes selladas (patrón del juego de referencia): el rival solo ve "sellada"; se resuelve al sellar los dos', () => {
  const { auth, g0, g1, N, events } = hostGame(duel, 'simultaneous');
  play(g0, 'R', N);
  assert.deepEqual(g0.view.sealed, [true, false]); assert.equal(g0.view.myInput, 'R');
  assert.deepEqual(g1.view.sealed, [false, true]); assert.equal(g1.view.myInput, null);
  assert.ok(!JSON.stringify(g1.view).includes('"R"'), 'la orden del rival no se filtra');
  assert.equal(g1.view.state.round, 1, 'nada se resuelve con una sola orden');
  play(g0, 'P', N); assert.equal(g0.view.rejected.reason, 'sealed', 'no se resella');
  play(g1, 'Z', N); assert.equal(g1.view.rejected.reason, 'invalid');
  play(g1, 'S', N);                                             // R rompe S: punto para el asiento 0
  assert.equal(g0.view.state.round, 2); assert.deepEqual(g0.view.state.score, [1, 0]);
  assert.deepEqual(g0.view.sealed, [false, false]);
  play(g0, 'R', N); play(g1, 'S', N);
  assert.equal(g0.view.over, true); assert.equal(g0.view.winner, 'you'); assert.equal(events.at(-1).type, 'over');
  g0.rematch(); g1.rematch(); N.flush();
  assert.equal(g1.view.seat, 0); assert.deepEqual(g1.view.wins, [0, 1]);
  assert.equal(auth.snapshot.gameNo, 2);
});

test('desconexión y abandono: hay gracia para volver con el estado intacto; si no, pierde por abandono', async () => {
  const { auth, g0, g1, N, events } = hostGame(ttt, 'sequential', { graceMs: 80 });
  play(g0, { cell: 4 }, N);
  auth.leave(1); N.flush();
  assert.equal(g0.view.online[1], false, 'el rival aparece desconectado');
  play(g0, { cell: 0 }, N);
  assert.equal(g0.view.rejected.reason, 'rival-offline');
  auth.join(1); g1.resync(); N.flush();                          // vuelve a tiempo (p. ej. el DataChannel pasó a relevo)
  assert.equal(g0.view.online[1], true); assert.equal(g1.view.state.board[4], 0, 'recupera el estado con resync');
  play(g1, { cell: 0 }, N); assert.equal(g0.view.state.board[0], 1);
  auth.leave(1); N.flush();
  await sleep(160); N.flush();
  assert.equal(g0.view.over, true); assert.equal(g0.view.end, 'forfeit'); assert.equal(g0.view.winner, 'you');
  assert.deepEqual(g0.view.wins, [1, 0]);
  assert.deepEqual(events.find(e => e.type === 'forfeit'), { type: 'forfeit', person: 1 });
  auth.dispose();
});

// --- lockstep ----------------------------------------------------------------------------------
const racer = { // determinista: cada asiento suma sus pasos; gana quien llegue a 6
  initial: () => ({ p: [0, 0] }),
  step: (s, [a, b]) => ({ p: [s.p[0] + (a?.dx ?? 0), s.p[1] + (b?.dx ?? 0)] }),
  status: s => s.p[0] >= 6 ? { over: true, winner: 0 } : s.p[1] >= 6 ? { over: true, winner: 1 } : { over: false },
};
function lockstepPair(engine1 = racer, opts = {}) {
  const N = makeNet(); let a, b; const desyncs = [];
  const link = (to) => msg => N.push(() => to().receive(clone(msg)));
  a = createLockstep({ engine: racer, seat: 0, send: link(() => b), hashEvery: 4, onDesync: d => desyncs.push(['a', d]), ...opts });
  b = createLockstep({ engine: engine1, seat: 1, send: link(() => a), hashEvery: 4, onDesync: d => desyncs.push(['b', d]), ...opts });
  return { a, b, N, desyncs };
}
function run(p, frames) { for (let i = 0; i < frames; i++) { p.a.advance(); p.b.advance(); p.N.flush(); } }

test('lockstep: dos pares avanzan al mismo ritmo con las mismas entradas y llegan al mismo estado final', () => {
  const p = lockstepPair();
  assert.equal(p.a.advance(), false, 'sin entradas del rival espera'); assert.equal(p.a.stalled, true);
  for (let i = 0; i < 12 && !p.a.over; i++) {
    if (i % 2 === 0) p.a.input({ dx: 1 }); else p.b.input({ dx: 1 });
    run(p, 1);
    if (p.a.tick === p.b.tick) assert.deepEqual(p.a.state, p.b.state);
  }
  run(p, 30);
  assert.equal(p.a.over, true); assert.equal(p.b.over, true);
  assert.deepEqual(p.a.state, p.b.state); assert.equal(p.a.tick, p.b.tick);
  assert.equal(p.desyncs.length, 0, 'sin falsos positivos de desincronización');
});

test('lockstep: un corte de red detiene sin romper; resend() reenvía lo perdido y se reanuda sin desincronizar', () => {
  const p = lockstepPair();
  run(p, 6);
  const before = p.a.tick;
  p.a.input({ dx: 1 }); p.b.input({ dx: 1 });
  for (let i = 0; i < 6; i++) { p.a.advance(); p.b.advance(); p.N.drop(); }   // corte: todo lo enviado se pierde
  assert.ok(p.a.stalled && p.b.stalled, 'los dos esperan');
  const stuck = p.a.tick;
  p.a.resend(); p.b.resend(); p.N.flush();                              // el transporte vuelve
  run(p, 20);
  assert.ok(p.a.tick > stuck && p.b.tick > stuck && stuck >= before);
  assert.deepEqual(p.a.state, p.b.state); assert.equal(p.desyncs.length, 0);
});

test('lockstep: detecta desincronización por hash y el anfitrión la corrige con un snapshot', () => {
  const buggy = { ...racer, step: (s, [a, b]) => ({ p: [s.p[0] + (a?.dx ?? 0), s.p[1] + (b?.dx ?? 0) + (s.p[0] === 2 ? 1 : 0)] }) }; // diverge
  const p = lockstepPair(buggy);
  p.a.input({ dx: 1 });
  run(p, 3); p.a.input({ dx: 1 }); run(p, 3); p.a.input({ dx: 1 }); run(p, 20);
  assert.ok(p.desyncs.length >= 1, 'se detecta la divergencia');
  assert.ok(p.a.halted && p.b.halted, 'se detiene en lugar de seguir con estados distintos');
  p.a.sendSnapshot(); p.N.flush();
  assert.equal(p.a.halted, false); assert.equal(p.b.halted, false);
  assert.deepEqual(p.a.state, p.b.state, 'el invitado adopta el estado del anfitrión');
  assert.equal(p.a.tick, p.b.tick);
  p.b.sendSnapshot(); // el invitado no puede imponer estado
  assert.equal(p.N.size, 0);
});

test('lockstep: entradas viejas, futuras o de otra época se ignoran; revancha intercambia asientos', () => {
  const p = lockstepPair();
  p.a.receive({ t: 'ls-input', epoch: 0, tick: 9999, input: { dx: 1 } });   // demasiado adelante
  p.a.receive({ t: 'ls-input', epoch: 7, tick: 1, input: { dx: 1 } });      // otra época
  p.a.receive('basura'); p.a.receive({ t: 'ls-input', epoch: 0, tick: 'x' });
  run(p, 2); assert.deepEqual(p.a.state, p.b.state);
  for (let i = 0; i < 40 && !p.a.over; i++) { p.a.input({ dx: 1 }); run(p, 1); }
  run(p, 10);
  assert.equal(p.a.over, true); assert.equal(p.a.state.p[0] >= 6, true);
  p.a.rematch(); p.N.flush();
  assert.equal(p.a.over, true);
  p.b.rematch(); p.N.flush();
  assert.equal(p.a.over, false); assert.equal(p.b.over, false);
  assert.equal(p.a.seat, 1); assert.equal(p.b.seat, 0); assert.equal(p.a.tick, 0);
  assert.deepEqual(p.a.state, racer.initial());
  run(p, 3); assert.equal(p.a.tick > 0 && p.a.tick === p.b.tick, true, 'siguen en sincronía tras el cambio de asiento');
});
