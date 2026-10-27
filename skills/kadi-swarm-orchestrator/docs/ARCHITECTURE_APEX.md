# KADI Swarm v3.0.0 Apex — Arquitectura interna

Sistema operativo transaccional distribuido para enjambres multi-agente sobre **Windows NTFS**, escrito en Python 3.13 con solo librería estándar. Componentes:

| Archivo | Responsabilidad |
|---|---|
| `scripts/swarm_coordinator.py` | Kernel CLI: estado, locks, contratos, reportes, remediación, dashboard |
| `scripts/ast_distiller.py` | Dual hash Content/Shape y micro-briefs AST (/boost) |
| `scripts/shadow_vault.py` | Shadow snapshots y rollback atómico por agente |
| `scripts/preview_multiplexer.py` | Puertos TCP, readiness HTTP, guardián de PIDs (/teamwork-preview) |

## 1. Protocolo MVCC sobre NTFS

El estado vive en `<workspace>/.swarm_state/`:

| Entrada | Contenido |
|---|---|
| `mutex.lock` | Centinela bloqueado en kernel con `msvcrt.locking(fd, LK_NBLCK, 1)` |
| `mission.json` | `mission_id`, `orchestrator_model`, `created_at`, `wave_status`, `workspace_root` |
| `locks.json` | `{agent_id: {model, normalized_paths, display_paths, acquired_at, expires_at, ttl, heartbeat_count, shadow_manifest_path}}` |
| `contracts.json` | `{name: {schema_path, owner, content_sha256, shape_sha256, mode, kind, published_at}}` |
| `ports.json` | Lista de `{port, agent_id, pid, preferred, acquired_at, health_url}` |
| `reports.json` | Reportes cronológicos (Olas 1, 2, 2.5) con `accepted` y `exit_code` |
| `remediations.json` | `{attempts: {agent: n}, tickets: [], incidents: []}` |
| `briefs/` | `<agent_id>_brief.json` generados por el destilador |
| `shadows/` | `<agent_id>/manifest.json` + `files/<ruta relativa>` |
| `events.jsonl` | Flight Recorder append-only |

### Serialización (mutex)
Cada comando (excepto `check-preview`, que solo lee y sondea) se ejecuta dentro de `Mutex`. Si `LK_NBLCK` falla se reintenta con backoff exponencial (`5 ms · 2^n`, máx. 250 ms) más jitter aleatorio igual al retardo, hasta **10 s**; después el CLI sale con Exit 1. El bloqueo cubre el byte 0 de `mutex.lock` (Windows permite bloquear regiones más allá del EOF) y el SO lo libera si el proceso muere, por lo que no hay mutex huérfanos.

### Aislamiento y atomicidad (MVCC por reemplazo)
Cada archivo de estado se escribe **entero** en un temporal del mismo directorio (`tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")`), `flush()` + `os.fsync()`, cierre del descriptor y `os.replace(tmp, destino)`. Un lector concurrente (p. ej. `check-preview`) siempre ve una versión completa — la anterior o la nueva — nunca una escritura parcial. Las copias de archivos de usuario (rollback) usan el mismo patrón (temp en el directorio destino + `os.replace`).

### Leases y colisiones jerárquicas
Cada ruta se resuelve con `(workspace / p).resolve()`, se pasa a minúsculas y se normalizan separadores (NTFS es case-insensitive). Para dos rutas normalizadas `a` (solicitada) y `b` (bloqueada por otro agente):

| Condición | `conflict_type` |
|---|---|
| `a == b` | `exact` |
| `a.startswith(b + os.sep)` (hijo en padre bloqueado) | `descendant` |
| `b.startswith(a + os.sep)` (padre sobre hijo bloqueado) | `ascendant` |

El comparador usa el separador, de modo que `src/ui-other` **no** colisiona con `src/ui`. Respuesta de conflicto (Exit 2): `conflict_type`, `blocking_agent`, `blocking_model`, `conflicting_path`, `remaining_ttl_seconds` (más `all_conflicts`).

Antes de evaluar, `prune_stale_locks` elimina leases con `expires_at <= now`. Si el mismo `agent_id` ya posee las rutas → `RENEWED` (renueva `expires_at`, `heartbeat_count += 1`, sin shadow). Si añade rutas nuevas → `EXTENDED`; si no tenía lease → `GRANTED`. Esto cubre el patrón "el Orquestador pre-asigna en Ola 0 y el subagente confirma en Ola 1".

### Shadow Vault
`acquire-lock` llama a `ShadowVault.capture_snapshot` solo para rutas **nuevas** del lease (un territorio ya capturado no se recaptura; de lo contrario un heartbeat sobrescribiría la copia limpia con archivos ya editados, y la remediación de Ola 2.5 perdería su punto de restauración). `manifest.json` registra `territories`, `territory_existed`, `files` (SHA-256 binario y tamaño originales) y `dirs`. `rollback-agent` restaura archivos modificados o borrados, elimina archivos y directorios nuevos del territorio y libera locks y puertos, sin tocar rutas de otros agentes. `release-lock` conserva la sombra hasta cerrar la misión; `register-squad --reset` la elimina.

