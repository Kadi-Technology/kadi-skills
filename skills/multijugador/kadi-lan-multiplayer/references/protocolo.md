# Protocolo de mensajes

Todo es JSON en texto sobre WebSocket (`/ws`), un objeto por mensaje con `type`. Versión del protocolo: `1` (`hello.v`). Los mensajes con `type` desconocido, JSON roto o binarios se rechazan: cinco inválidos cierran la conexión (código `4400`), un mensaje binario cierra con `1003` y uno mayor que `maxMessageBytes` con `1009`.

Convenciones: ids (`id`, `matchId`, `inviteId`) son hex aleatorios y opacos; `alias` es texto sin confianza (24 caracteres, sin `<`, `>` ni control): píntalo siempre con `textContent`; ningún mensaje del servidor contiene IPs.

## 1. Señalización y emparejamiento (cliente ↔ servidor)

### Cliente → servidor

| `type` | Campos | Cuándo | Respuesta |
|---|---|---|---|
| `hello` | `v`, `game` (`[A-Za-z0-9._-]{1,48}`), `alias`, `pin?`, `resume?` | Primer mensaje, obligatorio en 5 s | `welcome` o `error` + cierre `4400` |
| `queue` | | Buscar rival | `queued`; luego `matched` o `queue-ended` |
| `dequeue` | | Cancelar la búsqueda | `queue-ended{reason:'cancelled'}` |
| `invite` | `to` (id del peer) | Invitar a un rival visible | `invite-sent`; el otro recibe `invited`; o `invite-ended` inmediato |
| `invite-cancel` | | Retirar mi invitación | `invite-ended{reason:'cancelled'}` |
| `invite-accept` | `inviteId` | Aceptar | `matched` a ambos |
| `invite-decline` | `inviteId` | Rechazar | `invite-ended{reason:'declined'}` |
| `room-create` | | Sala con código | `room-created{code, ttlMs}` |
| `room-cancel` | | Cerrar mi sala | `room-closed{reason:'cancelled'}` |
| `room-join` | `code` (5 caracteres) | Entrar a una sala | `matched` o `error room-not-found` / `rate` |
| `signal` | `matchId`, `kind: 'offer'\|'answer'\|'ice'`, `data` | Negociar WebRTC | Reenviado al rival como `signal` |
| `relay-open` | `matchId` | WebRTC falló | `relay-ready` a ambos |
| `relay` | `matchId`, `data` | Dato del juego por el servidor | Reenviado al rival como `relay` |
| `leave-match` | `matchId` | Salir de la partida | `match-ended` a ambos |
| `ping` | `t` | Latencia o keepalive | `pong{t}` |
| `bye` | | Salir y olvidar la identidad | Cierre |

Ejemplos:

```json
{ "type": "hello", "v": 1, "game": "mi-juego-v1", "alias": "Ana", "resume": "e3b0c4429...(si reconecta)" }
{ "type": "invite", "to": "9f2c4a1b7d3e5f60" }
{ "type": "signal", "matchId": "a1b2c3d4e5f60718", "kind": "offer", "data": { "type": "offer", "sdp": "v=0..." } }
{ "type": "signal", "matchId": "a1b2c3d4e5f60718", "kind": "ice", "data": { "candidate": "candidate:1 1 udp 2122260223 192.168.1.5 50000 typ host" } }
{ "type": "relay", "matchId": "a1b2c3d4e5f60718", "data": { "t": "input", "seq": 7, "input": { "cell": 4 } } }
```

### Servidor → cliente

