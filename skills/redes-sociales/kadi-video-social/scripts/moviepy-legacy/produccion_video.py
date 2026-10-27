import imageio_ffmpeg
import os
import asyncio
import numpy as np

os.environ['IMAGEIO_FFMPEG_EXE'] = imageio_ffmpeg.get_ffmpeg_exe()

from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ImageClip, ColorClip, CompositeAudioClip
)
from PIL import Image, ImageDraw, ImageFont
import edge_tts
import sys

# ---------------------------------------------------------
# FUNCIONES REUTILIZABLES (De python_components.md)
# ---------------------------------------------------------

def safe_subclip(path: str, start: float, end: float,
                 output_size: tuple = (1920, 1080)) -> VideoFileClip | None:
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

def get_font(size: int, estilo: str = "courier") -> ImageFont.FreeTypeFont:
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
    candidatos += fuentes_courier + fuentes_sans
    for path in candidatos:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def make_subtitle_overlay(
    text: str,
    duration: float,
    video_size: tuple = (1920, 1080),
    fontsize: int = 52,
    color_texto: str = '#00ffcc',
    color_sombra: str = '#ff3366',
    posicion: str = 'bottom',
    estilo_fuente: str = 'courier',
) -> ImageClip:
    img = Image.new('RGBA', video_size, (0, 0, 0, 0))
    font = get_font(fontsize, estilo_fuente)
    lines = text.split('\n')
    line_h = int(fontsize * 1.3)
    block_h = line_h * len(lines) + 20

    if posicion == 'bottom':
        bar_y = video_size[1] - block_h - 30
    elif posicion == 'top':
        bar_y = 20
    else:
        bar_y = (video_size[1] - block_h) // 2

    overlay = Image.new('RGBA', video_size, (0, 0, 0, 0))
    bar = Image.new('RGBA', (video_size[0], block_h + 20), (0, 0, 0, 160))
    overlay.paste(bar, (0, bar_y))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        y = bar_y + 10 + i * line_h
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (video_size[0] - tw) // 2
        draw.text((x + 2, y + 2), line, font=font, fill=color_sombra)
        draw.text((x, y), line, font=font, fill=color_texto)

    return ImageClip(np.array(img), ismask=False).set_duration(duration)

def make_credits_sequence(
    pantallas: list[list[str]],
    duration_total: float = 20.0,
    bg_color: tuple = (0, 0, 0),
    color_titulo: str = '#00ffcc',
    color_texto: str = '#ffffff',
    video_size: tuple = (1920, 1080),
):
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

def build_video(
    segmentos: list[dict],
    config_plataforma: dict,
    config_estilo: dict,
    music_path: str | None,
    output_path: str,
    tts_dir: str,
    tts_voice: str = 'es-CO-SalomeNeural',
) -> None:
    output_size = config_plataforma['output_size']
    
    print("\n[1/4] 🎙 Generando narración TTS...")
    try:
        asyncio.run(generate_all_tts(segmentos, tts_dir, tts_voice))
    except Exception as e:
        print(f"  ⚠ TTS global falló: {e}. Continuando sin narración...")

    print("\n[2/4] 🎬 Ensamblando clips...")
    assembled = []
    for seg in segmentos:
        clip = safe_subclip(seg['path'], seg['start'], seg['end'], output_size)
        if clip is None:
            continue
        
        subtitle = make_subtitle_overlay(
            seg['subtitle'], clip.duration, output_size,
            color_texto=config_estilo['color_texto'],
            color_sombra=config_estilo['color_sombra'],
        )
        composed = CompositeVideoClip([clip, subtitle])
        
        tts_path = seg.get('tts_path', '')
        if os.path.exists(tts_path) and clip.audio is not None:
            try:
                tts_audio = AudioFileClip(tts_path)
                tts_cut = tts_audio.subclip(0, min(tts_audio.duration, clip.duration - 0.2))
                mixed = CompositeAudioClip([
                    clip.audio.volumex(0.15),
                    tts_cut.volumex(1.0).set_start(0.3),
                ])
                composed = composed.set_audio(mixed)
            except Exception as e:
                print(f"  ⚠ Audio mix falló para seg {seg['id']}: {e}")
        
        composed = composed.fadein(0.5).fadeout(0.5)
        assembled.append(composed)

    if not assembled:
        print("❌ No se ensamblaron clips. Verifica rutas y timestamps.")
        sys.exit(1)

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

    print(f"\n[4/4] 🚀 Renderizando {final.duration:.1f}s → {output_path}")
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
    print(f"\n✅ VIDEO COMPLETADO: {output_path} ({final.duration:.1f}s)")

# ---------------------------------------------------------
# EJECUCIÓN DEL DOCUMENTAL
# ---------------------------------------------------------
if __name__ == "__main__":
    BASE_DIR = os.environ.get("KADI_VIDEOS_SOURCE", "./videos_source")
    
    segmentos = [
        {
            'id': 1,
            'path': os.path.join(BASE_DIR, 'kadi-demo-comercial-profesional.mp4'),
            'start': 0.0,
            'end': 15.0,
            'tts': "Bienvenido a CADI, el sistema operativo veterinario de alta especialidad.",
            'subtitle': "KADI\nBIENVENIDO"
        },
        {
            'id': 2,
            'path': os.path.join(BASE_DIR, 'page@40050cef39156762424f334ba0c92333.webm'),
            'start': 15.0,
            'end': 30.0,
            'tts': "Comenzar es muy sencillo. Primero, elige el modelo de negocio que mejor se adapte a tu operación.",
            'subtitle': "FLEXIBILIDAD\nELIGE TU MODELO"
        },
        {
            'id': 3,
            'path': os.path.join(BASE_DIR, 'kadi_presentacion_oficial_2min_hd.mp4'),
            'start': 35.0,
            'end': 50.0,
            'tts': "Ingresa los datos esenciales de tu clínica. Nosotros nos encargamos de adaptar el sistema a tus necesidades.",
            'subtitle': "CONFIGURACIÓN RÁPIDA\nSIN COMPLICACIONES"
        },
        {
            'id': 4,
            'path': os.path.join(BASE_DIR, 'kadi_promo_oficial_hd.mp4'),
            'start': 130.0,
            'end': 145.0,
            'tts': "Revisa tu configuración, personaliza tus colores, y con un solo clic estarás listo para iniciar.",
            'subtitle': "LISTO PARA LANZAR\nEN MINUTOS"
        },
        {
            'id': 5,
            'path': os.path.join(BASE_DIR, 'kadi_promo_master_1080p.mp4'),
            'start': 35.0,
            'end': 50.0,
            'tts': "Y así de fácil, tu clínica está operando en la nube con un dashboard de control total en tiempo real.",
            'subtitle': "CONTROL TOTAL\nEN TIEMPO REAL"
        }
    ]

    config_plataforma = {
        "nombre": "Demo Interno",
        "output_size": (1920, 1080),
        "fps": 30,
        "codec": "libx264",
        "bitrate": "5000k",
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "preset": "fast",
        "musica_volumen": 0.15,
    }

    config_estilo = {
        "color_texto": "#00ffcc",
        "color_sombra": "#ff3366",
        "fondo_creditos": (0, 0, 0),
    }

    out_path = os.path.join(BASE_DIR, "produccion_kadi_cyberpunk.mp4")
    tts_dir = os.path.join(BASE_DIR, "tts_narration")
    
    build_video(
        segmentos=segmentos,
        config_plataforma=config_plataforma,
        config_estilo=config_estilo,
        music_path=None, 
        output_path=out_path,
        tts_dir=tts_dir,
    )
