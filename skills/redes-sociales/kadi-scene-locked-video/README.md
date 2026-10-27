# KADI Scene-Locked Video Engine

Motor audiovisual Scene-Locked: cada escena dura exactamente su locución TTS más 0.35 s de respiración. Incluye `scripts/scene_locked_engine.py`.

## Requisitos y notas

- Dependencias: Pillow, pypdfium2, moviepy 2.x, ffmpeg/ffprobe y `edge-tts` (voz `es-CO-SalomeNeural`, servicio de síntesis en línea). Opcional: `chrono` (ver `skills/voz/chrono-tts`).
- Uso: `python scripts/scene_locked_engine.py --manifest <manifiesto.json> --output <salida.mp4>`.
- Manifiesto: `{ "width": 1080, "height": 1920, "breath_padding_sec": 0.35, "scenes": [{ "badge", "headline", "subheadline", "narration", "asset_path" }] }`.

## Marcadores y variables a configurar

| Marcador | Qué poner |
|---|---|
| `%APPDATA%\Python\Python313\Scripts\chrono.exe` | Ruta del ejecutable `chrono` en tu equipo, si lo usas. |

## Credenciales

No requiere credenciales ni API keys.