| `type` | Campos | Significado |
|---|---|---|
| `welcome` | `v`, `id`, `resume`, `alias`, `resumed`, `state`, `groupSize?`, `iceServers`, `relayOnly`, `limits`, `match?` | Sesión aceptada. `match` solo aparece al reanudar con una partida activa. |
| `peers` | `peers: [{id, alias, state}]` | Lista completa de rivales visibles de mi red y juego (sin mí). `state`: `idle`, `searching`, `busy`. Se reenvía ante cualquier cambio. |
| `queued` | `timeoutMs` | Estás en la cola. |
| `queue-ended` | `reason: 'timeout'\|'cancelled'\|'invite'` | Saliste de la cola. |
| `invite-sent` | `inviteId`, `to`, `timeoutMs` | Tu invitación salió. |
| `invited` | `inviteId`, `from`, `timeoutMs` | Alguien te invita (hasta 4 pendientes). |
| `invite-ended` | `inviteId` (puede ser `null`), `reason` | `declined`, `timeout`, `cancelled`, `busy`, `not-found`, `self`, `left`. Llega a ambos. |
| `room-created` / `room-closed` | `code`, `ttlMs` / `reason: 'cancelled'\|'timeout'\|'offline'` | Ciclo de la sala con código. |
| `matched` | `matchId`, `role: 'host'\|'guest'`, `kind: 'queue'\|'invite'\|'room'`, `peer: {id, alias}`, `transport: 'p2p'\|'relay'`, `iceServers` | Emparejados. `host` ofrece WebRTC y, con autoridad, ejecuta la partida. |
| `signal` | `matchId`, `from`, `kind`, `data` | Señal del rival. |
| `relay-ready` | `matchId` | El relevo está abierto: usa `relay` para enviar. |
| `relay` | `matchId`, `data` | Dato del rival por el servidor. |
| `peer-status` | `matchId`, `status: 'offline'\|'online'` | El rival perdió o recuperó la conexión con el servidor. |
| `match-ended` | `matchId`, `reason: 'left'\|'peer-left'\|'peer-lost'` | Fin del emparejamiento. |
| `pong` | `t` | |
| `error` | `code`, `message`, `ref` | Ver tabla. |

### Códigos de `error`

| `code` | Causa | Acción del cliente |
|---|---|---|
| `bad-json`, `bad-type`, `no-hello` | Mensaje inválido | Corregir el cliente; la conexión se cierra tras 5 |
| `bad-version`, `bad-game`, `bad-pin`, `group-full` | `hello` rechazado (la conexión se cierra con `4400`) | Mostrar el motivo; no reintentar solo |
| `rate` | Demasiados mensajes o códigos de sala incorrectos | Esperar |
| `busy` | Acción no permitida en ese estado | Ignorar o refrescar la UI |
| `invite-gone` | La invitación ya no existe | Quitar el aviso |
| `room-not-found` | Código inexistente, caducado, de otro juego o ya usado | Pedir otro código |
| `no-match`, `relay-closed`, `relay-only`, `bad-signal`, `too-big` | Uso incorrecto de `signal`/`relay` | Bug del cliente |
| `internal` | Excepción en el servidor | Reintentar |

Códigos de cierre propios: `4400` (inválido), `4408` (sin `hello` a tiempo), `4429` (tasa sostenida), `1009` (mensaje grande). HTTP al abrir: `403` (secreto de origen u `Origin`), `404` (ruta distinta de `/ws`), `429` (demasiadas conexiones de esa red), `503` (servidor lleno).

### Máquina de estados de un peer

```
idle ──queue──▶ searching ──(pareja | timeout | dequeue)──▶ idle / matched
idle ──invite─▶ inviting  ──(accept)──▶ matched   (declined | timeout | cancelled) ──▶ idle
idle ──room-create──▶ room ──(room-join de otro)──▶ matched   (cancel | ttl) ──▶ idle
matched ──(leave-match | match-ended)──▶ idle
cualquiera ──cae el WebSocket──▶ offline (gracia resumeGraceMs) ──(resume)──▶ estado anterior
                                                              └──(caduca)──▶ eliminado (+ match-ended 'peer-lost')
```

## 2. Datos de WebRTC

