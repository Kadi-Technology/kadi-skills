---
name: kadi-swarm-orchestrator
description: Skill de orquestación multi-agente de grado empresarial v3.0.0 (E2E Overpower Apex) para KADI Technology. Sistema operativo transaccional distribuido sobre Windows NTFS - locks jerárquicos con shadow snapshots, contratos criptográficos duales (Content/Shape SHA-256), destilación AST zero-read (/boost), multiplexor de previsualización (/teamwork-preview) y auto-remediación quirúrgica con circuit breaker. Actívalo cuando una misión requiera múltiples subagentes editando archivos en paralelo dentro del mismo workspace.
---

# KADI Swarm Orchestrator v3.0.0 — Edición E2E Overpower Apex

Kernel: `scripts/swarm_coordinator.py` (Python 3.13, solo librería estándar). Invocación:

    uv run "%USERPROFILE%\.claude\skills\kadi-swarm-orchestrator\scripts\swarm_coordinator.py" <comando> [opciones] --workspace "<ruta>"
    # O bien:
    python "%USERPROFILE%\.claude\skills\kadi-swarm-orchestrator\scripts\swarm_coordinator.py" <comando> [opciones] --workspace "<ruta>"

Toda salida es JSON. Documentación profunda: `docs/ARCHITECTURE_APEX.md`. Plantillas de despacho: `docs/SUBAGENT_PROMPT_TEMPLATES.md`. Auto-verificación: `uv run tests/self_test_swarm.py` (debe terminar con Exit Code 0).

## 1. Matriz inmutable de modelos (Tier S)

| Rol | Olas | Modelos válidos (`--model`) |
|---|---|---|
| Orquestador General (Brain) | 0, 2.5, 3 | `gemini-4-argon-high`, `opus-5.5-xhigh` |
| Subagentes especialistas | 1, 2.5 | `gemini-3.8-flash-high`, `sonnet-5.5-high` |
| QA-RedTeam-Inspector (instancia limpia, cero contexto heredado) | 2 | `gemini-3.8-flash-high`, `sonnet-5.5-high` |

Especialistas: **Data-Architect** (`_data/*.json`, SQL/Prisma, migraciones), **UI-Glassmorphism-Specialist** (CSS vanilla, tokens, NJK/HTML), **Core-Logic-Engineer** (controladores, rutas, APIs, middlewares), **Media-Pipeline-Engineer** (FFmpeg, ChronoSDK, WebGL/Canvas, HTML5).

**Ley Anti-Herencia:** prohibido `Model: "inherit"` y modelos antiguos. El CLI rechaza con **Exit Code 6** cualquier `--model` fuera de la lista blanca (`register-squad`, `publish-contract`, `distill-context`, `emit-remediation`, `rollback-agent` exigen modelo de orquestador; `acquire-lock` exige modelo de subagente y es obligatorio). `--allow-legacy` solo sirve para migraciones y **nunca** habilita `inherit`.

## 2. Exit Codes

| Código | Significado |
|---|---|
| 0 | Operación exitosa |
| 1 | Error general, argumentos inválidos, archivo inexistente, misión no registrada |
| 2 | Conflicto de lock NTFS (`exact`, `ascendant`, `descendant`) |
| 3 | Violación de contrato SHA-256 (Content o Shape) |
| 4 | Agotamiento de puertos TCP |
| 5 | Violación de frontera (artifact fuera del lock del agente) |
| 6 | Violación de política de modelos |
| 7 | Circuit Breaker de auto-remediación (>2 intentos) |

## 3. Comandos

| Comando | Función |
|---|---|
| `register-squad --model <orq> [--reset] [--mission-id id]` | Inicializa `.swarm_state/` y `mission.json` |
| `publish-contract --file f [--name n] [--owner o] [--mode strict\|structural]` | Congela Content-SHA256 + Shape-SHA256 |
| `verify-contract --all \| --name n` | Verifica contra disco; Exit 3 si hay discrepancia |
| `distill-context --agent-id a --territory ... --contracts ... --mission-goal "..."` | Micro-brief AST en `.swarm_state/briefs/<a>_brief.json` |
| `acquire-lock --agent-id a --model <sub> --paths ... [--ttl 1800]` | Poda vencidos, detecta colisiones, shadow snapshot, asigna o renueva (`GRANTED`/`RENEWED`/`EXTENDED`) |
| `heartbeat-lock --agent-id a` | Renueva TTL de los locks del agente |
| `release-lock --agent-id a` | Libera locks (conserva la sombra) |
| `prune-stale-locks` | Purga leases vencidos |
| `acquire-port --agent-id a [--preferred p] [--pid n]` | Sondeo real de sockets 127.0.0.1 (preferido → pool KADI → 5200-5299) |
| `check-preview --agent-id a \| --port p [--path /] [--timeout 10]` | Readiness HTTP 200 + latencia |
| `release-port --agent-id a [--pid n] [--kill-pid n]` | Libera puerto y ejecuta `taskkill /F /T /PID` |
| `submit-report --agent-id a --wave 1 --summary "..." --artifacts ...` | Verifica fronteras (5) y contratos (3), registra reporte |
| `emit-remediation --agent-id a --file f --error "..." [--line n] [--assertion s] [--reopen]` | Ticket quirúrgico; intento 3 ⇒ Exit 7 |
| `rollback-agent --agent-id a --model <orq>` | Restaura el territorio desde la sombra y libera recursos |
| `status-report` | Dashboard completo de la misión |

