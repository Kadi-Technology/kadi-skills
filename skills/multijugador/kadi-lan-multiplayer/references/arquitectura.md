# Arquitectura: multijugador local 1 contra 1

Este documento explica el patrón, por qué se eligió y cómo encaja cada plantilla. Los mensajes exactos están en [`protocolo.md`](protocolo.md) y los controles de seguridad en [`seguridad-y-pruebas.md`](seguridad-y-pruebas.md).

## 1. Patrón de origen y cómo se generaliza

La skill parte del multijugador en línea de un juego táctico 1v1 por turnos de KADI (producto privado; aquí solo se publica el patrón y código nuevo). Ese servidor es el modelo de lo que sigue valiendo en una LAN:

| Aspecto | Qué hacía el juego de referencia | Cómo queda en esta skill |
|---|---|---|
| Autoridad | El servidor guarda el estado, valida cada orden contra el motor y solo revela las órdenes selladas al resolver la ronda. El motor es una función pura (`resolve(estado, ordenA, ordenB)`) copiada byte a byte al cliente, con una prueba que compara los hashes. | `game-session.js`: `createHostAuthority` hace de servidor (en el anfitrión P2P o en el host LAN). El motor sigue siendo puro y compartido; `engine.validate` es obligatorio. |
| Protocolo | HTTP + JSON: `POST` para ordenar, Server-Sent Events para empujar la vista de cada asiento. Cada asiento recibe una vista filtrada (`myOrder`, `sealed`). | Un único canal JSON bidireccional (DataChannel, relevo o WebSocket). Mismo filtrado por asiento (`engine.view`, `sealed`, `myInput`). |
| Salas y emparejamiento | Sala con código de 5 caracteres de un alfabeto sin ambiguos, una sola "sala en espera" para el botón buscar rival, tokens de 128 bits por asiento. | Mismo alfabeto y longitud de código; cola FIFO por red y por juego; invitaciones; id de peer y token de reanudación aleatorios. |
| Reconexión | El token del asiento se guarda en `localStorage`; SSE reintenta solo; el servidor marca `connected` y `left` por asiento. | Token de reanudación (`resume`) con periodo de gracia en el servidor, `peer-status` al rival, reintentos con backoff en el cliente y `resync` del estado. |
| Revancha | Los dos deben pedirla; los asientos se intercambian y el marcador sigue a la persona. | Igual (`swapOnRematch`), también en lockstep. |
| Validación | Normaliza la orden a una forma conocida, comprueba que sea una acción legal, rechaza duplicados y órdenes con el rival ausente, límite de cuerpo de 2 KB. | `validate` + `seq` monótono + `MAX_INPUT_BYTES`; el servidor de señalización limita tamaño de mensaje, tasa, conexiones y grupo. |
| Seguridad de origen | El origen solo aceptaba tráfico de un proxy/CDN que añadía un secreto compartido y la IP real del cliente; la IP solo se creía con el secreto. El grupo de seguridad solo abría el puerto a los rangos del CDN. | `originSecret` + `trustProxy` + `proxyHops`: la IP del cliente solo se toma de la cabecera cuando se declara proxy de confianza. |
| Pruebas | Servidor en puerto efímero, partida completa contra el motor de referencia, órdenes ocultas, emparejamiento, 403/404/413, y un E2E con dos navegadores reales. | `tests/`: 50 pruebas de red, señalización, cliente, capa de juego y host LAN. Falta el E2E con navegadores reales (ver "Pruebas manuales" en `seguridad-y-pruebas.md`). |

Lo que **no** se traslada: HTTP + SSE (aquí el canal es bidireccional), CDN, infraestructura en la nube y estado en la nube. En una LAN el reto cambia: no hay IP fija ni DNS, hay que encontrar al rival sin que el usuario escriba nada, y el camino de datos ideal es directo entre los dos dispositivos.

## 2. Diagrama de la ruta recomendada (A)

