"""Carrusel IG 4:5 (1080x1350, 7 laminas) 'Detras del codigo: Visor 3D del Portal Clínica Fundadora'.

Usa capturas reales (publishable=true, pii_check=clean) y verifica el contraste WCAG AA de cada texto
contra los pixeles reales del lienzo. Salida: assets/carrusel_ig_visor3d/
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, PALETTE as P, SRC, Canvas, crop4k, write_json  # noqa: E402

W, H = 1080, 1350
OUT_DIR = OUT / "carrusel_ig_visor3d"
TOTAL = 7


def chrome(c: Canvas, n: int, kicker: str) -> None:
    c.text(60, 64, kicker, "mono_b", 26, P["gold"], max_w=960, role="kicker", tracking=3)
    c.text(60, 1268, "KADI TECHNOLOGY", "sans_b", 24, P["muted"], max_w=500, role="pie", tracking=4)
    c.text(660, 1268, f"{n} / {TOTAL}", "sans_b", 24, P["muted"], max_w=360, align="right", role="pie")


def title(c: Canvas, y: float, text: str, size: float = 62) -> float:
    return c.text(60, y, text, "serif_b", size, P["cream"], max_w=960, line_h=1.14, role="titulo")


def body(c: Canvas, y: float, text: str, size: float = 36, color=None) -> float:
    return c.text(60, y, text, "sans", size, color or P["cream"], max_w=960, line_h=1.32, role="cuerpo")


def slide_1() -> Canvas:
    c = Canvas(W, H)
    chrome(c, 1, "DETRÁS DEL CÓDIGO")
    y = title(c, 112, "KADI Anatomy 3D: Demo Pública Básica en el portal de la Clínica Fundadora", 58)
    shot = crop4k(SRC["anat4k"], (345, 113, 1160, 900))
    box = c.image(shot, (125, y + 30, 955, y + 30 + 802), radius=22, border=P["panel_hi"], border_w=3)
    c.text(60, box[3] + 26, "Cómo está construida la demo web, en 7 láminas.", "sans", 36, P["muted"], max_w=960, align="center", role="subtitulo")
    return c


def code_card(c: Canvas, top: float, file_label: str, lines: list[str], colors: list) -> float:
    inner_w = 890
    heights = [c.measure(t, "mono", 34, max_w=inner_w, line_h=1.35) for t in lines]
    pad = 30
    total = pad * 2 + 34 + sum(heights) + 14 * (len(lines) - 1)
    c.rect((60, top, 1020, top + total), P["panel"], radius=22)
    y = c.text(96, top + pad, file_label, "sans_b", 26, P["muted"], max_w=inner_w, role="archivo", tracking=1)
    y += 8
    for t, col in zip(lines, colors):
        y = c.text(96, y, t, "mono", 34, col, max_w=inner_w, line_h=1.35, role="codigo") + 14
    return top + total


def slide_2() -> Canvas:
    c = Canvas(W, H)
    chrome(c, 2, "1 · EL MOTOR")
    y = title(c, 112, "WebGL puro, sin Three.js")
    y = body(c, y + 24, "La Demo Pública Básica se dibuja con WebGL directo. Así lo declaran los encabezados de sus archivos:", 34)
    end = code_card(c, y + 30, "visor3d.js",
                    ["/* KADI SCV · Visor de Anatomía 3D v2 (WebGL puro, sin librerías) */",
                     "const gl = cv.getContext('webgl', { antialias: false, alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true });"],
                    [P["gold"], P["cream"]])
    end = code_card(c, end + 26, "anatomia3d.js",
                    ["- Sin dependencias. Expone window.KADI_ANAT"],
                    [P["cream"]])
    c.text(60, end + 24, "Texto copiado de los archivos públicos del portal.", "sans", 28, P["muted"], max_w=960, role="nota")
    return c


def slide_3() -> Canvas:
    c = Canvas(W, H)
    chrome(c, 3, "2 · EL MODELO")
    y = title(c, 112, "Un modelo procedural")
    y = body(c, y + 24, "Atlas anatómico procedural: un conjunto de 344 580 puntos (cifra de la captura) que genera el propio código y que se ancla a niveles vertebrales (C7, T13, L7, S3, Cd), costillas, esternón y pelvis.", 34)
    dog = crop4k(SRC["anat4k"], (480, 205, 1030, 600))
    c.image(dog, (60, y + 30, 1020, y + 30 + 690), radius=22, border=P["panel_hi"], border_w=3)
    return c


def slide_4() -> Canvas:
    c = Canvas(W, H)
    chrome(c, 4, "3 · LOS SISTEMAS")
    y = title(c, 112, "Cuatro especies, 14 sistemas anatómicos", 58)
    y = body(c, y + 24, "Elige qué sistemas ver: piel, esqueleto, corazón, sistema nervioso y más. Hay búsqueda por nombre y niveles vertebrales.", 34)
    panel = crop4k(SRC["anat4k"], (1180, 115, 1576, 430))
    c.image(panel, (100, y + 32, 980, y + 32 + 700), radius=22, border=P["panel_hi"], border_w=3)
    return c


def slide_5() -> Canvas:
    c = Canvas(W, H)
    chrome(c, 5, "4 · LOS MODOS")
    y = title(c, 112, "Anatomía, Rayos X y TC")
    rows = [
        ("anat4k", "Anatomía", "Puntos con color por sistema."),
        ("rx4k", "Rayos X", "Niveles vertebrales rotulados sobre el modelo."),
        ("tc4k", "TC simulada", "Corte axial con ventanas Blando, Pulmón, Hueso, Cerebro, Mediastino y Angio, más contraste IV."),
    ]
    top = y + 26
    for i, (key, label, desc) in enumerate(rows):
        y0 = top + i * 322
        shot = crop4k(SRC[key], (345, 113, 1160, 655))
        c.image(shot, (60, y0, 500, y0 + 296), radius=18, border=P["panel_hi"], border_w=3)
        yy = c.text(536, y0 + 14, label, "serif_b", 44, P["gold"], max_w=484, role="modo")
        c.text(536, yy + 8, desc, "sans", 31, P["cream"], max_w=484, line_h=1.3, role="modo-desc")
    return c


def slide_6() -> Canvas:
    c = Canvas(W, H)
    chrome(c, 6, "5 · EL MONITOR")
    y = title(c, 112, "Monitor multiparamétrico simulado")
    y = body(c, y + 24, "ECG II y PLETH junto con FC, SpO₂, FR, T y PAS. Es una simulación didáctica del portal, no un paciente.", 34)
    mon = crop4k(SRC["anat4k"], (345, 668, 1160, 900))
    box = c.image(mon, (60, y + 34, 1020, y + 34 + 271), radius=22, border=P["panel_hi"], border_w=3)
    labels = [("FC", "lpm"), ("SpO₂", "%"), ("FR", "rpm"), ("T", "°C"), ("PAS", "mmHg")]
    top = box[3] + 44
    cell_w = (960 - 4 * 14) / 5
    for i, (name, unit) in enumerate(labels):
        x0 = 60 + i * (cell_w + 14)
        c.rect((x0, top, x0 + cell_w, top + 150), P["panel"], radius=18)
        c.text(x0, top + 22, name, "serif_b", 42, P["gold"], max_w=cell_w, align="center", role="parametro")
        c.text(x0, top + 88, unit, "mono_b", 28, P["cream"], max_w=cell_w, align="center", role="unidad")
    c.rect((60, top + 190, 1020, top + 190 + 230), P["panel"], radius=22)
    yy = c.text(96, top + 190 + 28, "Qué muestra", "serif_b", 38, P["gold"], max_w=890, role="panel")
    c.text(96, yy + 10, "Un trazo ECG II y una onda PLETH con sus parámetros, todo simulado para enseñar y no vinculado a ningún paciente.",
           "sans", 31, P["cream"], max_w=890, line_h=1.3, role="panel")
    return c


def slide_7() -> Canvas:
    c = Canvas(W, H)
    chrome(c, 7, "6 · LÍMITES Y VERSIONES")
    y = title(c, 112, "Demo Básica vs Suite Pro", 64)
    y = body(c, y + 24, "La Demo Pública Básica en web es apoyo visual para tutores. La Suite Clínica Pro avanzada vive integrada en KADI SCV (v1.8.0-rc.4, en validación para despliegue; no en producción general).", 33)
    top = y + 36
    c.rect((60, top, 1020, top + 130), P["gold"], radius=65)
    c.text(60, top + 34, "Míralo en el portal: enlace en la descripción", "sans_b", 36, P["ink"], max_w=960, align="center", role="boton")
    card_top = top + 170
    c.rect((60, card_top, 1020, card_top + 400), P["panel"], radius=22)
    yy = c.text(96, card_top + 30, "Cohorte KADI Founders #01", "serif_b", 42, P["gold"], max_w=890, role="cohorte")
    yy = c.text(96, yy + 8, "10 plazas para clínicas veterinarias.", "sans", 32, P["cream"], max_w=890, role="cohorte")
    cy = yy + 26
    d = 76
    gap = (890 - 10 * d) / 9
    for i in range(10):
        x0 = 96 + i * (d + gap)
        label = f"{i + 1:03d}"
        if i == 0:
            c.ellipse((x0, cy, x0 + d, cy + d), fill=P["gold"])
            c.text(x0, cy + 22, label, "mono_b", 26, P["ink"], max_w=d, align="center", role="plaza")
        else:
            c.ellipse((x0, cy, x0 + d, cy + d), outline=P["gold"], width=3)
            c.text(x0, cy + 22, label, "mono_b", 26, P["cream"], max_w=d, align="center", role="plaza")
    c.text(96, cy + d + 28, "#001 asignada a la Clínica Fundadora. De la #002 a la #010, abiertas.", "sans", 31, P["cream"], max_w=890, line_h=1.3, role="cohorte")
    return c


ALT = [
    "Captura de la Demo Pública Básica de KADI Anatomy 3D del portal de la Clínica Fundadora: modelo de perro en vista 3/4 como un conjunto de puntos sobre fondo verde oscuro.",
    "Dos líneas de código del archivo visor3d.js sobre fondo verde oscuro: el comentario de encabezado que dice WebGL puro, sin librerías, y la creación del contexto webgl.",
    "Acercamiento al modelo de perro en KADI Anatomy 3D: puntos de colores que dibujan huesos y órganos.",
    "Panel de sistemas de KADI Anatomy 3D con 14 botones: Piel, Esqueleto, Digestivo, Articular, Respiratorio, Corazón, Circulación, Linfático, Urinario, Endocrino, Reproductor, Sentidos, Nervioso y Músculos.",
    "Tres capturas de KADI Anatomy 3D, una por modo: Anatomía, Rayos X con niveles vertebrales rotulados y TC con panel de corte axial.",
    "Monitor multiparamétrico simulado del portal con trazo ECG II en verde, onda PLETH en azul y valores de FC, SpO2, FR, temperatura y PAS.",
    "Lámina de cierre distinguiendo la Demo Pública Básica (apoyo visual) de la Suite Clínica Pro en KADI SCV v1.8.0-rc.4 en validación; recuadro de la cohorte KADI Founders #01 con 10 plazas, la #001 asignada y de la #002 a la #010 abiertas.",
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    builders = [slide_1, slide_2, slide_3, slide_4, slide_5, slide_6, slide_7]
    report = {"formato": "1080x1350 (4:5)", "min_contraste_exigido": 4.5, "laminas": []}
    for i, build in enumerate(builders, start=1):
        c = build()
        path = OUT_DIR / f"ig_carrusel_visor3d_{i:02d}.png"
        c.im.save(path, optimize=True)
        r = c.report()
        report["laminas"].append({"archivo": path.name, "ancho": c.im.size[0], "alto": c.im.size[1],
                                  "alt_text": ALT[i - 1], "textos": r["texts"], "peor_contraste": r["worst_contrast"],
                                  "aprueba_AA": r["all_pass"], "detalle": r["details"]})
        print(path.name, c.im.size, "peor contraste", r["worst_contrast"], "AA" if r["all_pass"] else "FALLA")
    report["peor_contraste_global"] = min(l["peor_contraste"] for l in report["laminas"])
    report["todas_aprueban_AA"] = all(l["aprueba_AA"] for l in report["laminas"])
    write_json(OUT_DIR / "contraste_wcag.json", report)
    print("peor contraste global:", report["peor_contraste_global"])


if __name__ == "__main__":
    main()
