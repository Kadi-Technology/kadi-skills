# Seguridad, privacidad y pruebas

## 1. Modelo de amenazas y controles

El escenario es 1v1 entre personas que comparten WiFi, con un servidor de señalización que ve metadatos y un posible atacante en internet o en la misma red.

| Amenaza | Control implementado | Dónde |
|---|---|---|
| Alguien de otra red ve a mis dispositivos o me invita | Grupos por HMAC de la IP pública (sal aleatoria por proceso) + juego; `peers` solo lista a tu grupo; invitar a otro grupo responde `not-found` | `signaling-server.mjs`: `networkKey`, `gidOf` |
| Suplantar otra red con una cabecera `X-Forwarded-For` falsa | La cabecera solo se usa con `trustProxy: true` y se toma la entrada número `proxyHops` desde el final; sin proxy declarado se ignora y se avisa una vez si llega | `clientIp` |
| Exponer IPs privadas o públicas a otros | Ningún mensaje del servidor lleva IPs; no se registran. Los SDP/ICE solo se reenvían al rival ya emparejado y después de aceptar; los candidatos `srflx`/`relay`/`prflx` se descartan salvo `allowRemoteCandidates` | `H.signal`, `H.invite-accept` |
| Revelar la IP pública al rival o a un STUN | `iceServers: []` por defecto: solo candidatos `host` (los navegadores los ofuscan con un nombre `.local` por mDNS) | `DEFAULTS.iceServers`, `lan-client.js` |
| Adivinar o forzar códigos de sala | Código de 5 caracteres de 32 símbolos (≈ 33,5 millones), un solo uso, caduca en `roomTtlMs` (5 min), mismo `game`, y bloqueo tras `codeFailLimit` fallos por red y minuto | `room-create`, `room-join`, `codeFailed` |
| Adivinar el PIN de una mesa LAN | Comparación en tiempo constante y el mismo bloqueo por fallos | `hello` (`pin`) |
| Inundación de mensajes | Cubo de fichas por conexión: control (`ctlBurst`/`ctlPerSec`) y relevo (`relayBurst`/`relayPerSec`); cierre `4429` si persiste | `bucket`, `onMessage` |
| Mensajes enormes | `maxPayload` de `ws` (16 KB) → cierre `1009`; `data` del relevo ≤ 4 KB; SDP ≤ 12 KB; candidato ≤ 600; entrada de juego ≤ 512 bytes | `maxMessageBytes`, `maxRelayBytes`, `MAX_INPUT_BYTES` |
| Agotar recursos | `maxPeers`, `maxGroupSize`, `maxConnsPerIp`, hasta 4 invitaciones entrantes y una saliente, timeouts de hello, cola, invitación y sala, latido con terminación de conexiones muertas | opciones del servidor |
| Saltarse el proxy y hablar directo con el origen | `originSecret`: el proxy añade `x-origin-secret` (el navegador no puede) y el origen exige el valor; `allowedOrigins` limita el `Origin`; en la nube, que el grupo de seguridad solo abra el puerto al proxy | `upgrade` |
| Trampas del cliente | El anfitrión valida cada entrada con `engine.validate`, ignora `seq` repetidos, exige que el rival esté conectado y no filtra órdenes selladas | `game-session.js` |
| Anfitrión tramposo (P2P) | No se evita: es una partida entre conocidos. Para competir en serio, usa el host LAN con `engine` o un servidor autoritativo | `lan-host-mdns.mjs` |
| XSS por alias | El servidor recorta a 24 caracteres y elimina control, `<` y `>`; el cliente debe pintar con `textContent` | `cleanAlias` |
| Path traversal en la ruta B | `path.resolve` + comprobación de prefijo, `%00` rechazado, solo `GET`/`HEAD`, cabeceras `nosniff`, CSP y `frame-ancestors 'none'` | `httpHandler` |
| Anuncios falsos en la LAN | `parseAnnounce` valida forma, tamaño, puerto, `game` e ignora orígenes que no sean IP privada | `lan-host-mdns.mjs` |
| `__proto__` y similares en entradas | Las entradas se clonan con `JSON.parse(JSON.stringify())` y las valida el motor con una lista de campos permitidos | `HostAuthority` |

### Lo que el motor del juego debe hacer