```
        MISMO WIFI (mismo NAT, misma IP pública)                       OTRA RED
 ┌───────────────┐   ┌───────────────┐                              ┌───────────────┐
 │ Móvil de Ana  │   │ Laptop de Beto│                              │ Vecino        │
 │ lan-client.js │   │ lan-client.js │                              │ lan-client.js │
 └──────┬────────┘   └───────┬───────┘                              └──────┬────────┘
        │  WSS: hello, queue, invite, signal, relay                        │
        └──────────────┬─────┴────────────────────────────────────────────┘
                       ▼
          ┌───────────────────────────────────┐
          │ signaling-server.mjs (Node + ws)  │  agrupa por HMAC(IP pública) + juego
          │  grupo A: {Ana, Beto}   grupo B: {Vecino}   -> nadie ve fuera de su grupo
          │  cola 1v1 | invitaciones | salas con código | relevo SDP/ICE | relevo de datos
          └───────────────────────────────────┘
                       ▲  (solo SDP/ICE y, si falla WebRTC, datos)
 ┌───────────────┐     │      ┌───────────────┐
 │ Ana  (host)   │◀════╧═════▶│ Beto (guest)  │   WebRTC DataChannel P2P, iceServers = []
 │ HostAuthority │  datos del │ GuestSession  │   candidatos "host" = solo la LAN, sin TURN
 │ + motor       │  juego     │ (+ predicción)│   si no conecta en p2pTimeoutMs -> relevo por WSS
 └───────────────┘            └───────────────┘
```

Puntos clave:

- El servidor solo ve metadatos de emparejamiento y, **solo si WebRTC falla**, los mensajes del juego. En el camino feliz el juego nunca sale de la LAN.
- La agrupación es por red, no por usuario. No hay cuentas.
- `iceServers: []` impide candidatos `srflx`/`relay`, así que ni siquiera se revela la IP pública al rival ni a un STUN. El servidor descarta además los candidatos que no sean `host`.
- El anfitrión es quien invitó o quien entró primero a la cola. Es a la vez el oferente de WebRTC y, si el juego usa autoridad, el que ejecuta `HostAuthority`.

## 3. Diagrama de la ruta B (totalmente offline)

```
                  Router o punto de acceso (sin internet)
   ┌──────────────────────┬──────────────────────────┬──────────────────────┐
   │                      │                          │                      │
┌──┴──────────────┐  ┌────┴───────────┐        ┌─────┴──────────┐   ┌───────┴────────┐
│ Dispositivo HOST│  │ Teléfono 1     │        │ Teléfono 2     │   │ App de escritorio│
│ lan-host-mdns   │  │ navegador      │        │ navegador      │   │ o móvil (nativa) │
│  HTTP :8787 /   │◀─┤ escanea el QR  │        │ escribe la URL │   │ discoverLanHosts │
│  WS   :8787 /ws │  │ http://IP:8787 │        │ http://IP:8787 │   │ (UDP) o NSD/Bonjour
│  /info          │  └────────────────┘        └────────────────┘   └──────────────────┘
│  mDNS 5353 UDP  │──── anuncia _kadigame._tcp.local y <nombre>.local ───────▶ apps nativas
│  broadcast 41234│──── JSON sin IP ni PIN cada 2 s ─────────────────────────▶ apps nativas
│  engine (opc.)  │  la página y el WebSocket vienen del MISMO origen http://
└─────────────────┘
```

Por qué así:

- Los navegadores **no pueden** escuchar mDNS ni UDP. La página web no descubre nada por sí sola.
- Cómo se conectan los jugadores: (1) escanear el QR o abrir la URL con la IP local que imprime el host, (2) abrir `http://<nombre>.local:8787` donde el sistema resuelve `.local` (iOS, macOS, Windows 10+; en Android conviene la IP), (3) una app nativa que descubre por NSD/Bonjour o con `discoverLanHosts()` y abre el `url` encontrado.
- La página del juego se sirve desde el propio host por `http://`. Una página `https://` publicada en internet no puede abrir `ws://192.168.x.x` (contenido mixto) y los navegadores empiezan a pedir permiso para acceder a la red local. Servir la página desde el host evita ambos problemas.
- Con `engine`, el host es la autoridad (mismo patrón que el juego de referencia). Sin `engine`, el host solo retransmite y el cliente con rol `host` es la autoridad.

## 4. Decisión: qué ruta usar

| Criterio | A: señalización por IP + WebRTC | B: host LAN offline | C (descartada como principal): intercambio de SDP por QR |
|---|---|---|---|
| Necesita internet | Sí, para llegar al servidor de señalización (aunque el juego viaje por la LAN) | No | No |
| Necesita servidor propio | Sí, un Node pequeño con TLS | No: lo corre un jugador o un dispositivo fijo | No |
| Descubrimiento | Automático por IP pública (como Snapdrop y PairDrop) | Manual (QR o URL) o automático en app nativa | Manual (dos escaneos) |
| Funciona en navegador puro | Sí | Sí, entrando por URL | Sí, con cámara |
| Latencia | La mejor: P2P dentro de la LAN | Un salto por el host | P2P |
| Falla cuando | CGNAT o VPN o IPv4/IPv6 mezclados (grupo mal calculado), aislamiento de clientes del WiFi, multicast bloqueado | El WiFi aísla clientes, no hay IP privada, el cortafuegos del host bloquea el puerto | La cámara falla o el WiFi aísla clientes |
| Salida de emergencia | Relevo por WebSocket y salas con código | Ninguna: si no hay LAN, no hay juego | Ninguna |

