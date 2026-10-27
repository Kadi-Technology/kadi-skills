"""Reel 9:16 (1080x1920) y gemelo 16:9 (1920x1080) 'Detras del codigo: Visor 3D del Portal Clínica Fundadora'.

- Capturas reales (publishable=true, pii_check=clean) del indice semantico, recortadas SIN la barra de navegacion
  del portal (asi no aparece el telefono comercial de la clinica).
- Locucion Salome (es-CO-SalomeNeural) sintetizada con edge-tts A ARCHIVO. 'chrono speak' solo sintetiza y
  reproduce (no tiene salida a archivo), por eso no se usa. Este script nunca reproduce audio.
- Pan y zoom suaves por remuestreo con caja flotante (LANCZOS), subtitulos en la zona segura central-inferior.
- 9:16 a 30 fps; 16:9 a 60 fps. Salida: assets/video_visor3d/
"""
from __future__ import annotations

import asyncio
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ASSETS_SRC, OUT, PALETTE as P, SRC, Canvas, contrast_ratio, load_font, write_json  # noqa: E402

VOICE = "es-CO-SalomeNeural"
RATE, PITCH = "+3%", "+5Hz"  # voz del agente 'chrono' del SDK (-5%), acelerada para caber en 45 s
OUT_DIR = OUT / "video_visor3d"
TMP = Path(__file__).resolve().parent / "_tmp_video"

NARRATION = [
    "Detrás del código: el visor 3D del portal de la Clínica Fundadora.",
    "Es un atlas de cuatro especies con catorce sistemas anatómicos, dibujado con WebGL puro, sin librerías.",
    "Cambia entre Anatomía, Rayos X y una TC simulada, con los niveles vertebrales rotulados.",
    "Debajo, un monitor simulado muestra ECG, pletismografía y signos vitales, con fines didácticos.",
    "Y con el puntero láser señalas una estructura mientras explicas.",
    "Es apoyo visual, no un diagnóstico. Míralo en el portal: el enlace está en la descripción.",
]
LEAD, GAP, TAIL = 0.4, 0.3, 0.8

# Escenas (coordenadas de la captura 1920x1080; la fuente es 3840x2160). (cx, cy, ancho) por keyframe.
SCENES = [
    {"kf": {"v": [(752, 520, 815), (752, 380, 600)], "w": [(790, 459, 1231), (750, 370, 760)]}, "src": "anat4k"},
    {"kf": {"v": [(752, 380, 600), (1378, 272, 430)], "w": [(750, 370, 760), (1250, 300, 640)]}, "src": "anat4k"},
    {"kf": {"v": [(752, 383, 815), (752, 383, 640)], "w": [(790, 459, 1231), (790, 400, 950)]}, "src": "rx4k",
     "kf2": {"v": [(752, 383, 815), (752, 383, 700)], "w": [(790, 459, 1231), (790, 400, 950)]}, "src2": "tc4k"},
    {"kf": {"v": [(752, 790, 700), (752, 790, 560)], "w": [(752, 800, 900), (752, 790, 820)]}, "src": "anat4k"},
    {"kf": {"v": [(752, 383, 815), (752, 383, 600)], "w": [(790, 459, 1231), (752, 383, 760)]}, "src": "laser4k"},
    None,  # lamina de cierre
]
CROP = (345, 113, 1576, 1000)  # region util del visor, sin barra de navegacion (coords 1920)


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


async def _synth(text: str, path: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(str(path))


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} fallo: {r.stderr[-800:]}")
    return r.stdout


def duration(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).strip())


def build_audio() -> tuple[Path, list[float], list[float]]:
    """Sintetiza cada frase a archivo, calcula la linea de tiempo y mezcla un WAV 44.1 kHz mono."""
    TMP.mkdir(parents=True, exist_ok=True)
    durs: list[float] = []
    wavs: list[Path] = []
    for i, text in enumerate(NARRATION):
        mp3 = TMP / f"seg_{i}.mp3"
        if not mp3.exists():
            asyncio.run(_synth(text, mp3))
        wv = TMP / f"seg_{i}.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wv)])
        durs.append(duration(wv))
        wavs.append(wv)
    starts, t = [], LEAD
    for d in durs:
        starts.append(t)
        t += d + GAP
    total = starts[-1] + durs[-1] + TAIL
    sr = 44100
    buf = np.zeros(int(total * sr) + sr, dtype=np.int16)
    for s, wv in zip(starts, wavs):
        with wave.open(str(wv)) as w:
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        i0 = int(s * sr)
        buf[i0:i0 + len(data)] = data
    out = TMP / "locucion.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(buf[: int(total * sr)].tobytes())
    return out, starts, durs