## 2. Content-Hash vs Shape-Hash

| | `content_sha256` | `shape_sha256` |
|---|---|---|
| Entrada | Bytes del archivo con CRLF→LF | Esqueleto estructural serializado canónicamente (`sort_keys`, separadores compactos) con prefijo de versión `kadi-shape/1` |
| Cambia si… | Cambia cualquier byte (salvo EOL) | Cambia la interfaz |

| Tipo | Qué entra en el shape |
|---|---|
| `.json` | Valores → nombre de tipo (`str,int,float,bool,null`); dicts con claves ordenadas; listas como conjunto ordenado de esquemas únicos (`{"__list__": [...]}`) |
| `.py` | `ast`: clases y funciones/métodos públicos (sin `_`), nombres de argumentos (`*args`, `**kw`), `async`, anotación de retorno |
| `.js .ts .mjs` | Regex deterministas sobre texto sin comentarios: `export function/class/const/let/var/interface/type/enum`, `export {…}`, `export default`, `module.exports`, `exports.x` (ordenado) |
| `.css` | Nombres de custom properties en `:root` + nombres de clases de selectores (sin valores) |
| otros / sintaxis inválida | `shape == content` |

Modos de contrato: **strict** exige ambos hashes; **structural** exige solo el shape (el propietario agrega datos o cambia implementación). `verify-contract` informa `shape_changed` y `content_changed`; `submit-report` rechaza (Exit 3) si algún contrato dejó de estar `INTACT`.

## 3. Micro-brief AST (`distill-context`)
`micro_brief.json` (`kadi-micro-brief/3.0`) contiene: árbol de territorio con tamaño y `sha256_16`, contratos de solo lectura con hashes completos y esqueleto (claves JSON, tokens `:root`, firmas exportadas; nunca cuerpos), reglas de frontera y comandos exactos de inicio/cierre, y `token_estimate` (caracteres/4). Se imprime comprimido en stdout y se guarda en `briefs/`.

## 4. Flight Recorder (`events.jsonl`)
Una línea JSON por operación CLI, append-only:

    {"ts":"2026-10-16T00:44:02.123456-06:00","command":"acquire-lock","agent_id":"ui-glass-001","model":"sonnet-5.5-high","duration_ms":41.7,"exit_code":0}

`ts` es ISO-8601 con microsegundos. `status-report` agrega `total_events`, `by_command`, `by_exit_code`, `non_zero_exits`, `avg_duration_ms` y los últimos 5 eventos.

## 5. Previsualización y guardián de procesos
Prioridad de puertos: `--preferred` → `[8000, 5173, 5174, 5175, 3000, 3001, 8080, 9222]` → `5200–5299`. Un puerto es libre si no figura en `ports.json`, `connect_ex != 0` **y** un `bind` efímero tiene éxito (sin `SO_REUSEADDR`). `check-preview` sondea con `urllib` (sin proxies) hasta HTTP 200 o timeout y reporta `latency_ms`. `release-port` termina el árbol de procesos con `taskkill /F /T /PID` para el PID registrado (o `--pid`/`--kill-pid`), protegiendo el PID propio y el del padre.

## 6. Exit Codes (0–7)

| Código | Nombre | Disparador |
|---|---|---|
| 0 | OK | Operación exitosa |
| 1 | ERROR | Argumentos inválidos (incluye errores de `argparse`, forzados a 1), archivo inexistente, ruta fuera del workspace, misión no registrada, timeout de mutex |
| 2 | LOCK_CONFLICT | Colisión `exact`/`ascendant`/`descendant` con otro agente |
| 3 | CONTRACT_VIOLATION | Content o Shape alterado sin autorización (`verify-contract`, `submit-report`) |
| 4 | PORTS_EXHAUSTED | Ningún puerto disponible en el pool |
| 5 | BOUNDARY_VIOLATION | Artifact fuera del lock activo del agente |
| 6 | MODEL_POLICY | Modelo fuera de la Matriz Tier S o `inherit` |
| 7 | CIRCUIT_BREAKER | Tercer ticket de remediación para el mismo agente |

## 7. Remediación (Ola 2.5)
`emit-remediation` incrementa `attempts[agent]` y emite un ticket (`ticket_id`, `attempt`, `file`, `line`, `failed_assertion`, `error`, `expected_diff`, `reopen_ttl_seconds=300`). Con `--reopen` reabre el lock solo sobre ese archivo. El intento 3 registra un incidente y devuelve Exit 7 con el comando exacto de `rollback-agent`.