- `validate` debe **aceptar solo la forma esperada** (tipos, rangos, campos conocidos) y comprobar legalidad contra el estado actual. No uses `Object.assign` ni fusiones sobre objetos de entrada.
- Nada de `Math.random()`, `Date.now()` ni orden de iteración no determinista dentro de `apply`, `resolve` ni `step`. Si necesitas azar, genera una semilla en el anfitrión y envíala en el estado.
- El motor debe ser **el mismo archivo** en cliente y anfitrión; añade una prueba que compare hashes si hay copias.

## 2. Privacidad: lo que hay que decir al usuario

- **El servidor de señalización ve la IP pública de cada dispositivo** (es técnicamente inevitable para agrupar). La plantilla no la guarda ni la registra; si tu infraestructura (proxy, CDN, balanceador) registra IPs, dilo en tu aviso de privacidad. Una IP es dato personal en varias jurisdicciones.
- **Quien comparte tu red pública te ve en la lista** (alias y estado). En redes grandes (CGNAT, universidades, cafeterías) pueden ser desconocidos. Muestra un aviso la primera vez y deja un modo "invisible" (no aparecer en la lista y solo jugar con código) si el juego lo necesita.
- **Los SDP contienen las IP de LAN de los dispositivos** (o un nombre `.local` si el navegador ofusca). Solo se envían al rival tras aceptar la invitación o entrar en la cola, y el servidor no los guarda. Si activas `allowRemoteCandidates` o añades STUN/TURN, las IP públicas sí se revelan al rival y al proveedor del STUN: documéntalo.
- **Si WebRTC falla, los mensajes del juego pasan por tu servidor** (relevo). Muestra el estado "modo relevo" en la interfaz y no envíes por ahí nada que no sea del juego.
- **Salas con código entre redes distintas** terminan en relevo (sin STUN). Es esperable.
- **Alias libre = texto sin moderar.** No añadas chat sin moderación ni filtro; si el juego es para menores, no uses alias libres ni muestres la lista de red sin consentimiento del tutor.
- **Ruta B en http/ws**: el tráfico no va cifrado. Úsala en una red de confianza (no en WiFi público) y comunícalo. El PIN limita quién entra, no cifra.
- No registres `req.headers`, `x-forwarded-for` ni cuerpos de mensajes. Registra solo contadores y códigos de error.

## 3. Lista de verificación de despliegue (ruta A)

1. Node ≥ 20 detrás de TLS (WSS) con un proxy que reenvíe `Upgrade` y **sobrescriba** `X-Forwarded-For` con la IP real del cliente.
2. `TRUST_PROXY=1` y `PROXY_HOPS` igual al número de proxies de confianza que añaden entradas a la cabecera (con un CDN que fija la IP real en una cabecera propia, usa `clientIpHeader`).
3. Define `ORIGIN_SECRET` en el entorno (nunca en el repositorio ni en el código) y haz que el proxy envíe `x-origin-secret`. Restringe el puerto del origen a la IP del proxy.
4. `ALLOWED_ORIGINS` con el origen exacto de tu página de juego.
5. Una sola instancia basta: el estado es efímero y en memoria. Si escalas a varias instancias, el grupo debe vivir en la misma (afinidad por IP) o en un almacén compartido; la plantilla no lo trae resuelto.
6. Comprueba `GET /healthz` y que la respuesta no trae IPs. Prueba con tres dispositivos (apartado 5).
7. Confirma que el proxy no guarda cabeceras de cliente más tiempo del que declara tu aviso de privacidad.

## 4. Pruebas automáticas

```powershell
cd templates
npm install          # solo instala ws
npm test             # node --test sobre ../tests/*.test.mjs
```

Para integrar en tu proyecto: copia `templates/` a la carpeta del servidor y `tests/` a la de pruebas, ajusta las rutas `../templates/...` de los `import` y reemplaza los motores de ejemplo (tres en raya, "reclamar celdas", duelo sellado, carrera lockstep) por el de tu juego.

