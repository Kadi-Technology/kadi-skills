<!-- ESTADO-VERIFICADO-2026-10-31 -->
# KADI Skills — Catálogo Oficial de Skills para Agentes de Código

Repositorio público de skills y recetas de automatización agéntica de **KADI Technology** para entornos de desarrollo en escritorio y terminal ([Claude Code](https://claude.com/claude-code), Antigravity, y agentes compatibles con el estándar `SKILL.md`).

Este catálogo reúne las herramientas operativas que estructuran flujos de trabajo multi-modelo, control de costos de inferencia, transacciones concurrentes en sistemas de archivos locales, multijugador local en red (LAN), producción audiovisual determinista y gobernanza de desarrollo.

Cada carpeta bajo `skills/` contiene una skill autocontenida (`SKILL.md` junto con sus scripts, contratos, pruebas o referencias) lista para integrarse directamente en el directorio de skills del agente.

---

## 1. Perfil del Entorno y Runtime

- **Target:** Entorno de escritorio, estación de trabajo y terminal CLI (Windows, macOS, Linux).
- **Runtimes de Agente:** Claude Code (`~/.claude/skills` o `.claude/skills`), Antigravity (`~/.gemini/config/skills`), o herramientas CLI compatibles.
- **Runtimes de Ejecución:** Python 3.10+ (scripts auxiliares) y Node.js 20+ (plantillas de red/LAN).

---

## 2. Catálogo General de Skills

### 2.1 Orquestación y Gobernanza Core (`skills/`)

Skills de despacho, partición jerárquica de modelos y transaccionalidad local de alta fidelidad.

| Skill | Activación | Stack / Dependencias | Descripción Técnica |
|---|---|---|---|
| [`kadi-brain-orchestrator`](skills/kadi-brain-orchestrator) | Automática / Prompt | Python 3, `anthropic` SDK | Orquestación jerárquica multi-modelo (Quad-Brain Engine): distribuye estrategia (Claude Fable), arquitectura técnica y DAGs (Claude Opus), síntesis de código (Claude Sonnet) y ejecución mecánica local (Gemini/CLI) aprovechando Prompt Caching. Requiere `ANTHROPIC_API_KEY`. |
| [`kadi-swarm-orchestrator`](skills/kadi-swarm-orchestrator) | Automática / Prompt | Python 3 estándar | Núcleo transaccional multi-agente para Windows NTFS: bloqueos jerárquicos de archivos, copias de seguridad shadow en bóveda, contratos duales SHA-256 (Content/Shape), destilación AST sin lectura completa (`/boost`) y multiplexor de previsualización web local (`/teamwork-preview`). |
| [`kadi-ultra-eco`](skills/kadi-ultra-eco) | Manual (`/kadi-ultra-eco`) | Markdown / Receta | Protocolo de enrutamiento por tiers de costo: asigna cada subtarea al modelo de menor consumo viable (T1 Sonnet, T2 Opus, T3 Fable) en lugar de propagar el modelo de la sesión padre. Incluye calculadora de costos y estimación de tokens. |
| [`kadi-ticket`](skills/kadi-ticket) | Automática / Prompt | Markdown / Harness | Protocolo de gobernanza y despacho: emisión, validación y verificación de tickets en ledger previo a cualquier mutación territorial o asignación a subagentes. Principio default-deny. |

---

### 2.2 Multijugador LAN y Red Local (`skills/multijugador/`)

Patrones de conectividad P2P y de área local para videojuegos y aplicaciones interactivas en dos dispositivos.

| Skill | Activación | Stack / Dependencias | Descripción Técnica |
|---|---|---|---|
| [`kadi-lan-multiplayer`](skills/multijugador/kadi-lan-multiplayer) | Automática / Prompt | Node.js 20+, `ws` | Implementación de multijugador local 1v1 y emparejamiento entre dispositivos conectados a la misma red WiFi o subred LAN. Provee dos arquitecturas: <br>• **Ruta A (Recomendada):** Señalización liviana agrupada por IP pública y sesión P2P vía WebRTC DataChannel sin necesidad de servidor TURN (con relevo WebSocket como respaldo). <br>• **Ruta B (Offline estricto):** Anfitrión local en LAN con descubrimiento mDNS/DNS-SD (RFC 6762), broadcast UDP y código QR con IP local. <br>Incluye suite de pruebas automatizadas con 50 casos (`node --test`), control de tasa, esquemas de serialización y templates funcionales en `templates/`. |

---

### 2.3 Redes Sociales y Contenido Audiovisual (`skills/redes-sociales/`)

Herramientas para generación técnica de copys, validación de claims, cosecha de evidencia real y renderizado audiovisual Scene-Locked. **Todas las skills operan en modo borrador local; ninguna realiza publicaciones automáticas ni contiene credenciales de redes sociales.**

| Skill | Activación | Stack / Dependencias | Descripción Técnica |
|---|---|---|---|
| [`kadi-redes-sociales`](skills/redes-sociales/kadi-redes-sociales) | Automática / Prompt | Python 3, Node.js | Community manager técnico multi-plataforma: linter estricto de claims (`lint:claims`), construcción paramétrica de URLs con UTMs para analítica, servidor MCP local y generación de borradores para LinkedIn, Instagram, X, TikTok y YouTube. |
| [`kadi-scene-locked-video`](skills/redes-sociales/kadi-scene-locked-video) | Automática / Prompt | Python 3, MoviePy 2.2+, FFmpeg, PIL | Motor de sincronización audiovisual determinista: calcula y bloquea la duración exacta de cada escena gráfica a partir del audio generado por TTS más una cota de respiro natural, eliminando desajustes temporales. |
| [`kadi-social-harvest`](skills/redes-sociales/kadi-social-harvest) | Automática / Prompt | Python 3, Playwright, `pypdfium2` | Cosechador automatizado de evidencia gráfica local: toma capturas headless reales de UIs en ejecución y renderiza páginas PDF vectoriales para ilustrar publicaciones técnicas sin maquetas sintéticas. |
| [`kadi-video-social`](skills/redes-sociales/kadi-video-social) | Automática / Prompt | Python 3, MoviePy, FFmpeg, faster-whisper | Pipeline completo de composición de video: guiones estructurados por plataforma, integración de subtítulos con faster-whisper y guías para flujos con Claude y Google AI Studio. |
| [`kadi-linkedin-growth-engine`](skills/redes-sociales/kadi-linkedin-growth-engine) | Automática / Prompt | Markdown | Especificación arquitectónica de embudo técnico B2B: arquitectura de canales, matriz semafórica de claims (GREEN / YELLOW / RED), cola de contenidos y trazabilidad comercial hacia CRM. |
| [`kadi-linkedin-publisher`](skills/redes-sociales/kadi-linkedin-publisher) | Automática / Prompt | Markdown / Plantillas | Estructurador de artículos técnicos en profundidad, carruseles documentales en PDF y comunicados corporativos orientados a la industria del software. |
| [`linkedin-manager`](skills/redes-sociales/linkedin-manager) | Automática / Prompt | Markdown | Estratega y redactor editorial para perfiles fundadores y técnicos en LinkedIn. Regla mandatoria de validación de evidencia empírica antes de borrador. |
| [`kadi-instagram-publisher`](skills/redes-sociales/kadi-instagram-publisher) | Automática / Prompt | Markdown / PIL | Generador de carruseles 4:5 (1080x1350) y especificaciones técnicas para Reels 9:16 (1080x1920) conforme a zonas seguras de interfaz móvil. |
| [`kadi-tiktok-youtube-shorts`](skills/redes-sociales/kadi-tiktok-youtube-shorts) | Automática / Prompt | Markdown / MoviePy | Formateador y validador de encuadres verticales 9:16 (1080x1920) respetando zonas seguras de UI para TikTok y YouTube Shorts. |
| [`kadi-facebook-whatsapp-broadcaster`](skills/redes-sociales/kadi-facebook-whatsapp-broadcaster) | Automática / Prompt | Markdown | Redactor de comunicados directos y cápsulas ejecutivas para Facebook y canales de mensajería, adaptado a políticas de privacidad estrictas. |
| [`video-content-creator`](skills/redes-sociales/video-content-creator) | Manual (`/Creador.de.contenido`) | Python 3, MoviePy, Edge-TTS | Flujo orquestador para convertir grabaciones de pantalla locales y pistas de audio en videos explicativos y tours de producto con subtítulos. |

---

### 2.4 Síntesis y Control de Voz (`skills/voz/`)

| Skill | Activación | Stack / Dependencias | Descripción Técnica |
|---|---|---|---|
| [`kadi-voice`](skills/voz/kadi-voice) | Automática / Prompt | CLI `chrono` (ChronoSDK) | Protocolo de control de voz asíncrono para agentes: garantiza locución secuencial sin colisiones mediante banderas bloqueantes (`chrono speak --blocking`). |
| [`chrono-tts`](skills/voz/chrono-tts) | Automática / Prompt | CLI `chrono` (ChronoSDK) | Emisión de síntesis de voz desde scripts de Python o llamadas de sistema para retroalimentación audible en tareas prolongadas. |

---

### 2.5 Archivo Histórico (`legacy/v1.6.0-rc1/`)

Skills preservadas exclusivamente como registro arquitectónico del flujo "Core2". No forman parte del flujo activo recomendado.

| Skill | Directorio | Contexto Histórico |
|---|---|---|
| `kadi-core2-routing-guardian` | `legacy/v1.6.0-rc1/kadi-core2-routing-guardian` | Enrutamiento formal y separación estricta entre motor, rol y autoridad. |
| `kadi-antigravity-qa-guardian` | `legacy/v1.6.0-rc1/kadi-antigravity-qa-guardian` | Protocolo de QA mecánico y ejecución acotada con Gemini. |
| `kadi-engineering-guardian` | `legacy/v1.6.0-rc1/kadi-engineering-guardian` | Reglas de mutación controlada para monolitos Laravel/React/TypeScript. |
| `kadi-ux-ui-specialist` | `legacy/v1.6.0-rc1/kadi-ux-ui-specialist` | Directivas de auditoría de usabilidad para interfaces de software denso. |
| `kadi-prm10k-booster` | `legacy/v1.6.0-rc1/kadi-prm10k-booster` | Protocolo PRM-10K de siete fases de análisis para decisiones de alto riesgo. |
| `kadi-teamwork-elite` | `legacy/v1.6.0-rc1/kadi-teamwork-elite` | Especificación primigenia multi-agente (estado: `DORMANT_UNQUALIFIED`). |

---

## 3. Instalación

Para instalar una o más skills en Claude Code, copia la carpeta de la skill correspondiente directamente en tu directorio de skills.

### 3.1 Instalación Global de Usuario (Todos los proyectos)

#### Windows (PowerShell)
```powershell
# Clonar el repositorio
git clone https://github.com/Kadi-Technology/kadi-skills.git

# Ejemplo: Instalar kadi-ultra-eco y kadi-lan-multiplayer
Copy-Item -Recurse kadi-skills\skills\kadi-ultra-eco "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse kadi-skills\skills\multijugador\kadi-lan-multiplayer "$env:USERPROFILE\.claude\skills\"
```

#### macOS / Linux (Bash)
```bash
# Clonar el repositorio
git clone https://github.com/Kadi-Technology/kadi-skills.git

# Ejemplo: Instalar kadi-ultra-eco y kadi-lan-multiplayer
cp -r kadi-skills/skills/kadi-ultra-eco ~/.claude/skills/
cp -r kadi-skills/skills/multijugador/kadi-lan-multiplayer ~/.claude/skills/
```

### 3.2 Instalación a Nivel de Repositorio Local
Si deseas habilitar una skill únicamente para un proyecto específico:
```bash
mkdir -p <mi-proyecto>/.claude/skills
cp -r kadi-skills/skills/multijugador/kadi-lan-multiplayer <mi-proyecto>/.claude/skills/
```

---

## 4. Requisitos y Dependencias por Módulo

| Módulo | Dependencias Mínimas | Configuración de Entorno |
|---|---|---|
| **kadi-brain-orchestrator** | Python 3.10+, `pip install anthropic` | Requiere variable de entorno `ANTHROPIC_API_KEY`. |
| **kadi-swarm-orchestrator** | Python 3.10+ (librería estándar: `pathlib`, `ast`, `hashlib`, `socket`) | Sin dependencias externas obligatorias. |
| **kadi-lan-multiplayer** | Node.js 20+, `npm install ws` (en `templates/`) | Parámetros opcionales: `TRUST_PROXY`, `ALLOWED_ORIGINS`, `ORIGIN_SECRET`. |
| **Redes / Audiovisual** | Python 3.10+, MoviePy 2.2+, Pillow, `pypdfium2`, Playwright | Binario de Chrome local y FFmpeg en PATH para renderizado. |
| **Voz (Chrono)** | Binario CLI `chrono` (ChronoSDK) | Opcional: motor `edge-tts` para síntesis en línea. |

---

## 5. Política de Seguridad, Privacidad y Veracidad (Cero Humo)

1. **Cero Secretos y Cero Credenciales:** Este repositorio público no contiene llaves de API, credenciales maestras, tokens de autenticación ni certificados privados. Las variables de configuración deben proveerse externamente en el entorno de ejecución.
2. **Sanitización de Datos y Redes:** Todas las direcciones IP en documentación y pruebas de socket emplean exclusivamente bloques de prueba y documentación estándar (RFC 5737: `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, RFC 1918: `10.0.0.0/8`, `192.168.0.0/16`, y multicast RFC 6762: `224.0.0.251`).
3. **Generación Determinista de Contenidos:** Las herramientas de redes sociales producen exclusivamente borradores y especificaciones en disco local (`Desktop/RedesSociales/`). No ejecutan publicaciones remotas automáticas hacia ninguna API de terceros.
4. **Veracidad Técnica (Ley II):** Las capacidades declaradas reflejan estrictamente el código funcional implementado y validado en los directorios de cada skill.

---

## 6. Licencia

Este proyecto está distribuido bajo la licencia [MIT](LICENSE).  
Copyright (c) 2026 KADI Technology.
