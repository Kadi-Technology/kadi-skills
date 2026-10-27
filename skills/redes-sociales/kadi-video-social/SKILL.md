---
name: kadi-video-social
description: Producción de video para redes de KADI (Reels, TikTok, YouTube Shorts, video horizontal y tour de producto). Incluye manuales maestros para producir con Claude (Remotion, HTML5 y FFmpeg) y con Google AI Studio (Imagen y Veo), guiones con prompts por plataforma, un pipeline en Python (MoviePy y FFmpeg) que renderiza reels y videos desde capturas reales, e importación y alineación de locución local con faster-whisper.
---

# KADI Video Social

Instrucciones y herramientas para crear **video listo para publicar** a partir de capturas de producto, un storyboard y una locución auténtica. Complementa a `kadi-redes-sociales` (copys, lint y parrilla) y a `linkedin-manager` (estrategia).

## Contenido

### `prompts/` (instrucciones y guiones)

| Archivo | Para qué sirve |
|---|---|
| `CLAUDE_VIDEO_PRODUCTION_MASTER_KIT.md` | Manual maestro: Claude como motor de planificación, composición y render con Remotion, animaciones HTML5 y FFmpeg; modelo recomendado por fase del pipeline. |
| `GOOGLE_AI_STUDIO_VIDEO_MASTER_KIT.md` | Manual maestro para generar keyframes y clips con Google AI Studio (Imagen, Veo) y voz sintética; tabla de capturas 16:9 y 9:16 por módulo. |
| `P-004_produccion_video_claude_master.md` | Prompt maestro listo para pegar que dispara la producción con Claude. |
| `SCRIPTS_AND_PROMPTS_INSTAGRAM_REELS.md` | Guiones escena por escena y prompts para Reels, TikTok y Shorts 9:16. |
| `SCRIPTS_AND_PROMPTS_LINKEDIN_ENTERPRISE.md` | Guiones y prompts para video B2B en LinkedIn. |
| `SCRIPTS_AND_PROMPTS_YOUTUBE_PRODUCT_TOUR.md` | Guion y prompts para el tour de producto en YouTube 16:9. |
| `visual-capture.md` | Sistema de captura visual con Playwright (resoluciones, datos demo, destino de los assets). Describe scripts de captura que no se incluyen aquí. |
| `HTML5_MOTION_VIDEO_PLAYER.html` | Reproductor de motion graphics en HTML5 de ejemplo. |

### `scripts/` (pipeline reproducible)

| Archivo | Para qué sirve |
|---|---|
| `storyboard.json` | Storyboard de seis escenas: texto de locución, capturas y duración. Es la entrada de los renderers. |
| `render_instagram.py` | Reel 9:16 de 30 s (1080x1920, 30 fps) con capturas reales, paneo, música sintetizada y copy en pantalla. `--preview-only` genera solo la vista previa. |
| `prepare_audio.py` | Importa una grabación auténtica, mide los canales, la transcribe localmente con faster-whisper y alinea las seis escenas; rechaza silencio y texto desactualizado. No usa TTS de reserva. |
| `audio_contract.py` | Contratos de validación del audio importado (hashes, identidad declarada del narrador, alineación). |
| `render_video.py` | Render del video web con MoviePy, Pillow y FFmpeg; genera MP4, subtítulos VTT, transcripción y póster. |
| `publication.py` | Publicación en etapas: construye, valida y reemplaza todos los artefactos juntos o no reemplaza ninguno. |
| `verify_pipeline_contracts.py` | Verificación de los contratos del pipeline. |
| `create_salome_test_fixture.py` | Genera una locución sintética **solo para pruebas** del importador (etiqueta `TEST-ONLY-Salome`); nunca se usa como voz del producto. |
| `moviepy-legacy/` | Scripts anteriores de MoviePy y edge-tts (`produccion_video.py`) y utilidades para inspeccionar videos y extraer fotogramas. |

## Flujo de trabajo

1. **Guion.** Parte de `SCRIPTS_AND_PROMPTS_*.md` o del kit maestro y escribe el `storyboard.json` (escena, locución, capturas).
2. **Capturas.** Reúne capturas con datos sintéticos o autorizados (ver `visual-capture.md`) y recorta barras con datos de contacto reales.
3. **Locución.** Graba la voz real y corre `prepare_audio.py --input <audio> --speaker Narrador --model <ruta-faster-whisper>`. El storyboard debe declarar `"voice": "Narrador (grabación importada)"`.
4. **Render.** `render_instagram.py` para el reel; `render_video.py` para el video web.
5. **Publicación en etapas.** `publication.py` valida y publica los artefactos juntos.
6. **Revisión.** Revisa el contact sheet de fotogramas, el audio (RMS y picos) y pasa el copy por el linter de `kadi-redes-sociales` antes de pedir aprobación al PO.

## Requisitos y configuración

- Python con las dependencias de `scripts/requirements.txt` (faster-whisper, MoviePy 1.0.3, NumPy, Pillow); FFmpeg y FFprobe en el `PATH`. `edge-tts` solo para el fixture de pruebas (`requirements-test-fixtures.txt`).
- Estructura esperada: los scripts resuelven `ROOT` dos niveles arriba de `scripts/` y escriben en `output/`. Ajústala a tu proyecto.
- Variables de entorno (sin credenciales): `KADI_SCREENSHOTS_DIR` (carpeta de capturas para `render_video.py`) y `KADI_VIDEOS_SOURCE` (carpeta de videos fuente para los scripts de `moviepy-legacy/`).
- Los nombres de capturas del storyboard (`07_login_clinica_ejemplo.png`, `11_ficha_paciente_ejemplo.png`, etc.) son marcadores: usa tus propias capturas con datos ficticios.
- Esta skill **no necesita tokens ni API keys**. Los kits de Google AI Studio asumen que usas tu propia cuenta; no hay claves en el repo.

## Reglas

- La voz del producto es siempre una grabación auténtica declarada por el operador; la voz sintética solo sirve como fixture etiquetado `TEST-ONLY`.
- Sin fotos ni videos de personas reales sin autorización: los prompts describen personas sintéticas.
- Los videos son borradores hasta la aprobación del PO.
