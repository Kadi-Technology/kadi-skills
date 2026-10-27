---
name: kadi-lan-multiplayer
description: Implementa multijugador local 1 contra 1 y "buscar rival" para quienes estén conectados al mismo WiFi, en juegos web o con cliente de escritorio/móvil. Ruta principal A - servidor de señalización que agrupa por IP pública (como Snapdrop/PairDrop) y juego por WebRTC DataChannel P2P sin TURN, con cola 1v1, invitaciones, salas con código y relevo por WebSocket si WebRTC falla. Ruta B - host Node en la LAN totalmente offline (mDNS/DNS-SD, broadcast UDP, QR con la IP local). Incluye autoridad del anfitrión o lockstep, reconexión, revancha, límites de tasa y plantillas probadas con node --test. Actívala cuando el usuario pida multijugador local, jugar con alguien en el mismo WiFi o red, lobby o matchmaking LAN, encontrar o invitar a un rival cercano, partida entre dos dispositivos, o convertir un modo bot o de un solo dispositivo en uno de dos jugadores. No la uses para servidores masivos en internet, más de dos jugadores ni shooters de latencia crítica.
---

# kadi-lan-multiplayer: multijugador local 1v1 y "buscar rival" en la misma red

Convierte un juego de un dispositivo en uno donde dos personas conectadas al **mismo WiFi** se encuentran, se retan y juegan 1 contra 1. El patrón sale de un servidor multijugador de producción de KADI (autoridad del servidor, salas con código, emparejamiento, reconexión, revancha, secreto de origen y pruebas) generalizado a LAN. Todo el código de `templates/` es genérico y nuevo, sin datos de ningún producto.

Documentos de apoyo (léelos cuando el paso lo pida, no antes):

- [`references/arquitectura.md`](references/arquitectura.md): diagramas, decisiones A/B, autoridad contra lockstep, flujos.
- [`references/protocolo.md`](references/protocolo.md): todos los mensajes JSON y códigos de error.
- [`references/seguridad-y-pruebas.md`](references/seguridad-y-pruebas.md): amenazas, privacidad, despliegue, pruebas automáticas y manuales.

## Cuándo NO usarla

- Más de 2 jugadores por partida, torneos o ranking: el emparejamiento, la autoridad y los límites están pensados para 1v1.
- Juegos de acción con latencia crítica y mucha simulación física sin motor determinista: usa lockstep solo si el motor es determinista; si no, esta skill no es suficiente.
- Partidas por internet entre desconocidos con cuentas, chat o pagos: necesitas otro diseño (identidad, moderación, servidores autoritativos).
- Si el usuario solo quiere "dos personas en un dispositivo" (hot-seat): ya está resuelto sin red.

## Decisión rápida

| Situación | Ruta | Modelo de juego |
|---|---|---|
| Hay internet y el usuario quiere que "aparezcan" los rivales del mismo WiFi | **A** (recomendada) | Autoridad del anfitrión |
| Evento o lugar sin internet, o no quiere servidor externo | **B** | Autoridad del host LAN (con `engine`) o del cliente `host` |
| Turnos, órdenes selladas, información oculta | A o B | Autoridad del anfitrión (`simultaneous` para órdenes selladas) |
| Tiempo real con motor determinista y estado grande | A | Lockstep (`createLockstep`) |

Si dudas, A + autoridad del anfitrión. Detalle y limitaciones (CGNAT, VPN, IPv6, aislamiento de clientes) en `references/arquitectura.md`.

## Flujo de implementación (paso a paso)

### 0. Reconoce el juego (lee el repositorio, pregunta solo lo que no puedas inferir)

Anota: (a) lenguaje y si corre en navegador, Electron, Unity/Godot web, etc.; (b) si hay un **motor de reglas separable** (estado + acciones) o la lógica está mezclada con el dibujo; (c) tipo de turno (alternado, simultáneo/sellado, tiempo real); (d) si ya existe un modo bot o de dos personas en un dispositivo, que es el punto de enganche; (e) dónde se puede alojar un Node pequeño (A) o qué dispositivo hará de host (B). Pregunta al usuario solo por (e) y por la ruta si de verdad no está claro.

