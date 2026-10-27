# Componentes Python Reutilizables — Creador de Contenido

Estas funciones son la base probada de producción. Cópialas directamente en
cualquier script de edición. Todas fueron validadas en producción real
(Operación Leviatán, 2026-08-07, 29 subagentes, 4 videos, Python 3.13).

---

## 1. Configuración de entorno (SIEMPRE al inicio del script)

```python
import imageio_ffmpeg
import os

# CRÍTICO: Configurar ffmpeg ANTES de importar moviepy
os.environ['IMAGEIO_FFMPEG_EXE'] = imageio_ffmpeg.get_ffmpeg_exe()

from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ImageClip, ColorClip, CompositeAudioClip
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import edge_tts
import asyncio
import traceback
import sys
```

---

## 2. safe_subclip() — Carga de clips con validación

```python
def safe_subclip(path: str, start: float, end: float,
                 output_size: tuple = (1920, 1080)) -> VideoFileClip | None:
    """
    Carga un subclip validando que los timestamps no excedan la duración real.
    Escala automáticamente a output_size para evitar mismatch en concatenate.
    
    LECCIÓN: Las grabaciones de pantalla tienen duraciones IMPREVISIBLES
    por el bitrate variable. NUNCA asumas duración por tamaño de archivo.
    """
    if not os.path.exists(path):
        print(f"    ⚠  Video no encontrado: {path}")
        return None
    try:
        raw = VideoFileClip(path)
        dur = raw.duration
        real_start = min(start, max(0, dur - 1))
        real_end   = min(end, dur)
        if real_start >= real_end:
            print(f"    ⚠  Timestamps [{start}-{end}s] fuera de rango (dur={dur:.1f}s): {os.path.basename(path)}")
            raw.close()
            return None
        clip = raw.subclip(real_start, real_end)
        if list(clip.size) != list(output_size):
            clip = clip.resize(output_size)
        print(f"    ✅ {os.path.basename(path)}: {real_start:.0f}s→{real_end:.0f}s ({real_end-real_start:.0f}s)")
        return clip
    except Exception as e:
        print(f"    ❌ Error cargando clip: {e}")
        return None
```

---

## 3. get_font() — Carga de fuentes con fallback

```python
def get_font(size: int, estilo: str = "courier") -> ImageFont.FreeTypeFont:
    """
    Carga la mejor fuente disponible en el sistema Windows con fallback robusto.
    NOTA: ImageMagick NO está instalado. Usar siempre PIL + ImageClip.
    """
    fuentes_courier = [
        r'C:\Windows\Fonts\cour.ttf',
        r'C:\Windows\Fonts\courbd.ttf',
        r'C:\Windows\Fonts\consola.ttf',
    ]
    fuentes_sans = [
        r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\arialbd.ttf',
        r'C:\Windows\Fonts\segoeui.ttf',
    ]
    candidatos = fuentes_courier if estilo in ("courier", "terminal", "tech") else fuentes_sans
    candidatos += fuentes_courier + fuentes_sans  # fallback chain
    for path in candidatos:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()
```

---

## 4. make_subtitle_overlay() — Subtítulos neón con barra semitransparente

```python
def make_subtitle_overlay(
    text: str,
    duration: float,
    video_size: tuple = (1920, 1080),
    fontsize: int = 52,
    color_texto: str = '#00ffcc',
    color_sombra: str = '#ff3366',
    posicion: str = 'bottom',   # 'bottom', 'top', 'center'
    estilo_fuente: str = 'courier',
) -> ImageClip:
    """
    Crea overlay de subtítulo con:
    - Barra negra semitransparente de fondo (legibilidad garantizada)
    - Texto principal en color_texto
    - Sombra en color_sombra (efecto neón/profundidad)
    
    LECCIÓN: Sin barra de fondo, los subtítulos son ilegibles sobre
    pantallas brillantes (código, terminales blancas).
    """
    img = Image.new('RGBA', video_size, (0, 0, 0, 0))
    font = get_font(fontsize, estilo_fuente)
    lines = text.split('\n')
    line_h = int(fontsize * 1.3)
    block_h = line_h * len(lines) + 20

    # Calcular posición vertical del bloque
    if posicion == 'bottom':
        bar_y = video_size[1] - block_h - 30
    elif posicion == 'top':
        bar_y = 20
    else:  # center
        bar_y = (video_size[1] - block_h) // 2

    # Barra semitransparente de fondo
    overlay = Image.new('RGBA', video_size, (0, 0, 0, 0))
    bar = Image.new('RGBA', (video_size[0], block_h + 20), (0, 0, 0, 160))
    overlay.paste(bar, (0, bar_y))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Renderizar líneas centradas
    for i, line in enumerate(lines):
        y = bar_y + 10 + i * line_h
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (video_size[0] - tw) // 2
        draw.text((x + 2, y + 2), line, font=font, fill=color_sombra)  # Sombra
        draw.text((x, y), line, font=font, fill=color_texto)            # Texto

    return ImageClip(np.array(img), ismask=False).set_duration(duration)
```