| Archivo | Qué cubre |
|---|---|
| `tests/signaling.test.mjs` | `networkKey` (IPv4, IPv6 /64, privadas); **agrupación por red** con dos clientes de la misma IP y uno de otra (y otro juego); cabecera ignorada sin `trustProxy`; cola 1v1 (emparejamiento FIFO, otra red espera, roles, sin STUN); **timeout** y cancelación de la cola; invitación (aceptar, rechazar, cancelar, timeout, otra red, ocupado, uno mismo); relevo SDP/ICE (solo entre los dos, validaciones, descarte de `srflx`); **relevo de datos** (`relay-open`, `relay-ready`, límites, intruso); salas con código (otra red, un solo uso, caducidad, fuerza bruta, otro juego); límites (mensaje grande, tasa, binario, JSON roto, hello obligatorio, hello tardío); conexiones por IP, grupo lleno, `bad-game`, PIN; secreto de origen y `Origin`; `/healthz` sin IPs; reanudación y caducidad; salida limpia. |
| `tests/client.test.mjs` | `lan-client.js` contra el servidor real con un doble de `RTCPeerConnection`: P2P feliz sin tocar el relevo y sin `iceServers`; invitar (aceptar, rechazar, cancelar, timeout, otra red); buscar rival (timeout, cancelación); **salida a relevo** por timeout, sin WebRTC y con `forceRelay`; pérdida con ICE restart exitoso y fallido; reconexión del WebSocket con misma identidad; sala con código entre redes; cierre y nueva búsqueda; PIN y servidor caído. |
| `tests/game-session.test.mjs` | Autoridad del anfitrión (partida completa, trampas, entradas hostiles); predicción y **reconciliación** (incluido el conflicto entre dos jugadores); órdenes selladas simultáneas; **desconexión, regreso y abandono**; **revancha** con cambio de asiento; lockstep (sincronía, corte y `resend`, detección de desincronización y snapshot, épocas, revancha). |
| `tests/lan-host.test.mjs` | DNS-SD (codificación, decodificación, qué contestar), responder mDNS con socket simulado, anuncio y descubrimiento UDP, `parseAnnounce` hostil, `lanAddresses`, HTTP del host (traversal, métodos, `/info`, CSP), PIN, partida completa con el host como autoridad (revancha, abandono) y como relevo. |

### Lo que las pruebas automáticas no verifican (dilo en tu informe)

- El motor **WebRTC real** de un navegador: el cliente se prueba con un doble. Falta una prueba E2E con dos navegadores (Playwright con dos contextos) para `RTCPeerConnection` real, candidatos mDNS `.local` y `iceRestart`.
- Multicast real en una red real: el responder mDNS se prueba con un socket simulado y el UDP, en `127.0.0.1`. Que la red permita 5353 y el broadcast depende del router.
- Redes con CGNAT, VPN o aislamiento de clientes.
- Rendimiento con muchos grupos o carga sostenida.

## 5. Pruebas manuales (obligatorias antes de dar la función por terminada)

| # | Escenario | Resultado esperado |
|---|---|---|
| 1 | Dos dispositivos en el mismo WiFi abren el juego | Cada uno ve al otro en la lista |
| 2 | Un tercer dispositivo con datos móviles | No ve a nadie; "Buscar rival" no lo empareja con los otros dos |
| 3 | Los dos pulsan "Buscar rival" | Emparejan; el indicador dice "P2P" (`transport === 'p2p'`) |
| 4 | Con un dispositivo ya en partida, otro lo invita | Responde "ocupado" |
| 5 | Invitar, rechazar, ignorar 20 s, cancelar | Cada caso libera a los dos |
| 6 | Activar aislamiento de clientes en el router (o `forceRelay`) | Pasa a relevo en ≈ 8 s y el juego sigue; el indicador dice "relevo" |
| 7 | Apagar el WiFi 5 s en uno de los dispositivos en plena partida | Aparece "reconectando"; al volver la partida sigue con el estado correcto |
| 8 | Cerrar el navegador de uno | El otro ve "rival desconectado" y, pasada la gracia, gana por abandono |
| 9 | Revancha | Solo empieza si aceptan los dos; cambian los asientos |
| 10 | Sala con código desde datos móviles | Entra por relevo |
| 11 | Ruta B: apagar el router de internet, host en la LAN | Se entra por QR/URL y se juega sin internet |
| 12 | Revisar los registros del servidor y el proxy | No hay IPs ni mensajes del juego |

Si no puedes probarlo en dispositivos reales, **dilo explícitamente**: "verificado con pruebas automáticas y dobles, no con navegadores ni redes reales".
