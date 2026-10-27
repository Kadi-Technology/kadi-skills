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

### Redes sociales (`skills/redes-sociales/`)

Skills para operar las redes de KADI: copys por plataforma, linter de claims, enlaces UTM, carruseles, PDFs, reels y video listo para publicar. Todas producen **borradores**: ninguna publica por sí sola ni usa tokens de redes.

| Skill | Origen | Para qué sirve |
|---|---|---|
| [`linkedin-manager`](skills/redes-sociales/linkedin-manager) | Repo de producto (`.agents/skills`) | Estratega B2B y copywriter de LinkedIn: perfil, pilares, estructura de posts y regla de evidencia antes de publicar. |
| [`kadi-linkedin-growth-engine`](skills/redes-sociales/kadi-linkedin-growth-engine) | Documentación del sitio web de KADI | Sistema de crecimiento en LinkedIn: embudo, cola de contenido, contrato UTM, matriz de claims públicos, marca en Canva y checklist de publicación. |
| [`kadi-redes-sociales`](skills/redes-sociales/kadi-redes-sociales) | Repo de redes sociales y directiva del agente | Community manager multi-plataforma: linter `lint:claims`, servidor MCP local, constructor de UTM, plantillas de copy por red, parrilla semanal y scripts de carruseles y reels. |
| [`kadi-video-social`](skills/redes-sociales/kadi-video-social) | Repo del sitio web y docs de marketing | Producción de video: manuales maestros con Claude y Google AI Studio, guiones y prompts por plataforma, y pipeline MoviePy/FFmpeg con locución importada. |
| [`kadi-linkedin-publisher`](skills/redes-sociales/kadi-linkedin-publisher) | Skills de Antigravity (`~/.gemini/config/skills`) | Artículos técnicos, carruseles PDF y publicaciones corporativas para LinkedIn con UTM canónicos y gate de aprobación. |
| [`kadi-instagram-publisher`](skills/redes-sociales/kadi-instagram-publisher) | Skills de Antigravity | Reels 9:16 y carruseles 4:5 de Instagram con especificaciones técnicas y compuerta de veracidad. |
| [`kadi-facebook-whatsapp-broadcaster`](skills/redes-sociales/kadi-facebook-whatsapp-broadcaster) | Skills de Antigravity | Comunicados para Facebook, WhatsApp y X respetando el contrato de privacidad del portal. |
| [`kadi-tiktok-youtube-shorts`](skills/redes-sociales/kadi-tiktok-youtube-shorts) | Skills de Antigravity | Videos verticales para TikTok y YouTube Shorts con zonas seguras y el motor Scene-Locked. |
| [`kadi-social-harvest`](skills/redes-sociales/kadi-social-harvest) | Skills de Antigravity | Cosecha capturas UI reales con Playwright y páginas de PDF con pypdfium2 antes de publicar. |
| [`kadi-scene-locked-video`](skills/redes-sociales/kadi-scene-locked-video) | Skills de Antigravity | Motor de video donde cada escena dura lo que su locución TTS más un margen de respiración (incluye `scene_locked_engine.py`). |
| [`video-content-creator`](skills/redes-sociales/video-content-creator) | Skills de Antigravity | Orquestador de producción de video a partir de grabaciones de pantalla, con script moviepy y edge-tts (incluye `references/`). |

### Voz (`skills/voz/`)

| Skill | Origen | Para qué sirve |
|---|---|---|
| [`kadi-voice`](skills/voz/kadi-voice) | Skills de Antigravity | Protocolo de voz sin encimamiento: `chrono speak --blocking`, Salomé para reportes y Opus para alertas. |
| [`chrono-tts`](skills/voz/chrono-tts) | Skills de Antigravity | Narración asíncrona con ChronoSDK desde CLI o Python. |

### Multijugador (`skills/multijugador/`)

| Skill | Origen | Para qué sirve |
|---|---|---|
| [`kadi-lan-multiplayer`](skills/multijugador/kadi-lan-multiplayer) | Servidor multijugador de un juego de KADI (patrón generalizado, código nuevo) | Multijugador local 1v1 y "buscar rival" para quienes comparten WiFi. Ruta A (recomendada): servidor de señalización que agrupa por IP pública, cola 1v1, invitaciones, salas con código, WebRTC DataChannel P2P sin TURN y relevo por WebSocket si falla. Ruta B: host Node offline con mDNS/DNS-SD, broadcast UDP y QR. Autoridad del anfitrión o lockstep, reconexión, revancha, límites de tasa y tamaño, y plantillas con 50 pruebas `node --test` (incluye `references/`, `templates/` y `tests/`). |

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

