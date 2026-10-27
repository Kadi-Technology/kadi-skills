// KADI LAN Multiplayer · capa de juego 1v1, independiente del transporte (DataChannel, WebSocket o relevo).
// Dos modelos, a elegir según el juego (ver references/arquitectura.md):
//   1) Autoridad del anfitrión: createHostAuthority (corre en el anfitrión o en el host LAN) + createGuestSession
//      (cliente, con predicción y reconciliación opcionales). Sirve para turnos, órdenes selladas y la mayoría de juegos 1v1.
//   2) Lockstep: createLockstep (corre igual en los dos). Solo viajan entradas; exige un motor 100 % determinista.
// No usa red ni DOM: recibe send() y entrega eventos. Funciona en navegador y en Node.
//
// Contrato del motor (puro, serializable, sin Math.random/Date.now dentro de las reglas):
//   engine.initial()                         -> estado inicial
//   engine.validate(state, seat, input)      -> true | false | "motivo"    (el anfitrión NUNCA confía en el cliente)
//   engine.apply(state, seat, input)         -> estado nuevo               (modo 'sequential')
//   engine.resolve(state, [in0, in1])        -> estado nuevo               (modo 'simultaneous': órdenes selladas)
//   engine.step(state, [in0, in1])           -> estado nuevo               (lockstep; entradas null = sin acción)
//   engine.status(state)                     -> { over: bool, winner: 0 | 1 | null }   (winner = asiento; null = empate)
//   engine.view(state, seat)  (opcional)     -> proyección del estado que puede ver ese asiento
//   engine.hash(state)        (opcional)     -> string; lockstep lo usa para detectar desincronización

const clone = x => JSON.parse(JSON.stringify(x));
const MAX_INPUT_BYTES = 512;