**Recomendación**: A como ruta principal (cero fricción para el usuario: abre el juego, ve a quien está en su WiFi, pulsa "Buscar rival"). B se ofrece como modo "sin internet" y para eventos presenciales. C solo si el usuario exige P2P sin ningún servidor ni host y acepta el paso manual; no hay plantilla porque el mismo `lan-client.js` se adapta cambiando el transporte de señales.

Alternativas consideradas y por qué no son la ruta principal:

- **Bluetooth o WiFi Direct**: no están disponibles en navegadores y exigen app nativa en cada plataforma.
- **Servidor en la nube con salas (modelo del juego de referencia)**: no es "local": toda la partida pasa por internet y exige pagar y operar infraestructura. Se conserva solo como relevo de emergencia.
- **Solo códigos de sala**: funciona siempre, pero obliga a teclear. Se mantiene como alternativa cuando la agrupación por red no sirve.

### Limitaciones reales de agrupar por IP pública

- **CGNAT y redes grandes** (datos móviles, universidades, cafeterías): muchos desconocidos comparten IP. El servidor limita el tamaño del grupo (`maxGroupSize`) y la UI debe decir "personas en tu red" sin dar datos personales. Si se prefiere más control, usa solo salas con código.
- **Dos redes con la misma IP pública** (un edificio con un solo NAT): se verán entre sí aunque no sean el mismo WiFi. Por eso la UI avisa antes de invitar y el invitado acepta o rechaza.
- **IPv4 contra IPv6**: un dispositivo puede llegar por IPv6 y el otro por IPv4 y quedar en grupos distintos. El grupo IPv6 usa el prefijo /64. Para evitarlo, haz que el endpoint de señalización sea solo IPv4, o documenta que en ese caso se use sala con código.
- **VPN, iCloud Private Relay o proxy**: cambian la IP vista. Con sala con código se resuelve.
- **Aislamiento de clientes (AP isolation)**: aunque el grupo sea correcto, WebRTC no conectará; el cliente pasa solo al relevo tras `p2pTimeoutMs` y avisa en `fallbackReason`.

## 5. Modelo de juego: autoridad del anfitrión o lockstep

Elige con esta tabla (por juego, no por preferencia):

| Pregunta | Autoridad del anfitrión | Lockstep con entradas |
|---|---|---|
| ¿Turnos, órdenes selladas o información oculta? | Sí, es la opción natural | No |
| ¿Tiempo real con motor determinista (sin `Math.random` ni `Date.now` en las reglas, aritmética entera o fija)? | Posible | Sí, es su caso |
| ¿Estado grande o muchos objetos? | Cuesta enviar el estado | Solo viajan entradas |
| ¿Lo que se ve en pantalla debe ser instantáneo? | Con predicción y reconciliación | Con retardo de entrada (`inputDelay`) |
| ¿Cómo se evita hacer trampa? | El anfitrión valida todo. Un anfitrión malicioso puede hacer trampa: es 1v1 entre conocidos en la misma red | Los dos ejecutan lo mismo; el hash detecta divergencias pero no quién manipula |
| ¿Tolera una desincronización? | Imposible: hay una sola verdad | Debe detectarse (hash) y resolverse con snapshot del anfitrión |
| Recomendación por defecto | **Esta**, salvo que el motor sea determinista y de tiempo real | Solo si el estado no se puede enviar |

### Autoridad del anfitrión (`createHostAuthority` + `createGuestSession`)

```
Invitado                      Anfitrión (HostAuthority + motor)                 Anfitrión (su propia UI)
 input(seq=7, {cell:4}) ───▶  seq > último?  tamaño ok?  engine.validate()?
                              sí: estado = engine.apply()   no: reject(seq=7, motivo) + estado actual
 ◀── state {tick, ack:7, state: view(seat), sealed, wins, online, over, winner}  ──▶ state {…}
 predicción: aplica {cell:4} ya; al llegar state con ack>=7 descarta lo confirmado
             y reaplica lo pendiente sobre el estado confirmado (reconciliación)
```