Las skills de `skills/redes-sociales/`, `skills/voz/` y `skills/multijugador/` se copian igual: copia la carpeta de la skill (por ejemplo `skills/voz/kadi-voice`) a `~/.claude/skills/`, sin las carpetas intermedias. Para una sola repo, copia a `<repo>/.claude/skills/` en lugar de `~/.claude/skills/`. La skill queda disponible en la siguiente sesión de Claude Code. Las que tienen `disable-model-invocation` (como `kadi-ultra-eco`) solo se activan al invocarlas por su comando.

## Notas de uso

- Las rutas locales de usuario se sustituyeron por `%USERPROFILE%` y `Path.home()`; ajústalas si tu layout es distinto.
- `kadi-swarm-orchestrator` usa solo la librería estándar de Python (3.13). `kadi-brain-orchestrator` necesita el SDK `anthropic` y la variable `ANTHROPIC_API_KEY` en tu entorno o en `~/.env`; este repo no incluye ninguna llave.
- `kadi-ticket` y `kadi-ultra-eco` hacen referencia al KADI Harness (`C:\KADI\harness`), que no forma parte de este repo; úsalas como receta si no tienes ese tooling.
- Los marcadores `<IP_PRODUCCION>` y similares son valores que debes poner tú.
- Las skills de redes sociales y de voz no necesitan tokens, API keys ni cookies. Los datos de contacto, cuentas y clientes del original se reemplazaron por marcadores que cada skill documenta en su `README.md` o `SKILL.md`: `<CORREO_CONTACTO>`, `<CORREO_VENTAS>`, `<TELEFONO_WHATSAPP>`, `<WHATSAPP_E164>`, `<ID_AGENDA>`, `<NOMBRE_COFUNDADOR_1>`, `<NOMBRE_COFUNDADOR_2>`, `<PERFIL_LINKEDIN>`, `<NOMBRE_FUNDADOR>`, `<RUTA_CHROMIUM_PLAYWRIGHT>`, `<URL_PRODUCCION_CLIENTE>` y `<URL_ACADEMIA_PUBLICA>`. Los hosts `portal-cliente`, `prod-cliente`, `academia-privada`, `demo-privada` y `demo-retirada` bajo `kadi.technology`, y las IPs `203.0.113.50` y `203.0.113.51`, son ficticios.
- Variables de entorno opcionales: `KADI_CHROME_EXEC`, `KADI_WEBPAGE_DIR`, `KADI_SCREENSHOTS_DIR` y `KADI_VIDEOS_SOURCE`.
- `kadi-lan-multiplayer` necesita Node 20 o superior y una sola dependencia, `ws` (`cd templates && npm install && npm test`). El servidor de señalización no guarda ni registra IPs; quien lo despliegue debe configurar `TRUST_PROXY`, `ORIGIN_SECRET` y `ALLOWED_ORIGINS` por variables de entorno (la skill no incluye secretos). Las IPs `203.0.113.x`, `198.51.100.x`, `192.0.2.x` y `192.168.1.x` de sus pruebas y ejemplos son de documentación o ficticias, y `senal.tu-dominio.example` es un marcador.
- Las skills de voz usan `chrono` (ChronoSDK) y `edge-tts`, que no se incluyen. `edge-tts` envía el texto a un servicio de síntesis en línea de Microsoft.

## Variantes de Antigravity

Antigravity guarda copias de `kadi-brain-orchestrator` y `kadi-swarm-orchestrator` en `~/.gemini/config/skills/`. Se comparó cada archivo con la versión publicada aquí (que viene de `~/.claude/skills/`) y solo difieren en lo siguiente; no se duplican en el repo:

| Skill | Archivo | Diferencia |
|---|---|---|
| `kadi-brain-orchestrator` | `SKILL.md` | La copia de Antigravity invoca el script desde `~/.gemini/config/skills/` en vez de `~/.claude/skills/`. |
| `kadi-brain-orchestrator` | `scripts/brain_orchestrator.py` | Antigravity lee el `.env` con `utf-8-sig` y recorta espacios en la clave; busca la base de conocimiento también en la subcarpeta `01_KADI_SCV/` e incluye el delta de estado `22_DELTA_ESTADO_...`. La versión publicada tiene en cambio tres filas extra de precios (`claude-fable-5`, `claude-opus-5`, `claude-sonnet-5`). |
| `kadi-swarm-orchestrator` | `SKILL.md` | Antigravity invoca siempre con `uv run` desde `~/.gemini/config/skills/`; la publicada ofrece `uv run` o `python` desde `~/.claude/skills/`. |
| `kadi-swarm-orchestrator` | `scripts/shadow_vault.py` | Antigravity añade soporte de rutas largas de Windows (prefijo `\\?\`) en lectura, copia, borrado y escritura del vault. |

El resto de archivos de ambas skills (docs, `swarm_coordinator.py`, `ast_distiller.py`, `preview_multiplexer.py` y las pruebas) es idéntico.

## Licencia

[MIT](LICENSE) © 2026 KADI Technology.