---

## 5. make_credits_sequence() — Créditos cinematográficos

```python
def make_credits_sequence(
    pantallas: list[list[str]],
    duration_total: float = 20.0,
    bg_color: tuple = (0, 0, 0),
    color_titulo: str = '#00ffcc',
    color_texto: str = '#ffffff',
    video_size: tuple = (1920, 1080),
) -> object:  # CompositeVideoClip/concatenate result
    """
    Crea secuencia de créditos con múltiples pantallas.
    
    pantallas: Lista de listas de strings. El primer string de cada lista
               es el "título" (color_titulo), el resto son cuerpo (color_texto).
    
    Ejemplo:
        pantallas = [
            ["73 MINUTOS DE GRABACIÓN", "4 SESIONES | 1 SISTEMA"],
            ["PRODUCIDO POR:", "Mi Empresa Tech"],
            ['"El futuro del desarrollo ya llegó."'],
        ]
    """
    clips = []
    per_screen = duration_total / len(pantallas)

    for pantalla in pantallas:
        img = Image.new('RGB', video_size, bg_color)
        draw = ImageDraw.Draw(img)
        font_big = get_font(62, 'courier')
        font_sm  = get_font(40, 'sans')

        lineas_validas = [l for l in pantalla if l.strip()]
        block_h = len(lineas_validas) * 75
        y = (video_size[1] - block_h) // 2
        es_titulo = True

        for linea in pantalla:
            if not linea.strip():
                y += 35
                continue
            font = font_big if es_titulo else font_sm
            color = color_titulo if es_titulo else color_texto
            bbox = draw.textbbox((0, 0), linea, font=font)
            tw = bbox[2] - bbox[0]
            x = (video_size[0] - tw) // 2
            draw.text((x, y), linea, font=font, fill=color)
            y += 75
            es_titulo = False

        clip = (ImageClip(np.array(img))
                .set_duration(per_screen)
                .fadein(0.8).fadeout(0.8))
        clips.append(clip)

    return concatenate_videoclips(clips, method='compose')
```

---

## 6. generate_all_tts() — TTS paralelo con edge-tts

```python
async def _gen_one_tts(text: str, path: str, voice: str) -> None:
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
        print(f"    🎙 TTS OK: {os.path.basename(path)}")
    except Exception as e:
        print(f"    ⚠ TTS FALLO ({os.path.basename(path)}): {e}")

async def generate_all_tts(
    segmentos: list[dict],
    tts_dir: str,
    voice: str = 'es-CO-SalomeNeural',
    force_regenerate: bool = False,
) -> None:
    """
    Genera todos los archivos MP3 de narración en paralelo.
    - Reutiliza archivos ya existentes (no regenera si force_regenerate=False)
    - Requiere conexión a internet (Microsoft Azure TTS)
    - Falla gracefully: si falla una narración, continúa con las demás
    
    Cada dict en segmentos debe tener: {'id': int, 'tts': str}
    Añade 'tts_path' a cada dict con la ruta del archivo generado.
    """
    os.makedirs(tts_dir, exist_ok=True)
    tasks = []
    for seg in segmentos:
        path = os.path.join(tts_dir, f"narr_{seg['id']:02d}.mp3")
        seg['tts_path'] = path
        if force_regenerate or not os.path.exists(path):
            tasks.append(_gen_one_tts(seg['tts'], path, voice))
        else:
            print(f"    ♻ TTS {seg['id']} reutilizado")
    if tasks:
        print(f"    Generando {len(tasks)} narraciones en paralelo...")
        await asyncio.gather(*tasks)
```

---

## 7. analyze_video_activity() — Mejores timestamps con OpenCV

```python
def analyze_video_activity(
    path: str,
    sample_interval_s: float = 10.0,
    top_n: int = 10,
) -> list[tuple[float, float]]:
    """
    Analiza el video con OpenCV para encontrar los momentos con más
    cambio visual (alta actividad = más interesante para el documental).
    
    Retorna lista de (timestamp_segundos, score_actividad) ordenada de mayor a menor.
    
    LECCIÓN: Para grabaciones de pantalla con mucho código/texto, la actividad
    visual identifica correctamente cuándo el desarrollador está activo
    vs cuándo hay texto estático (chat, espera).
    """
    import cv2
    
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"⚠ OpenCV no puede abrir: {path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = total_frames / fps
    print(f"  📊 Analizando {os.path.basename(path)}: {duration:.0f}s @ {fps}fps")

    activities = []
    prev_gray = None
    sample_frames = max(1, int(fps * sample_interval_s))
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_frames == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                score = float(np.mean(diff))
                activities.append((frame_idx / fps, score))
            prev_gray = gray
        frame_idx += 1

    cap.release()
    activities.sort(key=lambda x: x[1], reverse=True)
    return activities[:top_n]
```