// ================================================================================================
// 1) Autoridad del anfitrión
// ================================================================================================
// "persona" 0 = quien tiene el rol de anfitrión, 1 = invitado. "asiento" es el lado dentro del juego; la revancha puede
// intercambiarlos y el marcador sigue a la persona (como en el juego de referencia de KADI).
export function createHostAuthority(cfg) {
  const { engine, mode = 'sequential', send, onEvent = () => {}, swapOnRematch = true, graceMs = 30000 } = cfg;
  if (!engine || typeof send !== 'function') throw new Error('engine y send son obligatorios');
  const A = {
    state: engine.initial(), seats: [0, 1], online: [false, false], inputs: [null, null], // inputs por asiento
    lastSeq: [0, 0], ack: [0, 0], wins: [0, 0], gameNo: 1, tick: 0, over: false, winner: null,
    rematch: [false, false], timers: [null, null], ended: null,
  };

  function viewFor(person) {
    const seat = A.seats[person], rival = 1 - person;
    const msg = {
      t: 'state', gameNo: A.gameNo, tick: A.tick, seat, ack: A.ack[person],
      state: engine.view ? engine.view(A.state, seat) : A.state,
      over: A.over, winner: !A.over ? null : A.winner === null ? 'draw' : A.winner === seat ? 'you' : 'rival',
      wins: [A.wins[person], A.wins[rival]], rematch: [A.rematch[person], A.rematch[rival]],
      online: [A.online[person], A.online[rival]], end: A.ended,
    };
    if (mode === 'simultaneous') { msg.sealed = [A.inputs[seat] !== null, A.inputs[1 - seat] !== null]; msg.myInput = A.inputs[seat]; }
    return msg;
  }
  const push = person => { if (A.online[person]) send(person, viewFor(person)); };
  const broadcast = () => { push(0); push(1); };
  const reject = (person, seq, reason) => { send(person, { t: 'reject', seq, reason }); push(person); };

  function settle() {
    A.tick++;
    const st = engine.status ? engine.status(A.state) : { over: false };
    if (st.over) {
      A.over = true; A.winner = st.winner ?? null;
      if (A.winner !== null) A.wins[A.seats.indexOf(A.winner)]++;
      onEvent({ type: 'over', winner: A.winner });
    }
  }

  function onInput(person, msg) {
    const seq = msg.seq;
    if (!Number.isInteger(seq) || seq <= A.lastSeq[person]) return;          // duplicado o repetido: se ignora
    A.lastSeq[person] = seq; A.ack[person] = seq;
    if (!A.online[1 - person]) return reject(person, seq, 'rival-offline');
    if (A.over) return reject(person, seq, 'over');
    if (JSON.stringify(msg.input ?? null).length > MAX_INPUT_BYTES) return reject(person, seq, 'too-big');
    const seat = A.seats[person], input = clone(msg.input ?? null);
    const verdict = engine.validate(A.state, seat, input);
    if (verdict !== true) return reject(person, seq, typeof verdict === 'string' ? verdict : 'invalid');
    if (mode === 'simultaneous') {
      if (A.inputs[seat] !== null) return reject(person, seq, 'sealed');
      A.inputs[seat] = input;
      if (A.inputs[0] !== null && A.inputs[1] !== null) { A.state = engine.resolve(A.state, [A.inputs[0], A.inputs[1]]); A.inputs = [null, null]; settle(); }
    } else { A.state = engine.apply(A.state, seat, input); settle(); }
    broadcast();
  }

  function onRematch(person) {
    if (!A.over) return reject(person, 0, 'in-progress');
    A.rematch[person] = true;
    if (A.rematch[0] && A.rematch[1]) {
      if (swapOnRematch) A.seats.reverse();
      A.state = engine.initial(); A.inputs = [null, null]; A.rematch = [false, false];
      A.over = false; A.winner = null; A.ended = null; A.tick = 0; A.gameNo++;
      onEvent({ type: 'rematch', gameNo: A.gameNo });
    }
    broadcast();
  }

  return {
    join(person) { clearTimeout(A.timers[person]); A.online[person] = true; broadcast(); },
    leave(person) {
      if (!A.online[person]) return;
      A.online[person] = false; broadcast();
      clearTimeout(A.timers[person]);
      if (!A.over) A.timers[person] = setTimeout(() => {      // el rival tiene graceMs para volver; si no, pierde por abandono
        if (A.online[person] || A.over) return;
        A.over = true; A.ended = 'forfeit'; A.winner = A.seats[1 - person]; A.wins[1 - person]++;
        onEvent({ type: 'forfeit', person }); broadcast();
      }, graceMs);
    },
    receive(person, msg) {
      if (!msg || typeof msg !== 'object' || (person !== 0 && person !== 1)) return;
      if (msg.t === 'input') return onInput(person, msg);
      if (msg.t === 'rematch') return onRematch(person);
      if (msg.t === 'resync') return push(person);
    },
    get snapshot() { return viewFor(0); },
    dispose() { A.timers.forEach(clearTimeout); },
  };
}

// Cliente de la autoridad. predict=true (solo modo 'sequential' y juegos de información perfecta): aplica tu entrada
// al instante sobre el último estado confirmado y reconcilia cuando el anfitrión confirma (ack) o rechaza (reject).
export function createGuestSession({ engine = null, send, onState = () => {}, predict = false }) {
  let seq = 0, confirmed = null, pending = [], view = null, lastReject = null;
  function recompute() {
    if (!confirmed) return;
    let s = confirmed.state;
    if (predict && engine && !confirmed.over) {
      const kept = [];
      for (const p of pending) if (engine.validate(s, confirmed.seat, p.input) === true) { s = engine.apply(s, confirmed.seat, p.input); kept.push(p); }
      pending = kept;                                           // lo que ya no es válido sobre la verdad nueva se descarta
    }
    view = { ...confirmed, state: s, confirmedState: confirmed.state, pending: pending.length, rejected: lastReject };
  }
  return {
    receive(msg) {
      if (!msg || typeof msg !== 'object') return;
      if (msg.t === 'state') { confirmed = msg; pending = pending.filter(p => p.seq > msg.ack); recompute(); onState(view); }
      else if (msg.t === 'reject') { pending = pending.filter(p => p.seq !== msg.seq); lastReject = { seq: msg.seq, reason: msg.reason }; recompute(); if (view) onState(view); }
    },
    input(input) {
      if (!confirmed || confirmed.over) return null;
      if (predict && engine && engine.validate(view.state, confirmed.seat, input) !== true) return null;
      const n = ++seq; lastReject = null;
      if (predict) pending.push({ seq: n, input });
      send({ t: 'input', seq: n, input });
      recompute(); onState(view);
      return n;
    },
    rematch() { send({ t: 'rematch' }); },
    resync() { send({ t: 'resync' }); },          // llámalo cuando el transporte vuelva a abrirse tras una caída
    get view() { return view; },
  };
}