- Un solo `RTCDataChannel` llamado `game`, `ordered: true`, fiable. Lo crea el `host`.
- El contenido de cada mensaje es el mismo JSON que se enviaría por `relay.data`, serializado como texto. Tope de tamaño: `limits.maxRelayBytes` (4096 por defecto) para P2P y relevo.
- Negociación: oferente = `host`; trickle ICE; los candidatos recibidos antes de `setRemoteDescription` se encolan. Tras una pérdida, el `host` renegocia con `iceRestart: true`.

## 3. Juego: autoridad del anfitrión

Cada mensaje lleva `t`. Los envía/recibe `game-session.js` sobre `match.send` / `match.onMessage`.

| Dirección | Mensaje | Campos |
|---|---|---|
| Invitado → anfitrión | `input` | `seq` (entero creciente por persona), `input` (JSON ≤ 512 bytes) |
| Invitado → anfitrión | `rematch` | |
| Invitado → anfitrión | `resync` | Pide el estado completo (tras reconectar) |
| Anfitrión → ambos | `state` | `gameNo`, `tick`, `seat`, `ack` (último `seq` procesado de esa persona), `state` (vista del asiento), `over`, `winner: 'you'\|'rival'\|'draw'\|null`, `wins: [yo, rival]`, `rematch: [yo, rival]`, `online: [yo, rival]`, `end?: 'forfeit'`; en modo `simultaneous` también `sealed: [mía, del rival]` y `myInput` |
| Anfitrión → emisor | `reject` | `seq`, `reason` (`invalid`, `not-your-turn`, `sealed`, `too-big`, `over`, `rival-offline`, `in-progress` o el texto que devuelva `engine.validate`) |

Reglas: un `seq` menor o igual al último procesado se ignora sin responder; toda entrada que no pase `engine.validate` recibe `reject` y el estado vigente; nunca se envía al rival la orden sellada.

## 4. Juego: lockstep

| Mensaje | Campos | Uso |
|---|---|---|
| `ls-input` | `epoch`, `tick`, `input` (`null` = sin acción) | Entrada del emisor para ese tick. Un `ls-input` por tick, aunque sea `null`. |
| `ls-hash` | `epoch`, `tick`, `hash` | Cada `hashEvery` ticks, para detectar divergencias. |
| `ls-snap` | `epoch`, `tick`, `state` | Solo del anfitrión (asiento 0): reimpone su estado tras una desincronización. |
| `ls-rematch` | `epoch` | Se reinicia cuando los dos la envían; los asientos se intercambian. |

Se ignoran los mensajes de otra `epoch`, con `tick` anterior al actual o a más de `maxAhead` (120) ticks.

## 5. Ruta B (host LAN)

- **HTTP**: `GET /` (página del juego desde `publicDir`), `GET /info` → `{ kadi:'lan-host', v:1, name, game, players, pin:boolean, mode:'authority'|'relay', ws:'/ws' }`, `GET /healthz`.
- **WebSocket**: el mismo protocolo de las secciones 1 a 4, con `relayOnly`: `matched.transport = 'relay'` y `relay-ready` llega de inmediato; `signal` se rechaza con `relay-only`. El `hello` debe incluir `pin` si el host lo exige.
- **Con `engine`**: el host crea una `HostAuthority` por emparejamiento y consume los `relay` (no se reenvían al rival); los clientes usan `createGuestSession`. Las personas son `0` = quien tiene el rol `host`, `1` = invitado.
- **mDNS/DNS-SD**: servicio `<nombre>._kadigame._tcp.local`, SRV con puerto y host `<slug>.local`, A con las IPv4 privadas, TXT `v=1`, `game=<id>`, `path=/ws`, `pin=0|1`. TTL 120 s y un paquete con TTL 0 al apagarse.
- **Broadcast UDP** (puerto `41234`, cada 2 s): `{"kadi":"lan-host","v":1,"name":"…","game":"…","port":8787,"path":"/ws","players":0,"pin":true}`. No incluye IP (el receptor usa la dirección de origen) ni el PIN. `parseAnnounce` ignora lo que no venga de una IP privada.