- El anfitrión también juega: su UI usa una `GuestSession` con `send` conectado directamente a `auth.receive(0, msg)`.
- `engine.view(estado, asiento)` oculta información (órdenes selladas, mano del rival). Modo `simultaneous`: ambas órdenes se guardan selladas y se resuelven juntas, como el patrón de origen.
- **Reconciliación**: la verdad es siempre el último `state` del anfitrión. La predicción solo existe en el cliente y en juegos de información perfecta con modo `sequential`.
- **Desconexión**: `leave(persona)` marca offline y arranca una gracia (`graceMs`); si el rival no vuelve, pierde por abandono. Si vuelve (`join`), recibe el estado completo; el cliente pide `resync()` cada vez que el transporte se reabre (`onState` con `resumed: true`).
- **Revancha**: cuando los dos la piden, se reinicia el motor, se intercambian asientos y el marcador sigue a la persona.

### Lockstep (`createLockstep`)

- Cada cuadro llamas a `advance()`. Las entradas locales se programan en el tick `actual + inputDelay` y se envían; el juego solo avanza si ya están las entradas de los dos para ese tick (si no, `stalled`).
- Cada `hashEvery` ticks se intercambian hashes del estado. Si difieren, el módulo se detiene (`halted`) y llama a `onDesync`; el anfitrión puede llamar `sendSnapshot()` para reimponer su estado (cambia de `epoch`, así se descartan mensajes viejos).
- Tras un corte, `resend()` reenvía las últimas entradas. Los mensajes de otra época o con tick fuera de rango se ignoran.
- Requisitos del motor: sin aleatoriedad no sembrada, sin flotantes dependientes del orden de operaciones, sin lecturas de reloj, orden de iteración fijo.

## 6. Flujos principales

**Buscar rival (cola 1v1):**

```
Ana ─ queue ─▶ servidor: Ana en cola(grupo A, juego X)
Beto ─ queue ─▶ servidor: empareja a Ana y Beto (FIFO)
servidor ─ matched{role: host, peer: Beto, matchId} ─▶ Ana        (Ana ofrece WebRTC)
servidor ─ matched{role: guest, peer: Ana, matchId} ─▶ Beto
Ana ─ signal(offer) ─▶ servidor ─▶ Beto ─ signal(answer) ─▶ servidor ─▶ Ana ; ambos ─ signal(ice host) ─▶
DataChannel abierto  → onState {state: 'open', transport: 'p2p'}
```

**Invitar a un rival visible:** `peers` lista a los otros dispositivos de la red con `idle`, `searching` o `busy`. `invite{to}` envía `invited` al otro; el invitado acepta (`invite-accept`) o rechaza (`invite-decline`). El servidor responde `invite-ended` con `declined`, `timeout`, `cancelled`, `busy`, `not-found`, `self` o `left`. **Los SDP (con las IP de LAN de cada dispositivo) solo se intercambian después de aceptar.**

**Salida si WebRTC falla:** el cliente envía `relay-open` cuando (a) no hay DataChannel en `p2pTimeoutMs`, (b) ICE queda en `failed`, (c) tras una pérdida no se recupera en `restartGraceMs`, o (d) no existe WebRTC. El servidor responde `relay-ready` a los dos y desde ahí `send()` usa `relay`. El tope de tamaño es el mismo, para que el juego no cambie.

**Reanudación:** el cliente guarda `resume`. Si el WebSocket cae, reintenta con backoff; el servidor conserva el peer `resumeGraceMs` y avisa al rival (`peer-status`). Si no vuelve, `match-ended` con `peer-lost`.

## 7. Qué plantilla hace qué

| Archivo | Responsabilidad |
|---|---|
| `templates/signaling-server.mjs` | Grupos por IP, cola, invitaciones, salas, relevo SDP/ICE y de datos, límites, `/healthz`. En modo `groupBy: 'all'` + `relayOnly` es la base del host LAN. |
| `templates/lan-client.js` | API de navegador: `findRival`, `invite`, `onInvite`, `onMatch`, `createRoom`/`joinRoom`; por emparejamiento: `send`, `onMessage`, `onState`, `onPeerStatus`, ICE restart y relevo. |
| `templates/game-session.js` | `createHostAuthority`, `createGuestSession`, `createLockstep`. Sin red ni DOM. |
| `templates/lan-host-mdns.mjs` | Ruta B: HTTP + WS, mDNS/DNS-SD, broadcast UDP, `discoverLanHosts`, QR opcional, autoridad opcional. |
| `tests/*.test.mjs` | Pruebas de todo lo anterior con `node --test`. |
