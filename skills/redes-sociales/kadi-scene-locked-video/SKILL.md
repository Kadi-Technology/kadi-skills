---
name: kadi-scene-locked-video
description: Motor audiovisual institucional Scene-Locked de KADI Technology (PIL + pypdfium2 + moviepy 2.2.1 + ffmpeg + chrono.exe). Úsalo para producir Reels, Shorts y videos corporativos donde cada escena visual dura exactamente lo que dura su bloque de locución TTS más su margen de respiración, sin usar jamás los estilos viejos de subtítulos neón cian.
---

# KADI Scene-Locked Video Engine (`kadi-scene-locked-video`)

## Propósito y Reglas Inquebrantables
1. **Cero Estilo Neón Legacy:** Queda estrictamente prohibido utilizar subtítulos o cintillos neón cian (`#00FFFF`) de sesiones antiguas. Toda producción de KADI Technology utiliza la paleta ejecutiva institucional:
   - Fondo Primario: `#0A1220` (Deep Obsidian Slate)
   - Superficie Secundaria: `#0F1B2E` (Executive Navy)
   - Acento Institucional / Founder: `#C9A227` (Executive Gold)
   - Texto Principal: `#F6F7FA` (Crisp Alabaster)
   - Texto Secundario: `#94A3B8` (Muted Slate)
2. **Arquitectura Scene-Locked Determinista:**
   - Nunca se genera un único audio largo desconectado de los cortes visuales.
   - Cada escena $i$ define su propio texto de locución (`narration`), su activo visual real (`asset_path`: captura PNG, PDF renderizado con `pypdfium2` o clip MP4) y su titular editorial (`headline`, `subheadline`, `badge`).
   - El motor sintetiza primero el audio de cada escena individualmente, mide su duración exacta $d_i$ con `ffprobe` / `moviepy`, y bloquea la duración del clip visual de esa escena a $T_i = d_i + 0.35\text{ s}$.
3. **Veracidad Editorial (`lint:claims`):**
   - Todo guion debe respetar el estado real en `portal/src/_data/projects.json` (ej. `kadi-scv` como `"Cohorte Founder y Despliegue Piloto"`, cero métricas inventadas).

## Toolchain Verificado en Windows (Python 3.13)
- `moviepy==2.2.1` (Importar desde `from moviepy import ImageClip, VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips`)
- `Pillow==12.2.0` (`PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFont`)
- `pypdfium2==5.7.0` (Renderizado de PDFs reales a PNG de alta resolución)
- `ffmpeg` y `ffprobe` v8.1
- `chrono.exe` (`%APPDATA%\Python\Python313\Scripts\chrono.exe`) / `edge-tts` (`es-CO-SalomeNeural`)

## Uso del Motor Ejecutable
Ejecuta el motor pasándole un manifiesto JSON de escenas:
```powershell
python "%USERPROFILE%\.gemini\config\skills\kadi-scene-locked-video\scripts\scene_locked_engine.py" --manifest "%USERPROFILE%\Desktop\RedesSociales\Instagram\manifest_scene_locked.json" --output "%USERPROFILE%\Desktop\RedesSociales\Instagram\output\reel-custom.mp4"
```