// Cablea un emparejamiento de lan-client.js con la autoridad del anfitrión (ruta A, WebRTC o relevo):
//   - rol 'host': ejecuta HostAuthority y juega con su propia GuestSession (sin red entre ellas);
//   - rol 'guest': solo GuestSession. Al reabrirse el transporte (reconexión, paso a relevo) pide el estado completo.
// Devuelve { guest, auth, dispose }. Usa guest.input(...) desde la interfaz y onState para pintar.
export function bindAuthoritativeMatch(match, { engine, mode = 'sequential', predict = false, onState = () => {}, ...authOptions }) {
  const isHost = match.role === 'host';
  let auth = null;
  const guest = createGuestSession({ engine, predict, onState, send: isHost ? m => auth.receive(0, m) : m => match.send(m) });
  if (isHost) {
    auth = createHostAuthority({ engine, mode, ...authOptions, send: (person, m) => (person === 0 ? guest.receive(m) : match.send(m)) });
    match.onMessage(m => auth.receive(1, m));
    match.onPeerStatus(s => (s === 'offline' ? auth.leave(1) : auth.join(1)));  // el servidor de señalización perdió/recuperó al rival (relevo)
    match.onState(s => {
      if (s.state === 'open') auth.join(1);
      else if (s.state === 'reconnecting') auth.leave(1);
      else if (s.state === 'closed') auth.dispose();
    });
    auth.join(0);
  } else {
    match.onMessage(m => guest.receive(m));
    match.onState(s => { if (s.state === 'open') guest.resync(); });
  }
  return { guest, auth, dispose() { auth?.dispose(); } };
}

// ================================================================================================
// 2) Lockstep con entradas (los dos pares ejecutan el motor; la red solo lleva entradas)
// ================================================================================================
const fnv = str => { let h = 0x811c9dc5; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193); } return (h >>> 0).toString(16); };