---

## 8. Función principal — Pipeline completo

```python
def build_video(
    segmentos: list[dict],
    config_plataforma: dict,
    config_estilo: dict,
    music_path: str | None,
    output_path: str,
    tts_dir: str,
    tts_voice: str = 'es-CO-SalomeNeural',
) -> None:
    """
    Pipeline principal de producción. Ensambla todos los componentes.
    
    Cada dict en segmentos debe tener:
    {
        'id': int,
        'path': str,          # Ruta al video fuente
        'start': float,       # Timestamp inicio (segundos)
        'end': float,         # Timestamp fin (segundos)
        'tts': str,           # Texto de narración
        'subtitle': str,      # Texto del subtítulo en pantalla
        'tts_path': str,      # (Se añade por generate_all_tts)
    }
    """
    output_size = config_plataforma['output_size']
    
    # PASO 1: Generar TTS
    print("\n[1/4] 🎙 Generando narración TTS...")
    try:
        asyncio.run(generate_all_tts(segmentos, tts_dir, tts_voice))
    except Exception as e:
        print(f"  ⚠ TTS global falló: {e}. Continuando sin narración...")

    # PASO 2: Ensamblar clips
    print("\n[2/4] 🎬 Ensamblando clips...")
    assembled = []
    for seg in segmentos:
        clip = safe_subclip(seg['path'], seg['start'], seg['end'], output_size)
        if clip is None:
            continue
        
        # Overlay de subtítulo
        subtitle = make_subtitle_overlay(
            seg['subtitle'], clip.duration, output_size,
            color_texto=config_estilo['color_texto'],
            color_sombra=config_estilo['color_sombra'],
        )
        composed = CompositeVideoClip([clip, subtitle])
        
        # Audio: Solo TTS (original silenciado para evitar colisiones)
        tts_path = seg.get('tts_path', '')
        if os.path.exists(tts_path):
            try:
                tts_audio = AudioFileClip(tts_path)
                tts_cut = tts_audio.subclip(0, min(tts_audio.duration, clip.duration - 0.2))
                # Usamos SOLO el audio TTS para que las voces no choquen
                composed = composed.set_audio(tts_cut.set_start(0.3))
            except Exception as e:
                print(f"  ⚠ Audio TTS falló para seg {seg['id']}: {e}")
        
        composed = composed.fadein(0.5).fadeout(0.5)
        assembled.append(composed)

    if not assembled:
        print("❌ No se ensamblaron clips. Verifica rutas y timestamps.")
        sys.exit(1)

    # PASO 3: Créditos + Concatenar
    print("\n[3/4] 🎞 Construyendo créditos y concatenando...")
    creditos_pantallas = [
        ["PRODUCIDO CON IA AGÉNTICA", "Antigravity — Enjambre Gemini"],
        ['"El futuro del desarrollo ya llegó."'],
    ]
    creditos = make_credits_sequence(
        creditos_pantallas,
        duration_total=10.0,
        color_titulo=config_estilo['color_texto'],
        bg_color=config_estilo['fondo_creditos'],
    )
    final = concatenate_videoclips(assembled + [creditos], method='compose')

    # PASO 4: Música de fondo
    if music_path and os.path.exists(music_path):
        print(f"\n  🎵 Añadiendo música...")
        try:
            bg = AudioFileClip(music_path).volumex(config_plataforma['musica_volumen'])
            if bg.duration < final.duration:
                from moviepy.audio.fx.all import audio_loop
                bg = audio_loop(bg, nloops=int(final.duration / bg.duration) + 1)
            bg = bg.subclip(0, final.duration).audio_fadeout(3)
            if final.audio is not None:
                final = final.set_audio(CompositeAudioClip([final.audio, bg]))
        except Exception as e:
            print(f"  ⚠ Música falló: {e}")

    # PASO 5: Renderizar
    dur = final.duration
    print(f"\n[4/4] 🚀 Renderizando {dur:.1f}s → {output_path}")
    final.write_videofile(
        output_path,
        fps=config_plataforma['fps'],
        codec=config_plataforma['codec'],
        audio_codec=config_plataforma['audio_codec'],
        bitrate=config_plataforma['bitrate'],
        audio_bitrate=config_plataforma['audio_bitrate'],
        preset=config_plataforma['preset'],
        threads=4,
        logger='bar',
    )
    print(f"\n✅ VIDEO COMPLETADO: {output_path} ({dur:.1f}s)")
```
