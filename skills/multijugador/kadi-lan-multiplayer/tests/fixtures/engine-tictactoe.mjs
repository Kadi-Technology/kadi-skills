// Motor de ejemplo (tres en raya) para probar lan-host-mdns.mjs con ENGINE_MODULE. Sustitúyelo por el motor real del juego.
const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
export const mode = 'sequential';
export default {
  initial: () => ({ board: Array(9).fill(null), turn: 0 }),
  validate: (s, seat, i) => !Number.isInteger(i?.cell) || i.cell < 0 || i.cell > 8 || s.board[i.cell] !== null ? 'invalid' : s.turn !== seat ? 'not-your-turn' : true,
  apply: (s, seat, i) => { const board = [...s.board]; board[i.cell] = seat; return { board, turn: 1 - seat }; },
  status(s) {
    for (const [a, b, c] of LINES) if (s.board[a] !== null && s.board[a] === s.board[b] && s.board[b] === s.board[c]) return { over: true, winner: s.board[a] };
    return s.board.every(x => x !== null) ? { over: true, winner: null } : { over: false };
  },
};