export function createLockstep({ engine, seat, send, inputDelay = 2, hashEvery = 30, maxAhead = 120, swapOnRematch = true, onTick = () => {}, onDesync = () => {}, onRematch = () => {} }) {
  const hashOf = engine.hash || (s => fnv(JSON.stringify(s)));
  let state = engine.initial(), cur = 0, nextLocal = 0, epoch = 0, halted = false, over = false;
  let inputs = new Map(), hashes = new Map(), pendingLocal = [], sentLog = [], rematchFlags = [false, false];

  const record = (tick, s, input) => {
    let e = inputs.get(tick); if (!e) inputs.set(tick, e = [undefined, undefined]);
    if (e[s] !== undefined) return false; e[s] = input; return true;
  };
  function schedule() {
    while (nextLocal <= cur + inputDelay) {
      const input = pendingLocal.length ? pendingLocal.shift() : null;
      record(nextLocal, seat, input);
      const msg = { t: 'ls-input', epoch, tick: nextLocal, input };
      sentLog.push(msg); if (sentLog.length > 64) sentLog.shift();
      send(msg); nextLocal++;
    }
  }
  function checkpoint() {
    const h = hashOf(state), rec = hashes.get(cur) || {};
    rec.local = h; hashes.set(cur, rec);
    send({ t: 'ls-hash', epoch, tick: cur, hash: h });
    compare(cur);
    for (const k of hashes.keys()) if (k < cur - hashEvery * 4) hashes.delete(k);
  }
  function compare(tick) {
    const r = hashes.get(tick);
    if (r && r.local !== undefined && r.remote !== undefined && r.local !== r.remote) {
      halted = true; onDesync({ tick, local: r.local, remote: r.remote });
    }
  }
  function reset(newState, newTick, newEpoch) {
    state = newState; cur = newTick; nextLocal = newTick; epoch = newEpoch; halted = false; over = false;
    inputs = new Map(); hashes = new Map(); pendingLocal = []; sentLog = [];
  }

  return {
    // Encola una entrada local; se aplicará en el tick (actual + inputDelay).
    input(input) { if (!halted && !over) pendingLocal.push(input); },
    // Llamar una vez por cuadro (p. ej. a 30 o 60 Hz). Devuelve true si el juego avanzó (false = esperando al rival).
    advance(catchUp = 1) {
      if (halted || over) return false;
      let advanced = false;
      for (let i = 0; i < catchUp; i++) {
        schedule();
        const e = inputs.get(cur);
        if (!e || e[0] === undefined || e[1] === undefined) break;
        state = engine.step(state, e); inputs.delete(cur); cur++; advanced = true;
        if (cur % hashEvery === 0) checkpoint();
        const st = engine.status ? engine.status(state) : { over: false };
        if (st.over) { over = true; }
        onTick(state, cur, st);
        if (over) break;
      }
      return advanced;
    },
    receive(msg) {
      if (!msg || typeof msg !== 'object') return;
      const rival = 1 - seat;
      if (msg.t === 'ls-input') {
        if (msg.epoch !== epoch || !Number.isInteger(msg.tick) || msg.tick < cur || msg.tick > cur + maxAhead) return;
        if (JSON.stringify(msg.input ?? null).length > MAX_INPUT_BYTES) return;
        record(msg.tick, rival, msg.input ?? null);
      } else if (msg.t === 'ls-hash') {
        if (msg.epoch !== epoch || !Number.isInteger(msg.tick) || typeof msg.hash !== 'string') return;
        const rec = hashes.get(msg.tick) || {}; rec.remote = msg.hash; hashes.set(msg.tick, rec); compare(msg.tick);
      } else if (msg.t === 'ls-snap') {                         // el anfitrión impone su estado tras una desincronización
        if (seat === 0 || !Number.isInteger(msg.tick) || !Number.isInteger(msg.epoch) || msg.epoch <= epoch) return;
        reset(clone(msg.state), msg.tick, msg.epoch);
      } else if (msg.t === 'ls-rematch') { rematchFlags[rival] = true; maybeRematch(); }
    },
    // Anfitrión (seat 0): resincroniza a los dos desde su estado actual.
    sendSnapshot() {
      if (seat !== 0) return;
      const snap = { t: 'ls-snap', epoch: epoch + 1, tick: cur, state: clone(state) };
      reset(clone(state), cur, snap.epoch); send(snap);
    },
    // Tras reabrir el transporte (p. ej. del DataChannel al relevo): reenvía las últimas entradas por si se perdieron.
    resend() { for (const m of sentLog) send(m); },
    rematch() { if (!over) return; rematchFlags[seat] = true; send({ t: 'ls-rematch', epoch }); maybeRematch(); },
    get state() { return state; }, get tick() { return cur; }, get seat() { return seat; },
    get halted() { return halted; }, get over() { return over; }, get stalled() { const e = inputs.get(cur); return !e || e[1 - seat] === undefined; },
  };
  function maybeRematch() {
    if (!(rematchFlags[0] && rematchFlags[1]) || !over) return;
    rematchFlags = [false, false];
    if (swapOnRematch) seat = 1 - seat;
    reset(engine.initial(), 0, epoch + 1);
    onRematch({ seat });
  }
}