### 1. Aísla el motor de reglas

El multijugador exige un motor **puro y serializable** (contrato completo en la cabecera de `templates/game-session.js`):

```js
engine = {
  initial() -> state,
  validate(state, seat, input) -> true | false | 'motivo',   // nunca confíes en el cliente
  apply(state, seat, input) -> state,                         // modo 'sequential'
  resolve(state, [in0, in1]) -> state,                        // modo 'simultaneous' (órdenes selladas)
  step(state, [in0, in1]) -> state,                           // solo lockstep
  status(state) -> { over, winner: 0 | 1 | null },
  view?(state, seat) -> vista,                                // oculta lo que ese asiento no debe ver
}
```

Si la lógica está mezclada con la interfaz, extráela primero a un módulo sin DOM ni `Math.random`/`Date.now` dentro de las reglas, y deja el modo de un jugador funcionando igual (con una prueba). El mismo archivo debe usarse en cliente y anfitrión.

### 2. Copia las plantillas

Trabaja en un worktree o rama de la tarea; no edites esta skill. Copia desde `templates/`:

| Plantilla | Destino sugerido | Para |
|---|---|---|
| `signaling-server.mjs`, `package.json` | `server/` o `lan/` | Ruta A |
| `lan-client.js` | junto al código de navegador del juego | A y B |
| `game-session.js` | junto al motor (módulo compartido) | A y B |
| `lan-host-mdns.mjs` (+ las anteriores) | `lan-host/` | Ruta B |

Ejecuta `npm install` (solo `ws`). Copia también `tests/` y ajusta las rutas de los `import`.

### 3. Ruta A: servidor de señalización

```powershell
node signaling-server.mjs                       # puerto 8787
```

Variables: `PORT`, `HOST`, `TRUST_PROXY=1`, `PROXY_HOPS`, `ORIGIN_SECRET`, `ALLOWED_ORIGINS`. Reglas que no se negocian:

- En desarrollo, abre el cliente desde dos pestañas o dos dispositivos: todos llegan con la misma IP, así que se ven.
- **Detrás de un proxy o CDN** activa `TRUST_PROXY=1` y deja que el proxy sobrescriba `X-Forwarded-For`. Si no, todo el mundo parecerá estar en la misma red (o ninguno). El servidor avisa si ve la cabecera sin `trustProxy`.
- Servicio público: TLS (`wss://`), `ORIGIN_SECRET` en el entorno del servidor (nunca en el repositorio), `ALLOWED_ORIGINS` con el origen del juego y el puerto solo accesible desde el proxy.
- No registres IPs, cabeceras ni mensajes. Lista de despliegue completa en `references/seguridad-y-pruebas.md`.

### 4. Ruta A: cliente en el juego

```js
import { createLanClient } from './lan-client.js';
import { bindAuthoritativeMatch } from './game-session.js';
import engine from './motor.js';

const lan = createLanClient({ url: 'wss://senal.tu-dominio.example/ws', game: 'mi-juego-v1', alias: nombreElegido });
await lan.connect();

lan.on('peers', lista => ui.rivales(lista));          // [{id, alias, state}] de TU red; pinta alias con textContent
lan.on('status', s => ui.conexion(s));                // 'online' | 'reconnecting' | 'closed'
lan.onInvite(inv => ui.preguntar(`${inv.from.alias} te invita`).then(ok => ok ? inv.accept() : inv.decline()));

lan.onMatch(match => {                                // llega por cola, invitación o sala con código
  const { guest } = bindAuthoritativeMatch(match, { engine, predict: false, onState: vista => ui.pintar(vista) });
  match.onState(s => ui.transporte(s));               // { state, transport: 'p2p' | 'relay', resumed?, reason? }
  ui.alIniciar(guest);                                // guest.input(accion), guest.rematch()
});

botonBuscar.onclick   = () => lan.findRival().catch(e => ui.aviso(e.code));       // 'timeout' | 'cancelled' | ...
botonCancelar.onclick = () => lan.cancelFind();
botonInvitar.onclick  = id => lan.invite(id).catch(e => ui.aviso(e.code));        // 'declined' | 'timeout' | 'busy' | ...
```

