"""Utilidades compartidas para construir los activos del LOTE-01 (tipografia, lienzo, contraste WCAG)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]  # ...\RedesSociales
ASSETS_SRC = ROOT / "WebPage" / "assets_por_proyecto"
LOTE = ROOT / "Campanas" / "LOTE-01"
OUT = LOTE / "assets"
FONT_DIR = Path(r"C:\Windows\Fonts")

FONTS = {
    "serif_b": "georgiab.ttf",
    "serif": "georgia.ttf",
    "sans": "segoeui.ttf",
    "sans_b": "segoeuib.ttf",
    "mono": "consola.ttf",
    "mono_b": "consolab.ttf",
}

PALETTE = {
    "bg": (14, 33, 27),
    "panel": (23, 52, 43),
    "panel_hi": (31, 68, 56),
    "cream": (245, 239, 225),
    "muted": (185, 199, 190),
    "gold": (226, 182, 95),
    "coral": (242, 107, 94),
    "ink": (14, 33, 27),
    "white": (255, 255, 255),
}

MIN_CONTRAST = 4.5  # WCAG 2.1 AA texto normal; se exige tambien al texto grande


def _lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(a, b) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def region_worst_contrast(region: np.ndarray, fg) -> float:
    """Peor relacion de contraste entre el color de texto y cualquier pixel de fondo de la region."""
    arr = region.reshape(-1, region.shape[-1])[:, :3].astype(np.float64) / 255.0
    lin = np.where(arr <= 0.03928, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    lf = luminance(fg)
    hi = np.maximum(lum, lf)
    lo = np.minimum(lum, lf)
    return float(((hi + 0.05) / (lo + 0.05)).min())


@lru_cache(maxsize=None)
def load_font(key: str, size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / FONTS[key]), size_px)


class Canvas:
    """Lienzo con unidades de diseno 1080 de ancho (escala s) y verificacion de contraste por cada texto."""

    def __init__(self, width: int, height: int, scale: float = 1.0, bg=PALETTE["bg"]):
        self.w, self.h, self.s = width, height, scale
        self.im = Image.new("RGB", (width, height), bg)
        self.d = ImageDraw.Draw(self.im)
        self.records: list[dict] = []

    def u(self, v: float) -> int:
        return int(round(v * self.s))

    def font(self, key: str, size: float) -> ImageFont.FreeTypeFont:
        return load_font(key, max(8, self.u(size)))

    def rect(self, box, fill, radius: float = 0, outline=None, width: float = 0):
        x0, y0, x1, y1 = [self.u(v) for v in box]
        if radius:
            self.d.rounded_rectangle([x0, y0, x1, y1], radius=self.u(radius), fill=fill, outline=outline, width=self.u(width) if width else 0)
        else:
            self.d.rectangle([x0, y0, x1, y1], fill=fill, outline=outline, width=self.u(width) if width else 0)

    def ellipse(self, box, fill=None, outline=None, width: float = 0):
        x0, y0, x1, y1 = [self.u(v) for v in box]
        self.d.ellipse([x0, y0, x1, y1], fill=fill, outline=outline, width=self.u(width) if width else 0)

    def wrap(self, text: str, font: ImageFont.FreeTypeFont, max_w_px: int) -> list[str]:
        lines: list[str] = []
        for para in text.split("\n"):
            words = para.split(" ")
            cur = ""
            for w in words:
                trial = (cur + " " + w).strip()
                if font.getlength(trial) <= max_w_px or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
        return lines

    def measure(self, text, key="sans", size=36, max_w=None, line_h=1.28, x=0) -> float:
        """Alto (unidades de diseno) que ocupara un texto envuelto, sin dibujarlo."""
        font = self.font(key, size)
        max_px = self.u(max_w) if max_w else self.w - self.u(x) - self.u(40)
        lines = self.wrap(text, font, max_px)
        return int(round(font.size * line_h)) * len(lines) / self.s

    def text(self, x, y, text, key="sans", size=36, color=PALETTE["cream"], max_w=None, line_h=1.28,
             align="left", role="", tracking: float = 0.0) -> float:
        """Dibuja texto, verifica el contraste contra los pixeles que tiene debajo y devuelve la y inferior (unidades de diseno)."""
        font = self.font(key, size)
        max_px = self.u(max_w) if max_w else self.w - self.u(x) - self.u(40)
        lines = self.wrap(text, font, max_px)
        lh = int(round(font.size * line_h))
        px0, py0 = self.u(x), self.u(y)
        bottom = py0 + lh * len(lines)
        x_off = []
        widths = []
        for ln in lines:
            wl = font.getlength(ln) + tracking * self.s * max(0, len(ln) - 1)
            widths.append(wl)
            if align == "center":
                x_off.append(px0 + (max_px - wl) / 2)
            elif align == "right":
                x_off.append(px0 + max_px - wl)
            else:
                x_off.append(px0)
        bx0 = int(min(x_off))
        bx1 = int(max(o + w for o, w in zip(x_off, widths)))
        region = np.asarray(self.im.crop((max(0, bx0), max(0, py0), min(self.w, bx1 + 1), min(self.h, bottom))))
        worst = region_worst_contrast(region, color)
        self.records.append({
            "role": role or key,
            "text": text.replace("\n", " ")[:70],
            "size_px": font.size,
            "fg": "#%02X%02X%02X" % tuple(color),
            "worst_contrast": round(worst, 2),
            "min_required": MIN_CONTRAST,
            "pass": worst >= MIN_CONTRAST,
        })
        if worst < MIN_CONTRAST:
            raise ValueError(f"Contraste insuficiente ({worst:.2f}) en '{text[:40]}'")
        for i, ln in enumerate(lines):
            yy = py0 + i * lh
            if tracking:
                cx = x_off[i]
                for ch in ln:
                    self.d.text((cx, yy), ch, font=font, fill=color)
                    cx += font.getlength(ch) + tracking * self.s
            else:
                self.d.text((x_off[i], yy), ln, font=font, fill=color)
        return bottom / self.s

    def image(self, img: Image.Image, box, radius: float = 18, mode: str = "cover", border=None, border_w: float = 2):
        x0, y0, x1, y1 = [self.u(v) for v in box]
        bw, bh = x1 - x0, y1 - y0
        iw, ih = img.size
        k = max(bw / iw, bh / ih) if mode == "cover" else min(bw / iw, bh / ih)
        nw, nh = max(1, int(round(iw * k))), max(1, int(round(ih * k)))
        resized = img.convert("RGB").resize((nw, nh), Image.LANCZOS)
        if mode == "cover":
            left, top = (nw - bw) // 2, (nh - bh) // 2
            tile = resized.crop((left, top, left + bw, top + bh))
            px, py = x0, y0
        else:
            tile = resized
            px, py = x0 + (bw - nw) // 2, y0 + (bh - nh) // 2
        mask = Image.new("L", tile.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.size[0] - 1, tile.size[1] - 1], radius=self.u(radius), fill=255)
        self.im.paste(tile, (px, py), mask)
        if border:
            self.d.rounded_rectangle([px, py, px + tile.size[0] - 1, py + tile.size[1] - 1], radius=self.u(radius), outline=border, width=self.u(border_w))
        return (px / self.s, py / self.s, (px + tile.size[0]) / self.s, (py + tile.size[1]) / self.s)

    def report(self) -> dict:
        worst = min((r["worst_contrast"] for r in self.records), default=None)
        return {"texts": len(self.records), "worst_contrast": worst, "all_pass": all(r["pass"] for r in self.records), "details": self.records}


def crop4k(rel_path: str, box_1920: tuple[int, int, int, int]) -> Image.Image:
    """Recorta una captura 3840x2160 usando coordenadas de la version 1920x1080."""
    im = Image.open(ASSETS_SRC / rel_path).convert("RGB")
    assert im.size == (3840, 2160), (rel_path, im.size)
    x0, y0, x1, y1 = box_1920
    return im.crop((x0 * 2, y0 * 2, x1 * 2, y1 * 2))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# Rutas de capturas (relativas a assets_por_proyecto); todas publishable=true y pii_check=clean en el indice
SRC = {
    "anat4k": "anatomia-3d/live_2026-10-21/portal_visor3d_anatomia_monitor_ecg_desktop_3840x2160.png",
    "rx4k": "anatomia-3d/live_2026-10-21/portal_visor3d_rayos_x_monitor_ecg_desktop_3840x2160.png",
    "tc4k": "anatomia-3d/live_2026-10-21/portal_visor3d_tc_monitor_ecg_desktop_3840x2160.png",
    "laser4k": "anatomia-3d/live_2026-10-21/portal_visor3d_puntero_laser_desktop_3840x2160.png",
    "hero4k": "kadi-scv/live_2026-10-21/portal_hero_tablero_guardia_desktop_3840x2160.png",
    "aes_cif4k": "kadi-scv/live_2026-10-21/portal_tecnologia_aes256gcm_cifrado_desktop_3840x2160.png",
    "aes_dec4k": "kadi-scv/live_2026-10-21/portal_tecnologia_aes256gcm_descifrado_desktop_3840x2160.png",
    "aes4k": "kadi-scv/live_2026-10-21/portal_tecnologia_aes256gcm_desktop_3840x2160.png",
    "cartilla4k": "kadi-scv/live_2026-10-21/portal_tecnologia_cartilla_digital_desktop_3840x2160.png",
    "urg4k": "kadi-scv/live_2026-10-21/portal_urgencia_express_formulario_desktop_3840x2160.png",
    "gladys4k": "gladys/live_2026-10-21/portal_tecnologia_gladys_ia_demo_chat_desktop_3840x2160.png",
    "cohorte4k": "kadi-technology/live_2026-10-21/kadi_cohorte_founders_01_1_desktop_3840x2160.png",
    "portafolio4k": "kadi-technology/live_2026-10-21/kadi_portafolio_proyectos_1_desktop_3840x2160.png",
    "contacto4k": "kadi-technology/live_2026-10-21/kadi_contacto_1_desktop_3840x2160.png",
    "v_anat": "anatomia-3d/live_2026-10-21/portal_visor3d_anatomia_vertical_1080x1920.png",
    "v_rx": "anatomia-3d/live_2026-10-21/portal_visor3d_rayos_x_vertical_1080x1920.png",
    "v_tc": "anatomia-3d/live_2026-10-21/portal_visor3d_tc_vertical_1080x1920.png",
    "v_ecg": "anatomia-3d/live_2026-10-21/portal_monitor_ecg_pleth_vertical_1080x1920.png",
    "v_hero": "kadi-scv/live_2026-10-21/portal_hero_vertical_1080x1920.png",
    "v_tablero": "kadi-scv/live_2026-10-21/portal_tablero_guardia_vertical_1080x1920.png",
    "v_aes": "kadi-scv/live_2026-10-21/portal_aes256gcm_cifrado_vertical_1080x1920.png",
}
