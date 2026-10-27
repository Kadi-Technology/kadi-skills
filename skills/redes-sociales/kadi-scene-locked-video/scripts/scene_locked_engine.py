#!/usr/bin/env python3
"""
KADI Scene-Locked Video Engine (v2.0 - Zero Neon, Institutional Executive Edition)
Locks each visual scene's duration strictly to its synthesized TTS audio segment + breath padding.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Institutional Palette (Zero Neon)
BG_PRIMARY = (10, 18, 32)       # #0A1220
BG_CARD = (15, 27, 46)          # #0F1B2E
ACCENT_GOLD = (201, 162, 39)    # #C9A227
TEXT_MAIN = (246, 247, 250)     # #F6F7FA
TEXT_MUTED = (148, 163, 184)    # #94A3B8


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_scene_frame(scene: dict, width: int = 1080, height: int = 1920) -> Image.Image:
    canvas = Image.new("RGB", (width, height), BG_PRIMARY)
    draw = ImageDraw.Draw(canvas)

    # Top gold bar
    draw.rectangle([0, 0, width, 8], fill=ACCENT_GOLD)

    font_badge = load_font(28, bold=True)
    font_title = load_font(54, bold=True)
    font_sub = load_font(34, bold=False)
    font_caption = load_font(30, bold=False)

    badge = scene.get("badge", "KADI TECHNOLOGY").upper()
    draw.rounded_rectangle([72, 96, 72 + max(320, len(badge) * 20), 152], radius=12, fill=BG_CARD, outline=ACCENT_GOLD, width=2)
    draw.text((96, 108), badge, fill=ACCENT_GOLD, font=font_badge)

    headline = scene.get("headline", "")
    draw.text((72, 190), headline, fill=TEXT_MAIN, font=font_title)

    subheadline = scene.get("subheadline", "")
    if subheadline:
        draw.text((72, 270), subheadline, fill=TEXT_MUTED, font=font_sub)

    # Asset placement (screenshot or rendered PDF image)
    asset_path = scene.get("asset_path")
    if asset_path and Path(asset_path).exists():
        asset_file = Path(asset_path)
        if asset_file.suffix.lower() == ".pdf":
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(str(asset_file))
            page = pdf[0]
            pil_asset = page.render(scale=2.0).to_pil().convert("RGB")
        else:
            pil_asset = Image.open(asset_file).convert("RGB")

        max_w, max_h = width - 144, 1020
        pil_asset.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        ax = (width - pil_asset.width) // 2
        ay = 380 + (max_h - pil_asset.height) // 2
        draw.rounded_rectangle(
            [ax - 6, ay - 6, ax + pil_asset.width + 6, ay + pil_asset.height + 6],
            radius=16,
            fill=BG_CARD,
            outline=ACCENT_GOLD,
            width=2,
        )
        canvas.paste(pil_asset, (ax, ay))

    # Bottom editorial caption card
    narration = scene.get("caption") or scene.get("narration", "")
    if narration:
        draw.rounded_rectangle([64, height - 360, width - 64, height - 120], radius=18, fill=BG_CARD, outline=ACCENT_GOLD, width=2)
        draw.text((96, height - 320), narration[:180], fill=TEXT_MAIN, font=font_caption)

    return canvas


def synthesize_tts(text: str, out_mp3: Path, voice: str = "es-CO-SalomeNeural") -> None:
    cmd = ["python", "-m", "edge_tts", "--voice", voice, "--text", text, "--write-media", str(out_mp3)]
    subprocess.run(cmd, check=True)


def build_scene_locked_video(manifest_path: Path, output_path: Path) -> None:
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
    import numpy as np

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    width = data.get("width", 1080)
    height = data.get("height", 1920)
    pad = float(data.get("breath_padding_sec", 0.35))

    clips = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for idx, scene in enumerate(scenes):
            frame_img = render_scene_frame(scene, width=width, height=height)
            arr = np.array(frame_img)
            narration = scene.get("narration", "").strip()
            if narration:
                mp3_path = tmp / f"scene_{idx:02d}.mp3"
                synthesize_tts(narration, mp3_path)
                audio_clip = AudioFileClip(str(mp3_path))
                duration = audio_clip.duration + pad
                img_clip = ImageClip(arr).with_duration(duration).with_audio(audio_clip)
            else:
                duration = float(scene.get("duration", 3.5))
                img_clip = ImageClip(arr).with_duration(duration)
            clips.append(img_clip)

        final = concatenate_videoclips(clips, method="compose")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(str(output_path), fps=30, codec="libx264", audio_codec="aac")


def main() -> None:
    parser = argparse.ArgumentParser(description="KADI Scene-Locked Video Engine")
    parser.add_argument("--manifest", required=True, help="Path to JSON scene manifest")
    parser.add_argument("--output", required=True, help="Output MP4 file path")
    args = parser.parse_args()
    build_scene_locked_video(Path(args.manifest), Path(args.output))


if __name__ == "__main__":
    main()