Qué debe tener la interfaz (mínimo):

1. Lista "Jugadores en tu red" con estado (libre, buscando, ocupado) y botón Invitar, más botón **Buscar rival** con cancelar y cuenta atrás (`queueTimeoutMs`).
2. Aviso de invitación con Aceptar y Rechazar, que desaparece con `invite-ended`.
3. Indicador de conexión: "P2P" o "Relevo" (`transport`), "Reconectando..." (`state === 'reconnecting'`) y "Rival desconectado" (`view.online[1] === false`).
4. Salida cuando no aparece nadie: "Crear sala con código" (`lan.createRoom()`) y "Entrar con código" (`lan.joinRoom(code)`).
5. Final de partida con **Revancha** (`guest.rematch()`; empieza cuando aceptan los dos).
6. Avisos de privacidad de la primera vez: se ve tu alias a quien comparta tu red; si falla P2P, los mensajes pasan por el servidor.

Para tiempo real determinista, en vez de `bindAuthoritativeMatch` usa `createLockstep({ engine, seat: match.role === 'host' ? 0 : 1, send: m => match.send(m) })`, llama `advance()` en cada cuadro, `match.onMessage(m => ls.receive(m))` y `ls.resend()` cuando `onState` informe `resumed`.

### 5. Ruta B: host LAN offline

```powershell
$env:PUBLIC_DIR = "C:\ruta\al\juego"; $env:GAME = "mi-juego-v1"; $env:ENGINE_MODULE = "./motor.mjs"
node lan-host-mdns.mjs
```

Imprime las URL con la IP privada (y un QR si instalas `qrcode-terminal`), el PIN de la mesa y arranca mDNS (`_kadigame._tcp.local`) y broadcast UDP (`ANNOUNCE=none|mdns|udp|all` para elegir; el motor de ejemplo `tests/fixtures/engine-tictactoe.mjs` muestra el formato de `ENGINE_MODULE`). El mDNS es de mejor esfuerzo: si el puerto 5353 está ocupado o el router bloquea multicast, el host sigue con UDP y QR. Reglas:

- **Los navegadores no descubren mDNS ni UDP.** Los jugadores entran por QR o URL (`http://IP:puerto/`); las apps de escritorio o móvil descubren con `discoverLanHosts()` (Node/Electron) o NSD/Bonjour nativo.
- Sirve la página del juego **desde el host** (`PUBLIC_DIR`) por `http://`: una página `https://` externa no puede abrir `ws://IP-local`.
- La página lee `?pin=` de la URL, lo usa en `createLanClient({ pin })` y lo borra con `history.replaceState`.
- El cliente es el mismo `lan-client.js` (usa `url` por defecto `ws(s)://<mismo origen>/ws`). Con `ENGINE_MODULE` el host es la autoridad: el cliente usa `createGuestSession`, no `bindAuthoritativeMatch`; cablea con `m.onMessage(x => guest.receive(x))` dentro de `onMatch` y `guest.resync()` en `onState` con `resumed`.
- El tráfico es http/ws sin cifrar: solo redes de confianza.

### 6. Reconexión, desconexión y revancha (checklist)

- [ ] `onState` con `reconnecting`: bloquea la entrada y muestra el aviso; al volver con `resumed: true`, el invitado llama `resync()` (en `bindAuthoritativeMatch` ya está hecho).
- [ ] El anfitrión da `graceMs` (30 s) al rival; si no vuelve, gana por abandono (`view.end === 'forfeit'`).
- [ ] Cerrar a propósito (`match.close()`) termina la partida para ambos; una caída de red no.
- [ ] Revancha solo si aceptan los dos; los asientos se intercambian y el marcador sigue a la persona.
- [ ] Al terminar o cerrar, el cliente puede volver a `findRival()` sin recargar la página.

