# kadi-skills

Skills de agentes de **KADI Technology** para [Claude Code](https://claude.com/claude-code). Son las recetas de orquestación, ahorro de costos y despacho que usamos a diario para trabajar con varios agentes a la vez.

Cada carpeta dentro de `skills/` es una skill completa (un `SKILL.md` más sus `scripts/`, `docs/` o `references/` cuando los tiene) y se conserva tal cual para que puedas copiarla sin tocar nada.

## Skills

### Vigentes (`skills/`)

| Skill | Origen | Para qué sirve |
|---|---|---|
| [`kadi-brain-orchestrator`](skills/kadi-brain-orchestrator) | Skill de usuario (`~/.claude/skills`) | Orquestación "Quad-Brain" v3.0: reparte estrategia, arquitectura, síntesis de código y ejecución local entre Fable, Opus, Sonnet y Gemini, con prompt caching. |
| [`kadi-swarm-orchestrator`](skills/kadi-swarm-orchestrator) | Skill de usuario (`~/.claude/skills`) | Kernel transaccional multiagente v3.0.0 sobre Windows NTFS: locks jerárquicos, contratos SHA-256, puertos de previsualización y auto-remediación con circuit breaker. |
| [`kadi-ultra-eco`](skills/kadi-ultra-eco) | Skill de usuario (`~/.claude/skills`) | Ultracode económico: enruta cada subagente al tier más barato capaz (T1 Sonnet, T2 Opus, T3 Fable) en vez de heredar el modelo de la sesión, con calculadora de costos. |
| [`kadi-ticket`](skills/kadi-ticket) | KADI Harness (`harness/skills`) | Emite, valida y registra el Ticket de Despacho del Harness antes de delegar trabajo a un subagente o de tocar un repo. |

### Legado (`legacy/v1.6.0-rc1/`)

Skills de la release `v1.6.0-rc1` (flujo "Core2"). Se publican como referencia histórica; no son el flujo actual.

| Skill | Origen | Para qué sirve |
|---|---|---|
| [`kadi-core2-routing-guardian`](legacy/v1.6.0-rc1/kadi-core2-routing-guardian) | Release `v1.6.0-rc1` | Guardrail principal: separa motor, rol y autoridad, sobre default-deny y handoff canónico. |
| [`kadi-antigravity-qa-guardian`](legacy/v1.6.0-rc1/kadi-antigravity-qa-guardian) | Release `v1.6.0-rc1` | Ejecutor y QA mecánico con Gemini bajo sobres separados (escritura con allowlist, QA solo lectura). |
| [`kadi-engineering-guardian`](legacy/v1.6.0-rc1/kadi-engineering-guardian) | Release `v1.6.0-rc1` | Flujo de ingeniería (Laravel, React, TypeScript, Docker) con zonas críticas y reglas de cambio acotadas. |
| [`kadi-ux-ui-specialist`](legacy/v1.6.0-rc1/kadi-ux-ui-specialist) | Release `v1.6.0-rc1` | Auditoría y refactor UX/UI de interfaces operativas densas y rápidas. |
| [`kadi-prm10k-booster`](legacy/v1.6.0-rc1/kadi-prm10k-booster) | Release `v1.6.0-rc1` | Protocolo PRM-10K de siete fases para decisiones complejas o de alto riesgo. |
| [`kadi-teamwork-elite`](legacy/v1.6.0-rc1/kadi-teamwork-elite) | Release `v1.6.0-rc1` | Especificación histórica de orquestación multiagente, marcada como dormida (`DORMANT_UNQUALIFIED`). |

### Plugins

Estas skills no traen plugins propios, así que el repo no incluye ninguno.

## Instalación

Copia la carpeta de la skill que quieras a tu carpeta de skills de Claude Code. Para usuario (todos tus proyectos):

```powershell
# Windows (PowerShell)
git clone https://github.com/Kadi-Technology/kadi-skills.git
Copy-Item -Recurse kadi-skills\skills\kadi-ultra-eco "$env:USERPROFILE\.claude\skills\"
```

```bash
# macOS / Linux
git clone https://github.com/Kadi-Technology/kadi-skills.git
cp -r kadi-skills/skills/kadi-ultra-eco ~/.claude/skills/
```

Para una sola repo, copia a `<repo>/.claude/skills/` en lugar de `~/.claude/skills/`. La skill queda disponible en la siguiente sesión de Claude Code. Las que tienen `disable-model-invocation` (como `kadi-ultra-eco`) solo se activan al invocarlas por su comando.

## Notas de uso

- Las rutas locales de usuario se sustituyeron por `%USERPROFILE%` y `Path.home()`; ajústalas si tu layout es distinto.
- `kadi-swarm-orchestrator` usa solo la librería estándar de Python (3.13). `kadi-brain-orchestrator` necesita el SDK `anthropic` y la variable `ANTHROPIC_API_KEY` en tu entorno o en `~/.env`; este repo no incluye ninguna llave.
- `kadi-ticket` y `kadi-ultra-eco` hacen referencia al KADI Harness (`C:\KADI\harness`), que no forma parte de este repo; úsalas como receta si no tienes ese tooling.
- Los marcadores `<IP_PRODUCCION>` y similares son valores que debes poner tú.

## Licencia

[MIT](LICENSE) © 2026 KADI Technology.