def chunks_for(text: str, max_chars: int) -> list[str]:
    """Parte una frase en trozos de subtitulo de hasta dos lineas (por puntuacion y longitud)."""
    words = text.split()
    out, cur = [], ""
    limit = max_chars * 2
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) > limit and cur:
            out.append(cur)
            cur = w
        else:
            cur = trial
        if cur.endswith((".", ":", ";")) and not cur.endswith("Dr.") and len(cur) > max_chars:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def subtitle_track(starts: list[float], durs: list[float], max_chars: int) -> list[tuple[float, float, str]]:
    track = []
    for s, d, text in zip(starts, durs, NARRATION):
        parts = chunks_for(text, max_chars)
        weights = [len(p) for p in parts]
        acc = s
        for p, wgt in zip(parts, weights):
            seg = d * wgt / sum(weights)
            track.append((acc, acc + seg, p))
            acc += seg
    return track


def srt(track, path: Path) -> None:
    def ts(x: float) -> str:
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    lines = []
    for i, (a, b, t) in enumerate(track, 1):
        lines += [str(i), f"{ts(a)} --> {ts(b)}", t, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def wrap(text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def render_subtitle(text: str, box_w: int, font_px: int, bg_rgba, fg, size) -> Image.Image:
    font = load_font("sans_b", font_px)
    lines = wrap(text, font, box_w - 80)
    lh = int(font_px * 1.3)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y0 = (size[1] - lh * len(lines)) // 2
    for i, ln in enumerate(lines):
        w = font.getlength(ln)
        d.text(((size[0] - w) / 2, y0 + i * lh), ln, font=font, fill=fg + (255,))
    return im


def load_sources() -> dict[str, Image.Image]:
    out = {}
    x0, y0, x1, y1 = CROP
    for key in ("anat4k", "rx4k", "tc4k", "laser4k"):
        im = Image.open(ASSETS_SRC / SRC[key]).convert("RGB")
        assert im.size == (3840, 2160), (key, im.size)
        out[key] = im.crop((x0 * 2, y0 * 2, x1 * 2, y1 * 2))
    return out


def view(img: Image.Image, kf, t: float, out_size: tuple[int, int]) -> Image.Image:
    (cx0, cy0, w0), (cx1, cy1, w1) = kf[0], kf[-1]
    e = ease(t)
    cx, cy, w = cx0 + (cx1 - cx0) * e, cy0 + (cy1 - cy0) * e, w0 + (w1 - w0) * e
    aspect = out_size[0] / out_size[1]
    h = w / aspect
    # a coordenadas del recorte (4K): (valor_1920 - CROP_origen) * 2
    ox, oy = CROP[0], CROP[1]
    bx0, by0 = (cx - w / 2 - ox) * 2, (cy - h / 2 - oy) * 2
    bw, bh = w * 2, h * 2
    bx0 = min(max(0.0, bx0), img.size[0] - bw)
    by0 = min(max(0.0, by0), img.size[1] - bh)
    return img.resize(out_size, Image.LANCZOS, box=(bx0, by0, bx0 + bw, by0 + bh))


def scene_media(sc, srcs, t: float, size) -> Image.Image:
    o = "w" if size[0] > size[1] * 1.5 else "v"
    if "src2" in sc:
        if t < 0.5:
            return view(srcs[sc["src"]], sc["kf"][o], t / 0.5, size)
        return view(srcs[sc["src2"]], sc["kf2"][o], (t - 0.5) / 0.5, size)
    return view(srcs[sc["src"]], sc["kf"][o], t, size)


def slate(w: int, h: int, vertical: bool) -> Image.Image:
    s = w / 1080 if vertical else 1.0
    c = Canvas(w, h, scale=1.0 if not vertical else 1.0)
    if vertical:
        c.text(60, 560, "APOYO VISUAL,", "serif_b", 96, P["cream"], max_w=960, align="center", role="cierre")
        c.text(60, 670, "NO DIAGNÓSTICO", "serif_b", 96, P["gold"], max_w=960, align="center", role="cierre")
        c.text(90, 860, "Es material educativo: no sustituye el criterio del médico veterinario ni la imagen diagnóstica real.", "sans", 44, P["cream"], max_w=900, align="center", line_h=1.3, role="cierre")
        c.rect((90, 1090, 990, 1220), P["gold"], radius=65)
        c.text(90, 1128, "Míralo en el portal: enlace en la descripción", "sans_b", 34, P["ink"], max_w=900, align="center", role="boton")
        c.text(60, 280, "KADI TECHNOLOGY", "sans_b", 30, P["muted"], max_w=960, align="center", role="marca", tracking=6)
    else:
        c.text(160, 250, "APOYO VISUAL, NO DIAGNÓSTICO", "serif_b", 80, P["cream"], max_w=1600, align="center", role="cierre")
        c.text(260, 480, "Es material educativo: no sustituye el criterio del médico veterinario ni la imagen diagnóstica real del paciente.", "sans", 46, P["cream"], max_w=1400, align="center", line_h=1.3, role="cierre")
        c.rect((560, 690, 1360, 810), P["gold"], radius=60)
        c.text(560, 724, "Míralo en el portal: enlace en la descripción", "sans_b", 32, P["ink"], max_w=800, align="center", role="boton")
        c.text(160, 90, "KADI TECHNOLOGY", "sans_b", 28, P["muted"], max_w=1600, align="center", role="marca", tracking=6)
    slate.records = c.records  # type: ignore[attr-defined]
    return c.im


def frame_writer(w: int, h: int, fps: int, audio: Path, out_path: Path) -> subprocess.Popen:
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-i", str(audio), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-g", str(fps * 2), "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", "-shortest", str(out_path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render(vertical: bool, fps: int, audio: Path, starts, durs, srcs, out_path: Path) -> dict:
    W, H = (1080, 1920) if vertical else (1920, 1080)
    total = starts[-1] + durs[-1] + TAIL
    n = int(round(total * fps))
    bounds = [0.0] + starts[1:] + [total]  # inicio de cada escena
    track = subtitle_track(starts, durs, 30 if vertical else 62)
    # pre-render
    if vertical:
        panel = (40, 330, 1040, 1180)
        pw, ph = panel[2] - panel[0], panel[3] - panel[1]
        sub_box = (40, 1215, 1040, 1495)
        sw, sh = sub_box[2] - sub_box[0], sub_box[3] - sub_box[1]
        base = Image.new("RGB", (W, H), P["bg"])
        bd = ImageDraw.Draw(base)
        bd.rounded_rectangle(sub_box, radius=28, fill=P["panel"])
        bd.rounded_rectangle([panel[0] - 4, panel[1] - 4, panel[2] + 4, panel[3] + 4], radius=30, fill=P["panel_hi"])
        kf = load_font("mono_b", 30)
        k = "DETRÁS DEL CÓDIGO"
        x = (W - (kf.getlength(k) + 6 * (len(k) - 1))) / 2
        for ch in k:
            bd.text((x, 262), ch, font=kf, fill=P["gold"])
            x += kf.getlength(ch) + 6
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=26, fill=255)
        media_size = (pw, ph)
        contrast = contrast_ratio(P["cream"], P["panel"])
        sub_fg = P["cream"]
        subs = {t: render_subtitle(t, sw, 54, None, sub_fg, (sw, sh)) for _, _, t in track}
    else:
        media_size = (W, H)
        band_y0, band_y1 = 860, 1010
        alpha = 0.80
        band_rgb = np.array((6, 18, 14), dtype=np.float32)
        subs = {t: render_subtitle(t, W - 200, 46, None, P["cream"], (W, band_y1 - band_y0)) for _, _, t in track}
        # peor caso: fondo blanco bajo la banda
        worst_bg = alpha * band_rgb + (1 - alpha) * 255
        contrast = contrast_ratio(P["cream"], tuple(int(v) for v in worst_bg))
        chip_font = load_font("sans_b", 26)
        chip = Image.new("RGBA", (420, 56), (0, 0, 0, 0))
        cd = ImageDraw.Draw(chip)
        cd.rounded_rectangle([0, 0, 419, 55], radius=28, fill=(6, 18, 14, 215))
        cd.text((24, 12), "DETRÁS DEL CÓDIGO", font=chip_font, fill=P["gold"] + (255,))
        chip_contrast = contrast_ratio(P["gold"], (int(0.84 * 6 + 0.16 * 255), int(0.84 * 18 + 0.16 * 255), int(0.84 * 14 + 0.16 * 255)))
    slate_im = slate(W, H, vertical)
    proc = frame_writer(W, H, fps, audio, out_path)
    xfade = 0.35
    for fi in range(n):
        t = fi / fps
        si = max(i for i, b in enumerate(bounds[:-1]) if t >= b)
        sc = SCENES[si]
        local = (t - bounds[si]) / max(1e-6, bounds[si + 1] - bounds[si])
        if sc is None:
            media = slate_im.resize(media_size) if slate_im.size != media_size else slate_im
            if vertical:
                media = slate_im
        else:
            media = scene_media(sc, srcs, local, media_size)
        # fundido cruzado con la escena previa
        if si > 0 and (t - bounds[si]) < xfade and not (vertical and sc is None):
            a = ease((t - bounds[si]) / xfade)
            psc = SCENES[si - 1]
            prev = scene_media(psc, srcs, 1.0, media_size) if psc is not None else slate_im
            media = Image.blend(prev, media, a)
        if vertical:
            if sc is None and si == len(SCENES) - 1:
                # la lamina de cierre ocupa todo el cuadro; el fundido se hace contra el fondo del panel
                if (t - bounds[si]) < xfade:
                    a = ease((t - bounds[si]) / xfade)
                    prevframe = base.copy()
                    prevframe.paste(scene_media(SCENES[si - 1], srcs, 1.0, media_size), (panel[0], panel[1]), mask)
                    frame = Image.blend(prevframe, slate_im, a)
                else:
                    frame = slate_im.copy()
            else:
                frame = base.copy()
                frame.paste(media, (panel[0], panel[1]), mask)
                cur = next((txt for a0, b0, txt in track if a0 <= t < b0), None)
                if cur:
                    frame.paste(subs[cur], (sub_box[0], sub_box[1]), subs[cur])
        else:
            if sc is None:
                frame = media.copy()
            else:
                frame = media.copy()
                cur = next((txt for a0, b0, txt in track if a0 <= t < b0), None)
                if cur:
                    ov = Image.new("RGBA", (W, band_y1 - band_y0), (6, 18, 14, int(255 * alpha)))
                    reg = frame.crop((0, band_y0, W, band_y1)).convert("RGBA")
                    reg = Image.alpha_composite(reg, ov)
                    reg = Image.alpha_composite(reg, subs[cur])
                    frame.paste(reg.convert("RGB"), (0, band_y0))
                frame.paste(chip, (60, 50), chip)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg fallo al codificar")
    info = {
        "archivo": out_path.name, "formato": f"{W}x{H}", "fps": fps, "duracion_s": round(total, 2),
        "subtitulos_contraste": round(contrast, 2), "subtitulos_pasa_AA": contrast >= 4.5,
        "lamina_cierre_textos": slate.records,  # type: ignore[attr-defined]
        "lamina_cierre_pasa_AA": all(r["pass"] for r in slate.records),  # type: ignore[attr-defined]
    }
    if not vertical:
        info["chip_contraste"] = round(chip_contrast, 2)
    return info


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audio, starts, durs = build_audio()
    total = starts[-1] + durs[-1] + TAIL
    print("duracion total", round(total, 2), "s; frases", [round(d, 2) for d in durs])
    assert 30 <= total <= 45, f"la duracion {total:.1f}s esta fuera de 30-45 s"
    srcs = load_sources()
    report = {"voz": VOICE, "rate": RATE, "pitch": PITCH, "motor": "edge-tts a archivo (chrono speak solo reproduce)",
              "narracion": NARRATION, "videos": []}
    srt(subtitle_track(starts, durs, 30), OUT_DIR / "subtitulos_9x16.srt")
    srt(subtitle_track(starts, durs, 62), OUT_DIR / "subtitulos_16x9.srt")
    (OUT_DIR / "locucion_salome.wav").write_bytes(audio.read_bytes())
    report["videos"].append(render(True, 30, audio, starts, durs, srcs, OUT_DIR / "reel_visor3d_9x16_1080x1920.mp4"))
    report["videos"].append(render(False, 60, audio, starts, durs, srcs, OUT_DIR / "visor3d_16x9_1920x1080_60fps.mp4"))
    write_json(OUT_DIR / "video_build_report.json", report)
    print(json.dumps({v["archivo"]: (v["duracion_s"], v["subtitulos_contraste"]) for v in report["videos"]}, indent=1))


if __name__ == "__main__":
    main()