### 7. Seguridad y privacidad (resumen; el detalle está en la referencia)

Códigos de sala de 5 caracteres de un solo uso con caducidad, límites de tasa y de tamaño, tope de conexiones por IP y de tamaño de grupo, `iceServers: []` (solo candidatos de LAN), descarte de candidatos `srflx`/`relay`, SDP solo entre emparejados y tras aceptar, secreto de origen, validación del anfitrión, alias saneados, sin IPs en mensajes ni registros. **Advierte al usuario** de lo que expone cada ruta (sección 2 de `references/seguridad-y-pruebas.md`).

### 8. Pruebas

```powershell
cd templates; npm install; npm test      # node --test sobre ../tests/*.test.mjs
```

Antes de dar por terminada la función:

1. Adapta `tests/` al juego: sustituye el motor de ejemplo por el real y añade una partida completa de punta a punta (con trampas: fuera de turno, acción ilegal, repetida).
2. Las pruebas existentes deben seguir en verde: agrupación por red con dos clientes de la misma IP y uno de otra, cola 1v1, timeout, invitaciones, relevo SDP/ICE, relevo de datos, reconexión, límites.
3. Haz las pruebas manuales de `references/seguridad-y-pruebas.md` (dos dispositivos en el mismo WiFi y un tercero con datos móviles; aislamiento de clientes; WiFi apagado 5 s).
4. Si el juego es web, añade un E2E con dos contextos de navegador reales (Playwright) para el WebRTC auténtico: las pruebas de la skill usan un doble de `RTCPeerConnection`.

### 9. Qué reportar al terminar

Ruta elegida y por qué; modelo de juego; archivos añadidos o modificados; resultado literal de `npm test`; qué se verificó en dispositivos reales y qué no (di "verificado solo con pruebas automáticas y dobles" si es el caso); límites conocidos (CGNAT, VPN, aislamiento de clientes, instancia única); y los avisos de privacidad que se añadieron a la interfaz.

## Errores frecuentes

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Nadie aparece en la lista aunque estén en el mismo WiFi | IPv4 contra IPv6, VPN o Private Relay, o proxy sin `TRUST_PROXY` | Servidor de señalización solo IPv4; revisar `TRUST_PROXY`/`PROXY_HOPS`; usar sala con código |
| Todos se ven, incluso desconocidos | Proxy mal configurado (todos llegan con la IP del proxy) o CGNAT | Corregir `X-Forwarded-For`; limitar `maxGroupSize`; usar solo salas con código |
| Siempre cae en "relevo" | Aislamiento de clientes del WiFi, multicast/mDNS bloqueado, navegador sin WebRTC | Esperado y funcional; revisar `fallbackReason`; desactivar el aislamiento si el router lo permite |
| `Mixed Content` al abrir `ws://IP` | Página `https://` hablando con el host LAN | Servir la página desde el host (`PUBLIC_DIR`) |
| El QR abre pero no conecta | Cortafuegos del host o el dispositivo está en otra subred/VLAN | Abrir el puerto en el cortafuegos; comprobar que ambos tienen IP del mismo rango |
| La partida se rompe tras reconectar | El invitado no pidió `resync` o el motor no es puro | Usar `bindAuthoritativeMatch`; revisar determinismo y serialización del estado |
| Desincronización en lockstep | `Math.random`/`Date.now`/flotantes en las reglas | Hacer el motor determinista; usar `sendSnapshot()` como red de seguridad |
| `connect()` rechaza con `bad-pin`/`group-full`/`bad-game` | Opciones de `hello` | Corregir `pin`, `game` (`[A-Za-z0-9._-]{1,48}`) o el tamaño del grupo |

## Mapa de la skill

```
kadi-lan-multiplayer/
├─ SKILL.md
├─ references/  arquitectura.md · protocolo.md · seguridad-y-pruebas.md
├─ templates/   signaling-server.mjs · lan-client.js · game-session.js · lan-host-mdns.mjs · package.json
└─ tests/       signaling · client · game-session · lan-host (.test.mjs) + fixtures/public
```
