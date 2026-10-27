"""KADI Instagram Reel v2: six product-first scenes, 9:16, music and on-screen copy."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from moviepy.editor import VideoClip


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/instagram"
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS, DURATION = 1080, 1920, 30, 30
NAVY = (10, 18, 32)
GOLD = (226, 199, 102)
WHITE = (246, 248, 251)
MUTED = (180, 196, 218)
FONT = Path("C:/Windows/Fonts")
FONTS = {}

# Focal windows pan across the real screen while the inset keeps the whole UI in view.
SCENES = [
    {"tag": "PARA QUIEN DIRIGE LA CLÍNICA", "title": "¿La cuenta refleja\ntoda la atención?", "detail": "Medicamentos · tratamientos · hospitalización", "screen": "17_caja_finanzas.png", "chip": "El desorden también tiene un costo.", "focus": [(0.03, 0.0, 0.73, 1.0), (0.13, 0.0, 0.83, 1.0)]},
    {"tag": "DEL INGRESO AL EXPEDIENTE", "title": "Un paciente.\nEl mismo contexto.", "detail": "Historial y atención en la misma ficha.", "screen": "11_ficha_paciente_ejemplo.png", "chip": "Recepción y consulta, conectadas.", "focus": [(0.03, 0.0, 0.73, 1.0), (0.13, 0.0, 0.83, 1.0)]},
    {"tag": "CONTINUIDAD ENTRE TURNOS", "title": "El siguiente turno,\ncon contexto.", "detail": "Indicaciones y evolución en hospitalización.", "screen": "15_hospitalizacion_uci.png", "chip": "Consulta el seguimiento del paciente.", "focus": [(0.03, 0.0, 0.73, 1.0), (0.15, 0.0, 0.85, 1.0)]},
    {"tag": "ATENCIÓN Y ADMINISTRACIÓN", "title": "Del consumo\na la cuenta.", "detail": "Cargos, pagos y saldos del paciente.", "screen": "17_caja_finanzas.png", "chip": "Del expediente al cobro.", "focus": [(0.13, 0.0, 0.83, 1.0), (0.03, 0.0, 0.73, 1.0)]},
    {"tag": "CONFIGURA TU OPERACIÓN", "title": "Selecciona tu mejor opción.", "detail": "Hospital · Clínica · Grooming", "screen": "01_onboarding_paso0_modelo.png", "chip": "Elige tu modelo de operación.", "focus": None},
    {"tag": "CONOCE KADI", "title": "Tu clínica\nen orden.", "detail": "Del expediente al cobro.", "screen": "08_dashboard_ejemplo.png", "chip": "Conoce el producto en una demo.", "focus": [(0.03, 0.0, 0.73, 1.0), (0.14, 0.0, 0.84, 1.0)]},
]
LOGO_PATH = ROOT / "src/assets/logo-kadi.png"
LOGO = ImageOps.contain(Image.open(LOGO_PATH).convert("RGBA"), (182, 76), Image.Resampling.LANCZOS)
SHOTS = {name: Image.open(OUT / "sources" / name).convert("RGB") for name in {s["screen"] for s in SCENES}}

BACKGROUND = Image.new("RGB", (W, H), NAVY)
draw = ImageDraw.Draw(BACKGROUND)
for y in range(H):
    glow = max(0, 1 - abs(y - 850) / 1000)
    draw.line((0, y, W, y), fill=(10 + int(7 * glow), 18 + int(12 * glow), 32 + int(18 * glow)))
for x in range(0, W, 90):
    draw.line((x, 0, x, H), fill=(22, 33, 49))
for y in range(0, H, 90):
    draw.line((0, y, W, y), fill=(22, 33, 49))


def font(size, bold=False):
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype(str(FONT / ("segoeuib.ttf" if bold else "segoeui.ttf")), size)
    return FONTS[key]


def text(im, content, x, y, size, color=WHITE, bold=False, width=950, gap=1.12, max_lines=2):
    d = ImageDraw.Draw(im)
    f = font(size, bold)
    lines = []
    for paragraph in content.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if line and d.textlength(candidate, font=f) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
    if len(lines) > max_lines:
        raise ValueError(f"Texto excede {max_lines} líneas: {content}")
    for line in lines:
        d.text((x, y), line, font=f, fill=color)
        y += round(size * gap)
    return y


def ease(t):
    return 1 - (1 - max(0, min(1, t))) ** 3


def lerp_box(a, b, amount):
    return tuple(x + (y - x) * amount for x, y in zip(a, b))


def rounded_paste(base, overlay, xy, radius=18):
    mask = Image.new("L", overlay.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, overlay.width - 1, overlay.height - 1), radius=radius, fill=255)
    if overlay.mode == "RGBA":
        mask = ImageChops.multiply(mask, overlay.getchannel("A"))
    base.paste(overlay, xy, mask)


def screen_card(im, scene, local):
    x, y, w, h = 34, 422, 1012, 854
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x, y, x+w, y+h), radius=28, fill=(5, 11, 21), outline=(66, 83, 111), width=2)
    d.rounded_rectangle((x+2, y+2, x+w-2, y+52), radius=25, fill=(16, 27, 44))
    for k, color in enumerate(((226, 116, 124), GOLD, (125, 180, 160))):
        d.ellipse((x+20+k*25, y+20, x+33+k*25, y+33), fill=color)
    d.text((x+120, y+12), "KADI · ENTORNO DE DEMOSTRACIÓN", font=font(19, True), fill=MUTED)

    source = SHOTS[scene["screen"]]
    viewport = scene["focus"]
    image_box = (x+12, y+62, w-24, h-76)
    target = image_box[2], image_box[3]
    if viewport:
        progress = ease((local - 0.3) / 7.0)
        crop = lerp_box(viewport[0], viewport[1], progress)
        left, top, right, bottom = crop
        crop_px = (round(left*source.width), round(top*source.height), round(right*source.width), round(bottom*source.height))
        detail = ImageOps.fit(source.crop(crop_px), target, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        rounded_paste(im, detail, (image_box[0], image_box[1]), 10)

        # Persistent full-screen locator: viewers can see where the enlarged region sits.
        mini = (728, 494, 296, 169)
        d.rounded_rectangle((mini[0]-6, mini[1]-6, mini[0]+mini[2]+6, mini[1]+mini[3]+6), radius=15, fill=(5, 11, 21), outline=GOLD, width=2)
        overview = ImageOps.fit(source, (mini[2], mini[3]), method=Image.Resampling.LANCZOS)
        rounded_paste(im, overview, (mini[0], mini[1]), 10)
        # The screenshot itself is never edited; this outline only marks the zoomed area.
        md = ImageDraw.Draw(im)
        sx = mini[2] / source.width
        sy = mini[3] / source.height
        md.rectangle((mini[0]+crop_px[0]*sx, mini[1]+crop_px[1]*sy,
                      mini[0]+crop_px[2]*sx, mini[1]+crop_px[3]*sy), outline=(255, 214, 100), width=3)
    else:
        # Keep all three onboarding choices and their labels visible together.
        fit = ImageOps.contain(source, target, Image.Resampling.LANCZOS)
        px = image_box[0] + (target[0]-fit.width)//2
        py = image_box[1] + (target[1]-fit.height)//2
        rounded_paste(im, fit, (px, py), 10)
    return im


def scene_frame(index, local):
    scene = SCENES[index]
    im = BACKGROUND.copy()
    rounded_paste(im, LOGO, (58, 38), 0)
    d = ImageDraw.Draw(im)
    d.text((62, 132), scene["tag"], font=font(20, True), fill=GOLD)
    offset = round(18 * (1-ease(local/.55)))
    title_end = text(im, scene["title"], 60, 174+offset, 54, bold=True, width=950, gap=1.02, max_lines=2)
    detail_y = title_end + 5
    text(im, scene["detail"], 62, detail_y, 26, color=MUTED, width=960, gap=1.15, max_lines=2)
    screen_card(im, scene, local)

    if index == 5:
        d.rounded_rectangle((70, 1320, 1010, 1410), radius=18, fill=GOLD)
        d.text((114, 1338), "AGENDA TU DEMO", font=font(42, True), fill=NAVY)
        d.text((70, 1460), "kadi.technology", font=font(40, True), fill=WHITE)
    else:
        text(im, scene["chip"], 62, 1318, 33, bold=True, width=960, gap=1.1, max_lines=1)
        d.text((62, 1395), "kadi.technology", font=font(31, True), fill=GOLD)
    d.text((62, 1640), "PANTALLAS REALES · DATOS DE DEMOSTRACIÓN", font=font(18, True), fill=MUTED)
    for j in range(6):
        d.rounded_rectangle((62+j*160, 1744, 196+j*160, 1752), radius=4, fill=GOLD if j <= index else (53, 64, 80))
    return im


def frame(t):
    index = min(5, int(t // 5))
    local = t-index*5
    im = scene_frame(index, local)
    if index and local < .22:
        im = Image.blend(scene_frame(index-1, 4.99), im, ease(local/.22))
    return np.array(im)


def preview():
    sheet = Image.new("RGB", (1080, 1280), NAVY)
    for i in range(6):
        im = scene_frame(i, 2.55)
        im.save(OUT / f"escena-v2-{i+1:02d}.jpg", quality=94)
        sheet.paste(im.resize((360, 640)), ((i % 3) * 360, (i // 3) * 640))
    sheet.save(OUT / "storyboard-instagram-v2.jpg", quality=95)
    scene_frame(0, 2.55).save(OUT / "kadi-instagram-portada-v2.jpg", quality=95)


def render():
    silent = OUT / "reel-picture-v2.mp4"
    VideoClip(frame, duration=DURATION).write_videofile(str(silent), fps=FPS, codec="libx264", audio=False,
        preset="fast", threads=4, ffmpeg_params=["-crf", "19", "-pix_fmt", "yuv420p"], logger=None)
    music = ROOT / "output/video-kadi/music-original-ducked.wav"
    target = OUT / "kadi-instagram-reel-v2.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(music), "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-af", "afade=t=in:d=0.5,afade=t=out:st=28:d=2,loudnorm=I=-16:TP=-1.5:LRA=11",
        "-t", str(DURATION), "-movflags", "+faststart", str(target)], check=True)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json", str(target)], text=True))
    logo_hash = hashlib.sha256(LOGO_PATH.read_bytes()).hexdigest()
    screens = [{"file": name, "sha256": hashlib.sha256((OUT / "sources" / name).read_bytes()).hexdigest()}
        for name in sorted(SHOTS)]
    manifest = {
        "status": "v2_music_and_text_ready_no_narration",
        "format": "9:16",
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "probe": probe,
        "voice": None,
        "design": "Product-first crops pan across the real interface; a full-screen inset preserves context. Onboarding keeps all three model choices visible.",
        "logo": {"file": str(LOGO_PATH.relative_to(ROOT)), "sha256": logo_hash},
        "music": "Existing original KADI synthesis; no narration mixed",
        "screens": screens,
        "scenes": SCENES,
    }
    (OUT / "manifest-v2.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "texto-instagram-v2.txt").write_text(
        "Tu clínica en orden. Del expediente al cobro.\n\n"
        "Conoce cómo KADI conecta el expediente, la hospitalización y las cuentas del paciente en el mismo entorno.\n\n"
        "Elige el modelo que se parece a tu operación: Hospital, Clínica o Grooming.\n\n"
        "Agenda una demostración en kadi.technology.\n\n"
        "Pantallas reales con datos de demostración.\n\n"
        "#KADI #SoftwareVeterinario #ClinicaVeterinaria #GestionVeterinaria\n", encoding="utf-8")
    print("REEL_V2_COMPLETE", target, target.stat().st_size, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    preview()
    if not args.preview_only:
        render()