Pool TCP KADI: `8000, 5173, 5174, 5175, 3000, 3001, 8080, 9222`; respaldo `5200–5299`.

## 4. Contratos duales

- `content_sha256`: bytes crudos normalizados CRLF→LF.
- `shape_sha256`: esqueleto estructural. JSON → árbol de tipos (claves ordenadas, listas como conjunto de esquemas); `.py` → AST público (clases, funciones/métodos sin `_`, argumentos, retorno); `.js/.ts/.mjs` → firmas `export`/`module.exports`; `.css` → tokens `:root` y clases; otros → igual al content.
- `--mode strict` (default): content **y** shape deben coincidir. `--mode structural`: el propietario puede añadir datos/cambiar implementación mientras el shape no mute.

## 5. Protocolo DAG en 5 fases

### OLA 0 — Congelamiento, destilación /boost y partición (secuencial, solo Orquestador)
1. `register-squad --model gemini-4-argon-high|opus-5.5-xhigh` (con `--reset` si hay estado previo).
2. `publish-contract` sobre archivos compartidos (`strict` intocables, `structural` esquemas de datos evolutivos).
3. `acquire-lock` pre-asignando el territorio exclusivo de cada subagente con su modelo (`gemini-3.8-flash-high` / `sonnet-5.5-high`). Dispara el Shadow Snapshot inicial.
4. `distill-context` por subagente → `.swarm_state/briefs/<agent>_brief.json`.
5. Si hay validación web en vivo: `acquire-port --agent-id qa-redteam-001`.

### OLA 1 — Ejecución paralela aislada Zero-Exploration (subagentes)
- Cada subagente recibe su micro-brief y tiene **prohibido** leer/explorar fuera de su territorio.
- Confirma lock con `acquire-lock` (heartbeat idempotente → `RENEWED`). Exit 2 o 6 ⇒ abortar de inmediato.
- Edita dentro del territorio, valida sintaxis local, `submit-report` y `release-lock`.
- Exit 5 en `submit-report` ⇒ revertir todo archivo tocado fuera de la zona antes de liberar el lock.

### OLA 2 — Auditoría cruzada RedTeam y Live Teamwork Preview
- Solo cuando `status-report` muestre `active_locks == 0`. Instancia aislada del QA-RedTeam-Inspector.
- `verify-contract --all`; build/compilación; levantar servidor en el puerto asignado (registrar su PID con `acquire-port --pid`); `check-preview`; contraste WCAG 2.2 AA; enlaces HTTP 200; Playwright dual-viewport (Desktop 1440x900, Móvil 390x844).
- Dictamen con `submit-report --wave 2`; cierre con `release-port` (mata el árbol de procesos).

### OLA 2.5 — Auto-remediación quirúrgica (solo si la Ola 2 falla)
- Orquestador: `emit-remediation --agent-id <culpable> --file <f> --error "<detalle>" [--line n] [--assertion s] [--reopen]`.
- Exit 0 (intento 1 o 2): reabre lock 300 s solo sobre ese archivo (`--reopen` o `acquire-lock --ttl 300`) y despacha al especialista con el ticket; QA re-verifica.
- Exit 7 (circuit breaker): `rollback-agent --agent-id <culpable>` y documentar el incidente al PO.

### OLA 3 — Consolidación, deploy y Handoff al PO (solo Orquestador, 100% silencioso)
- `status-report`: exigir `active_locks == 0`, `active_ports == 0`, todos los contratos `INTACT` (`READY_FOR_HANDOFF`).
- Consolidar o empaquetar en la Bóveda de Releases y aplicar las Leyes Permanentes.

## 6. Leyes permanentes e inquebrantables de cierre

**LEY DE SILENCIO OPERATIVO ABSOLUTO (ZERO VOICE / ZERO CHRONO.EXE).** Prohibido ejecutar `chrono.exe speak`, scripts TTS o cualquier notificación sonora durante o al finalizar las olas. Orquestador y subagentes operan 100% en silencio.

**LEY DE ENTREGA OBLIGATORIA.** Todo reporte final del Orquestador General cierra con una sección titulada exactamente:

`MANUAL ESTRATÉGICO DE SIGUIENTES PASOS PARA EL PO`

que incluye siempre:
- **a) Resumen de Blindaje E2E y Guía de Rollback:** artefactos blindados, estado de contratos Content/Shape, métricas del Flight Recorder y comandos exactos (`rollback-agent` o Git) para revertir al instante.
- **b) 3 a 4 Caminos Estratégicos numerados** (p. ej. A: Captación Comercial y Ventas; B: Despliegue de Nueva Instancia Cliente desde Release Vault; C: Producción y Publicación de Lote en Redes Sociales; D: Evolución de Producto / Siguiente Ola de Ingeniería), cada uno con **Objetivo, Beneficio de Negocio, Nivel de Riesgo (Bajo/Medio/Alto)** y **Prompt/Comando exacto** listo para copiar y pegar.

`submit-report` y `status-report` repiten estas leyes en su JSON (`closing_laws`).

## 7. Reglas operativas rápidas

- Nunca uses `git reset --hard` para deshacer a un solo agente: usa `rollback-agent`.
- No edites `.swarm_state/` a mano; toda escritura pasa por `mutex.lock` + reemplazo atómico.
- Rutas fuera del workspace o dentro de `.swarm_state` son rechazadas (Exit 1).
- Uso de `--allow-legacy` solo en migraciones documentadas.
