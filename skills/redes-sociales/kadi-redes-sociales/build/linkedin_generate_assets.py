"""
KADI Technology - B2B Social Publisher Asset Generator
Generates:
1. LinkedIn Carousel #01: 8 slides (1080x1350), PDF multipage + PNGs (300 DPI)
2. Instagram Carousel #01: 6 slides (1080x1350) in carrusel_01/
3. Facebook Graphics: 3 high-res graphics (1200x630 landscape & 1080x1350 portrait)
All using Playwright Chromium with explicit executable path and Navy & Gold palette.
"""

import os
import sys
import base64
from pathlib import Path
from PIL import Image, JpegImagePlugin, PdfImagePlugin
import pypdfium2 as pdfium
from playwright.sync_api import sync_playwright

CHROME_EXEC = __import__("os").environ.get("KADI_CHROME_EXEC", "<RUTA_A_CHROMIUM_DE_PLAYWRIGHT>")
LINKEDIN_DIR = Path(r"RedesSociales\LinkedIn")
INSTAGRAM_DIR = Path(r"RedesSociales\Instagram")
FACEBOOK_DIR = Path(r"RedesSociales\Facebook")
WEB_DIR = Path(r"KadiWebPage")

def get_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            ext = os.path.splitext(path)[1].lower().replace(".", "")
            if ext == "jpg": ext = "jpeg"
            return f"data:image/{ext};base64," + base64.b64encode(f.read()).decode("utf-8")
    return ""

# Pre-load real screenshots and assets
img_scv_dash = get_b64(WEB_DIR / "portal/src/assets/img/kadi-scv-dashboard.webp")
img_gladys = get_b64(WEB_DIR / "portal/src/assets/img/gladys-asistente.webp")
img_scv_logo = get_b64(WEB_DIR / "portal/src/assets/img/kadi-scv-logo.png")
img_reception = get_b64(WEB_DIR / "src/assets/img/02_dashboard_principal_1080p-1280.f1721bee.webp")
img_caja = get_b64(WEB_DIR / "src/assets/img/07_caja_y_cuentas_1080p-1280.31292565.webp")
img_uci = get_b64(WEB_DIR / "src/assets/img/09_hospitalizacion_uci_1080p-1280.7e963e71.webp")
img_inventario = get_b64(WEB_DIR / "src/assets/img/11_inventario_vademecum_1080p-1280.c30c456e.webp")

KADI_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="40" height="40">
  <rect width="40" height="40" rx="10" fill="#0F1B2E" stroke="#C9A227" stroke-width="1.6"/>
  <path d="M13 9v22" stroke="#F6F7FA" stroke-width="3.4" stroke-linecap="round"/>
  <path d="M13.5 20 26.5 11.2M13.5 20l13 8.8" stroke="#C9A227" stroke-width="2.6" stroke-linecap="round"/>
  <circle cx="13" cy="20" r="3.3" fill="#F6F7FA"/>
  <circle cx="28" cy="10.3" r="3.3" fill="#C9A227"/>
  <circle cx="28" cy="29.7" r="3.3" fill="#94A3B8"/>
</svg>"""

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background-color: #0A1220;
  background-image: 
    radial-gradient(circle at 15% 15%, rgba(201, 162, 39, 0.08) 0%, transparent 45%),
    radial-gradient(circle at 85% 85%, rgba(15, 27, 46, 0.95) 0%, transparent 50%),
    radial-gradient(circle at 50% 50%, rgba(22, 35, 59, 0.45) 0%, transparent 60%);
  color: #F6F7FA;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.ambient-grid {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(201, 162, 39, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(201, 162, 39, 0.035) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
  z-index: 1;
}

.content-container {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  height: 100%;
  justify-content: space-between;
}

/* Header */
.slide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(201, 162, 39, 0.22);
  padding-bottom: 24px;
}

.brand-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-text-col {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 21px;
  letter-spacing: 0.14em;
  color: #F6F7FA;
}

.brand-tag {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  color: #C9A227;
  text-transform: uppercase;
  margin-top: 2px;
}

.header-badge {
  background: rgba(201, 162, 39, 0.12);
  border: 1px solid rgba(201, 162, 39, 0.45);
  padding: 8px 20px;
  border-radius: 999px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #C9A227;
}

/* Footer */
.slide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(201, 162, 39, 0.22);
  padding-top: 20px;
  font-size: 13px;
  color: #94A3B8;
  letter-spacing: 0.05em;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gold-dot {
  width: 9px;
  height: 9px;
  background-color: #C9A227;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(201, 162, 39, 0.6);
}

.footer-url {
  font-weight: 600;
  color: #F6F7FA;
}

.footer-tag {
  color: #C9A227;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* Common UI */
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(201, 162, 39, 0.12);
  border: 1px solid rgba(201, 162, 39, 0.35);
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #C9A227;
  text-transform: uppercase;
  margin-bottom: 14px;
  align-self: flex-start;
}

.headline {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 42px;
  line-height: 1.15;
  font-weight: 700;
  color: #F6F7FA;
  margin-bottom: 14px;
}

.headline .gold {
  color: #C9A227;
}

.subheadline {
  font-size: 18px;
  line-height: 1.5;
  color: #94A3B8;
  margin-bottom: 24px;
}

.glass-card {
  background: rgba(15, 27, 46, 0.85);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(201, 162, 39, 0.28);
  border-radius: 20px;
  box-shadow: 0 18px 40px -10px rgba(0, 0, 0, 0.55);
}

.gold-border-card {
  border-left: 4px solid #C9A227;
}

.icon-badge {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(201, 162, 39, 0.15);
  border: 1px solid rgba(201, 162, 39, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #C9A227;
  font-size: 20px;
  flex-shrink: 0;
}
"""

def wrap_html(body_content, width=1080, height=1350, padding="56px 64px 44px 64px"):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <style>
    {BASE_CSS}
    body {{
      width: {width}px;
      height: {height}px;
      padding: {padding};
    }}
  </style>
</head>
<body>
  <div class="ambient-grid"></div>
  <div class="content-container">
    {body_content}
  </div>
</body>
</html>"""

def make_header(counter_text):
    return f"""
    <header class="slide-header">
      <div class="brand-left">
        {KADI_LOGO_SVG}
        <div class="brand-text-col">
          <span class="brand-name">KADI TECHNOLOGY</span>
          <span class="brand-tag">SOFTWARE B2B DE MISIÓN CRÍTICA</span>
        </div>
      </div>
      <div class="header-badge">{counter_text}</div>
    </header>
    """

def make_footer(page_hint="Desliza para ver la arquitectura →"):
    return f"""
    <footer class="slide-footer">
      <div class="footer-left">
        <span class="gold-dot"></span>
        <span class="footer-url">kadi.technology</span>
        <span style="color:#64748B;">|</span>
        <span>Local Primero · Privacidad por Diseño</span>
      </div>
      <div class="footer-tag">{page_hint}</div>
    </footer>
    """

# ─────────────────────────────────────────────────────────────
# 1. LINKEDIN SLIDES (8 SLIDES)
# ─────────────────────────────────────────────────────────────

def get_linkedin_slide_1():
    header = make_header("REPORTE B2B #01")
    footer = make_footer("Desliza para explorar los 11 sistemas →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:28px; flex:1; padding: 20px 0;">
        <div>
          <div class="eyebrow">ARQUITECTURA DE SOFTWARE CRÍTICO · INFORME OFICIAL</div>
          <h1 class="headline" style="font-size: 52px; margin-bottom: 18px;">
            Arquitectura del Ecosistema <br><span class="gold">KADI Technology</span>
          </h1>
          <p class="subheadline" style="font-size: 20px; max-width: 900px; line-height: 1.55;">
            11 Sistemas de Misión Crítica diseñados para operar de forma local, proteger datos sensibles y mantener la decisión siempre en manos humanas.
          </p>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
          <div class="glass-panel" style="padding: 26px; border-radius: 18px;">
            <div class="icon-badge" style="margin-bottom: 16px;">🛡️</div>
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:18px; color:#F6F7FA; margin-bottom: 8px;">Local Primero</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">Operación autónoma sin depender de conexión para cobrar, atender o registrar.</p>
          </div>
          <div class="glass-panel" style="padding: 26px; border-radius: 18px;">
            <div class="icon-badge" style="margin-bottom: 16px;">🔒</div>
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:18px; color:#F6F7FA; margin-bottom: 8px;">Privacidad</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">Datos sensibles alojados en la sede de la organización, sin exponerlos a nubes públicas.</p>
          </div>
          <div class="glass-panel" style="padding: 26px; border-radius: 18px;">
            <div class="icon-badge" style="margin-bottom: 16px;">⚖️</div>
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:18px; color:#F6F7FA; margin-bottom: 8px;">Decisión Humana</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">La IA y los motores analíticos sugieren y asisten; el criterio del profesional manda.</p>
          </div>
        </div>

        <div class="glass-card gold-border-card" style="padding: 22px 28px; display:flex; align-items:center; justify-content:space-between; background:rgba(201,162,39,0.06);">
          <div>
            <span style="font-size:12px; font-weight:700; color:#C9A227; letter-spacing:0.12em; text-transform:uppercase;">Estado Operativo 2026</span>
            <div style="font-size:16px; font-weight:600; color:#F6F7FA; margin-top:4px;">
              Cohorte Founder #001 en Producción Activa (Salud Animal) + 10 Sistemas en Desarrollo Riguroso
            </div>
          </div>
          <div style="background:#C9A227; color:#0A1220; font-weight:700; padding:8px 18px; border-radius:8px; font-size:13px; font-family:'Space Grotesk';">
            COHORTE PILOTO
          </div>
        </div>
      </main>
      {footer}
    """)

def get_linkedin_slide_2():
    header = make_header("02 / 08")
    footer = make_footer("Vertical 01: Salud Animal →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:24px; flex:1; padding: 10px 0;">
        <div>
          <div class="eyebrow">FUNDAMENTOS DE INGENIERÍA</div>
          <h2 class="headline" style="font-size: 38px;">Cuatro Principios Inquebrantables</h2>
          <p class="subheadline" style="margin-bottom: 16px;">Frente a la fragilidad de servicios remotos convencionales, KADI construye sobre bases sólidas:</p>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <div class="glass-card" style="padding: 26px; border-top: 3px solid #C9A227;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
              <span style="color:#C9A227; font-weight:800; font-size:20px; font-family:'Space Grotesk';">01</span>
              <h3 style="font-size:19px; color:#F6F7FA;">Local Primero (Offline-First Real)</h3>
            </div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.55;">
              La aplicación y la base de datos (PostgreSQL / SQLite) se ejecutan dentro del equipo local. Si se corta el internet, la clínica, la constructora o el edificio no detienen sus cobros ni registros.
            </p>
          </div>

          <div class="glass-card" style="padding: 26px; border-top: 3px solid #C9A227;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
              <span style="color:#C9A227; font-weight:800; font-size:20px; font-family:'Space Grotesk';">02</span>
              <h3 style="font-size:19px; color:#F6F7FA;">Privacidad Desde el Diseño</h3>
            </div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.55;">
              Se recolecta lo indispensable y nada sale de las instalaciones del cliente sin una razón técnica justificada y autorización explícita. Sin telemetría abusiva ni minería de datos ajenos.
            </p>
          </div>

          <div class="glass-card" style="padding: 26px; border-top: 3px solid #C9A227;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
              <span style="color:#C9A227; font-weight:800; font-size:20px; font-family:'Space Grotesk';">03</span>
              <h3 style="font-size:19px; color:#F6F7FA;">Integridad Criptográfica</h3>
            </div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.55;">
              Presupuestos de obra, actas y recibos cuentan con huella digital SHA-256 e historial de revisiones inmutables. Lo que se emitió puede verificarse de forma independiente en cualquier momento.
            </p>
          </div>

          <div class="glass-card" style="padding: 26px; border-top: 3px solid #C9A227;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
              <span style="color:#C9A227; font-weight:800; font-size:20px; font-family:'Space Grotesk';">04</span>
              <h3 style="font-size:19px; color:#F6F7FA;">Personas al Centro</h3>
            </div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.55;">
              La tecnología asiste y amplifica el criterio del profesional. Nuestros asistentes y motores analíticos explican el origen de cada sugerencia; la decisión final es siempre humana.
            </p>
          </div>
        </div>
      </main>
      {footer}
    """)

def get_linkedin_slide_3():
    header = make_header("03 / 08")
    footer = make_footer("Vertical 02: Construcción y Obra →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:20px; flex:1; padding: 10px 0;">
        <div>
          <div class="eyebrow">SECTOR 01 · SALUD ANIMAL</div>
          <h2 class="headline" style="font-size: 38px;">KADI SCV & Asistente Gladys</h2>
          <p class="subheadline" style="margin-bottom: 14px;">Gestión clínica veterinaria integral en uso piloto (Cohorte Founder #001)</p>
        </div>

        <div style="display:grid; grid-template-columns: 1.15fr 0.85fr; gap: 24px; align-items: stretch;">
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div class="glass-card" style="padding: 22px;">
              <h4 style="color:#C9A227; font-size:16px; margin-bottom:10px; font-family:'Space Grotesk';">Capacidades del Sistema Clínico</h4>
              <ul style="list-style:none; display:flex; flex-direction:column; gap:8px; font-size:13.5px; color:#F6F7FA;">
                <li style="display:flex; gap:10px;"><span style="color:#C9A227;">✔</span> Expediente clínico, ficha médica y vademécum integral.</li>
                <li style="display:flex; gap:10px;"><span style="color:#C9A227;">✔</span> Agenda de citas, hospitalización y cuidados intensivos (UCI).</li>
                <li style="display:flex; gap:10px;"><span style="color:#C9A227;">✔</span> Punto de venta, caja, cuentas por cobrar y reportes financieros.</li>
                <li style="display:flex; gap:10px;"><span style="color:#C9A227;">✔</span> Control de inventario en lote y medicina preventiva.</li>
              </ul>
            </div>

            <div class="glass-card gold-border-card" style="padding: 20px;">
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                <span style="font-size:16px;">🤖</span>
                <h4 style="color:#F6F7FA; font-size:15px; font-family:'Space Grotesk';">Gladys: Asistente de IA Local</h4>
              </div>
              <p style="font-size:13px; color:#94A3B8; line-height:1.5;">
                Diseñada para correr en la máquina de la clínica sin enviar datos a internet. Conecta antecedentes y dosis en lenguaje natural. <strong style="color:#F6F7FA;">Límite:</strong> Apoyo informativo; no diagnostica ni receta.
              </p>
            </div>

            <div style="font-size:12px; color:#94A3B8; background:rgba(15,27,46,0.6); padding:10px 16px; border-radius:10px; border:1px solid rgba(201,162,39,0.15);">
              <strong style="color:#C9A227;">Stack:</strong> Laravel · PHP · PostgreSQL · React · TypeScript | <strong style="color:#C9A227;">Fase:</strong> v1.7 en uso piloto; v1.8 en preparación.
            </div>
          </div>

          <div class="glass-card" style="padding: 16px; display:flex; flex-direction:column; justify-content:center; align-items:center; overflow:hidden;">
            <div style="font-size:11px; font-weight:700; color:#C9A227; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:10px; align-self:flex-start;">EVIDENCIA DE INTERFAZ REAL</div>
            <img src="{img_scv_dash}" style="width:100%; border-radius:12px; border:1px solid rgba(201,162,39,0.3); box-shadow:0 8px 24px rgba(0,0,0,0.6);" alt="KADI SCV Dashboard">
            <div style="margin-top:14px; width:100%; display:flex; align-items:center; gap:10px;">
              <img src="{img_gladys}" style="width:48%; border-radius:8px; border:1px solid rgba(201,162,39,0.25);" alt="Gladys Assistant">
              <img src="{img_uci}" style="width:48%; border-radius:8px; border:1px solid rgba(201,162,39,0.25);" alt="UCI Monitoring">
            </div>
          </div>
        </div>
      </main>
      {footer}
    """)

def get_linkedin_slide_4():
    header = make_header("04 / 08")
    footer = make_footer("Vertical 03: Condominios y PropTech →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:22px; flex:1; padding: 10px 0;">
        <div>
          <div class="eyebrow">SECTOR 02 · CONSTRUCCIÓN Y CONTRATISTAS</div>
          <h2 class="headline" style="font-size: 38px;">Contract ERP: Control de Obra Sin Conexión</h2>
          <p class="subheadline" style="margin-bottom: 16px;">Aplicación de escritorio en Rust + Tauri para contratistas y despachos de arquitectura</p>
        </div>

        <div style="display:flex; flex-direction:column; gap:16px;">
          <div class="glass-card" style="padding: 24px; border-left: 4px solid #C9A227;">
            <h4 style="font-size:17px; color:#F6F7FA; margin-bottom:6px; font-family:'Space Grotesk';">1. Presupuestos por Partidas con Huella de Integridad</h4>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Cada presupuesto emitido conserva su historial de revisiones con huella inmutable SHA-256. Permite comparar al instante variaciones de precios unitarios y volúmenes entre versiones entregadas al cliente.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-left: 4px solid #C9A227;">
            <h4 style="font-size:17px; color:#F6F7FA; margin-bottom:6px; font-family:'Space Grotesk';">2. Órdenes de Cambio Formales</h4>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Elimina las fugas económicas causadas por acuerdos de palabra en la obra. Cualquier modificación en catálogo o especificación genera una orden formal con firma y trazabilidad contractual.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-left: 4px solid #C9A227;">
            <h4 style="font-size:17px; color:#F6F7FA; margin-bottom:6px; font-family:'Space Grotesk';">3. Aritmética Exacta en Enteros</h4>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Cálculos financieros ejecutados con precisión matemática de enteros (centavos), eliminando por completo los errores acumulativos de redondeo de punto flotante presentes en hojas de cálculo.
            </p>
          </div>
        </div>

        <div class="glass-card" style="padding: 16px 24px; display:flex; align-items:center; justify-content:space-between; background:rgba(201,162,39,0.08);">
          <div style="font-size:13px; color:#F6F7FA;">
            <strong style="color:#C9A227;">Tecnología:</strong> Tauri 2 · Rust · React 19 · TypeScript · SQLite Local
          </div>
          <div style="font-size:12px; color:#94A3B8;">
            * Herramienta de control interno; no sustituye comprobantes fiscales.
          </div>
        </div>
      </main>
      {footer}
    """)

def get_linkedin_slide_5():
    header = make_header("05 / 08")
    footer = make_footer("Vertical 04: Educación y Simulación →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:22px; flex:1; padding: 10px 0;">
        <div>
          <div class="eyebrow">SECTOR 03 · INMOBILIARIO Y CONDOMINIOS</div>
          <h2 class="headline" style="font-size: 38px;">TVillage: Cierre Mensual con Respaldo Jurídico</h2>
          <p class="subheadline" style="margin-bottom: 16px;">Administración de condominios con evidencia alineada a la Ley de Propiedad en Condominio CDMX</p>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <div class="glass-card" style="padding: 24px;">
            <div style="color:#C9A227; font-weight:700; font-size:14px; text-transform:uppercase; margin-bottom:8px;">Paso 1 al 3</div>
            <h4 style="font-size:18px; color:#F6F7FA; margin-bottom:8px; font-family:'Space Grotesk';">Cierre Mensual en 5 Pasos</h4>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Flujo guiado de conciliación asistida que explica con reglas claras la relación entre cuotas recibidas, adeudos históricos y gastos comprobados con soporte documental.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px;">
            <div style="color:#C9A227; font-weight:700; font-size:14px; text-transform:uppercase; margin-bottom:8px;">Gobernanza</div>
            <h4 style="font-size:18px; color:#F6F7FA; margin-bottom:8px; font-family:'Space Grotesk';">Visto Bueno de Vigilancia</h4>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              El Comité de Vigilancia revisa y aprueba cada versión preliminar con registro de identidad antes de la distribución formal a los condóminos.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px;">
            <div style="color:#C9A227; font-weight:700; font-size:14px; text-transform:uppercase; margin-bottom:8px;">Experiencia Móvil</div>
            <h4 style="font-size:18px; color:#F6F7FA; margin-bottom:8px; font-family:'Space Grotesk';">Acuses Sin Crear Cuenta</h4>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Cada condómino recibe un enlace individual seguro en su celular para consultar su estado de cuenta y registrar acuse de recibo de inmediato, sin registros engorrosos.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px;">
            <div style="color:#C9A227; font-weight:700; font-size:14px; text-transform:uppercase; margin-bottom:8px;">Seguridad Legal</div>
            <h4 style="font-size:18px; color:#F6F7FA; margin-bottom:8px; font-family:'Space Grotesk';">Bitácora Verificable con QR</h4>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Constancias de no adeudo y actas de asamblea emitidas con código QR de verificación pública de autenticidad y cadena de huellas digitales.
            </p>
          </div>
        </div>

        <div class="glass-card gold-border-card" style="padding: 16px 24px; display:flex; align-items:center; justify-content:space-between;">
          <div style="font-size:13px; color:#F6F7FA;">
            <strong style="color:#C9A227;">Stack:</strong> Node.js · Fastify · TypeScript · PostgreSQL · React | <strong style="color:#C9A227;">Fase:</strong> v0.2 funcional probada con datos demo.
          </div>
        </div>
      </main>
      {footer}
    """)

def get_linkedin_slide_6():
    header = make_header("06 / 08")
    footer = make_footer("Vertical 05: Herramientas IA y Documentos →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:22px; flex:1; padding: 10px 0;">
        <div>
          <div class="eyebrow">SECTORES 04 Y 05 · EDUCACIÓN Y VIDEOJUEGOS</div>
          <h2 class="headline" style="font-size: 38px;">Academia, Vital Signs Vet & Réquiem</h2>
          <p class="subheadline" style="margin-bottom: 16px;">Entornos interactivos de aprendizaje adaptativo y simulación con criterio</p>
        </div>

        <div style="display:flex; flex-direction:column; gap:16px;">
          <div class="glass-card" style="padding: 22px; border-left: 4px solid #C9A227;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <h4 style="font-size:18px; color:#F6F7FA; font-family:'Space Grotesk';">Academia (EdTech Adaptativo)</h4>
              <span style="font-size:12px; color:#C9A227; font-weight:700;">PROTOTIPO FUNCIONAL (3 RUTAS / 47 LECCIONES)</span>
            </div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Plataforma para aprender ingeniería de software construyendo de verdad. Ejecuta Python dentro del propio navegador mediante WebAssembly (Pyodide) sin conexión. Rutas adaptativas basadas en el dominio real del alumno.
            </p>
          </div>

          <div class="glass-card" style="padding: 22px; border-left: 4px solid #C9A227;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <h4 style="font-size:18px; color:#F6F7FA; font-family:'Space Grotesk';">Vital Signs Vet (Simulación de Gestión)</h4>
              <span style="font-size:12px; color:#C9A227; font-weight:700;">PROTOTIPO JUGABLE 0.1</span>
            </div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Juego de gestión donde la unidad es el caso clínico real. El diagnóstico diferencial se actualiza con cada evidencia recopilada mientras se hace crecer la clínica desde un consultorio modesto hasta un hospital de élite.
            </p>
          </div>

          <div class="glass-card" style="padding: 22px; border-left: 4px solid #C9A227;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <h4 style="font-size:18px; color:#F6F7FA; font-family:'Space Grotesk';">Réquiem: Acta Cero (Juego de Rol Táctico)</h4>
              <span style="font-size:12px; color:#C9A227; font-weight:700;">DISEÑO NARRATIVO</span>
            </div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.5;">
              Motor de juego táctico con grafos de consecuencias persistentes. Cada combate y elección conversacional altera el estado del mundo y redefine las lealtades entre capítulos.
            </p>
          </div>
        </div>
      </main>
      {footer}
    """)

def get_linkedin_slide_7():
    header = make_header("07 / 08")
    footer = make_footer("Cierre y Handoff Ejecutivo →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:22px; flex:1; padding: 10px 0;">
        <div>
          <div class="eyebrow">SECTORES 06 Y 07 · INFRAESTRUCTURA IA & DOCUMENTOS</div>
          <h2 class="headline" style="font-size: 38px;">ChronoSDK & GK Docs Recibos</h2>
          <p class="subheadline" style="margin-bottom: 16px;">Infraestructura de voz para sistemas multiagente y trazabilidad documental inmutable</p>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <div class="glass-card" style="padding: 26px; border-top: 3px solid #C9A227;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
              <span style="font-size:22px;">🎙️</span>
              <h3 style="font-size:20px; color:#F6F7FA; font-family:'Space Grotesk';">ChronoSDK</h3>
            </div>
            <div style="font-size:12px; color:#C9A227; font-weight:700; margin-bottom:12px;">SDK DE VOZ MULTIAGENTE</div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.55; margin-bottom:14px;">
              Diseñado para monitorear enjambres de inteligencia artificial en paralelo sin obligar al desarrollador a leer registros kilométricos. Cada agente habla con una voz asignada y sintetiza resúmenes narrados asíncronos.
            </p>
            <div style="font-size:12px; color:#64748B;">Línea de comandos · Python · Modo sin conexión</div>
          </div>

          <div class="glass-card" style="padding: 26px; border-top: 3px solid #C9A227;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
              <span style="font-size:22px;">📜</span>
              <h3 style="font-size:20px; color:#F6F7FA; font-family:'Space Grotesk';">GK Docs Recibos</h3>
            </div>
            <div style="font-size:12px; color:#C9A227; font-weight:700; margin-bottom:12px;">CONTROL INTERNO CON HASH SHA-256</div>
            <p style="font-size:14px; color:#94A3B8; line-height:1.55; margin-bottom:14px;">
              Motor de comprobantes y recibos internos para organizaciones que requieren cadena de custodia estricta. Cada documento se sella con huella digital verificable públicamente por QR.
            </p>
            <div style="font-size:12px; color:#64748B;">Node.js · PostgreSQL · Herramienta de control interno</div>
          </div>
        </div>

        <div class="glass-card gold-border-card" style="padding: 16px 24px;">
          <p style="font-size:13.5px; color:#94A3B8; line-height:1.5;">
            <strong style="color:#C9A227;">Aclaración de Cumplimiento:</strong> GK Docs Recibos es una herramienta de control administrativo interno; no sustituye comprobantes fiscales digitales (CFDI) ni trámites tributarios oficiales.
          </p>
        </div>
      </main>
      {footer}
    """)

def get_linkedin_slide_8():
    header = make_header("08 / 08")
    footer = make_footer("KADI Technology · Software B2B de Misión Crítica")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:24px; flex:1; padding: 10px 0;">
        <div>
          <div class="eyebrow">VINCULACIÓN ESTRATÉGICA B2B</div>
          <h2 class="headline" style="font-size: 40px;">Ingeniería de Software con Criterio</h2>
          <p class="subheadline" style="margin-bottom: 18px;">¿Cómo colaborar o acceder a las soluciones de KADI Technology?</p>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px;">
          <div class="glass-card" style="padding: 24px; border-top: 3px solid #C9A227;">
            <div style="font-size:13px; font-weight:700; color:#C9A227; margin-bottom:8px;">01. COHORTE FOUNDERS</div>
            <h4 style="font-size:17px; color:#F6F7FA; margin-bottom:8px; font-family:'Space Grotesk';">Acceso Piloto</h4>
            <p style="font-size:13.5px; color:#94A3B8; line-height:1.5;">
              Para clínicas veterinarias, constructoras o administraciones interesadas en evaluar despliegues iniciales con acompañamiento directo.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-top: 3px solid #C9A227;">
            <div style="font-size:13px; font-weight:700; color:#C9A227; margin-bottom:8px;">02. DEMO TÉCNICA</div>
            <h4 style="font-size:17px; color:#F6F7FA; margin-bottom:8px; font-family:'Space Grotesk';">Sesión de Arquitectura</h4>
            <p style="font-size:13.5px; color:#94A3B8; line-height:1.5;">
              Reunión técnica directa con los fundadores para revisar funcionamiento local, stack, cifrado e integraciones a la medida.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-top: 3px solid #C9A227;">
            <div style="font-size:13px; font-weight:700; color:#C9A227; margin-bottom:8px;">03. PROYECTOS PRIVADOS</div>
            <h4 style="font-size:17px; color:#F6F7FA; margin-bottom:8px; font-family:'Space Grotesk';">Desarrollo a la Medida</h4>
            <p style="font-size:13.5px; color:#94A3B8; line-height:1.5;">
              Diseño de sistemas de misión crítica donde la soberanía de datos y la operación sin internet son requerimientos estrictos.
            </p>
          </div>
        </div>

        <div class="glass-card gold-border-card" style="padding: 22px 30px; display:flex; justify-content:space-between; align-items:center; background:rgba(201,162,39,0.06);">
          <div>
            <div style="font-size:12px; font-weight:700; color:#C9A227; letter-spacing:0.12em; text-transform:uppercase;">Canales Oficiales de Contacto</div>
            <div style="font-size:16px; font-weight:600; color:#F6F7FA; margin-top:4px;">
              <NOMBRE_COFUNDADOR_1> & <NOMBRE_COFUNDADOR_2> · Cofundadores
            </div>
            <div style="font-size:14px; color:#94A3B8; margin-top:2px;">
              Correo: <span style="color:#F6F7FA;"><CORREO_CONTACTO></span> · LinkedIn: <span style="color:#F6F7FA;">/in/<PERFIL_LINKEDIN></span>
            </div>
          </div>
          <div style="background:#C9A227; color:#0A1220; font-weight:700; padding:10px 22px; border-radius:10px; font-size:14px; font-family:'Space Grotesk'; text-align:center;">
            kadi.technology
          </div>
        </div>
      </main>
      {footer}
    """)

# ─────────────────────────────────────────────────────────────
# 2. INSTAGRAM SLIDES (6 SLIDES - 1080x1350)
# ─────────────────────────────────────────────────────────────

def get_instagram_slide_1():
    header = make_header("KADI TECH · 01/06")
    footer = make_footer("Desliza para ver la ingeniería →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:26px; flex:1; padding: 20px 0;">
        <div class="eyebrow">INGENIERÍA LOCAL-FIRST</div>
        <h1 class="headline" style="font-size: 50px;">
          Por Qué Construimos Software <br><span class="gold">Local Primero</span>
        </h1>
        <p class="subheadline" style="font-size: 20px; line-height: 1.55;">
          En clínicas, obras y edificios, el software no puede detenerse si el internet se corta. Descubre la arquitectura detrás del ecosistema de KADI Technology.
        </p>

        <div class="glass-card gold-border-card" style="padding: 26px;">
          <h4 style="color:#C9A227; font-size:17px; margin-bottom:8px; font-family:'Space Grotesk';">Nuestra Tesis Tecnológica</h4>
          <p style="font-size:15px; color:#F6F7FA; line-height:1.55;">
            "Tus datos viven en tu máquina. La aplicación corre en tu equipo. Y la decisión final permanece siempre en manos humanas."
          </p>
        </div>
      </main>
      {footer}
    """)

def get_instagram_slide_2():
    header = make_header("KADI TECH · 02/06")
    footer = make_footer("Desliza para conocer la solución →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:26px; flex:1; padding: 20px 0;">
        <div class="eyebrow">EL PROBLEMA DEL SOFTWARE COMÚN</div>
        <h2 class="headline" style="font-size: 40px;">
          La Fragilidad de Depender <br><span class="gold">de la Conexión Remota</span>
        </h2>

        <div style="display:flex; flex-direction:column; gap:18px;">
          <div class="glass-card" style="padding: 24px; border-left:4px solid #EF4444;">
            <h4 style="color:#F6F7FA; font-size:18px; margin-bottom:6px; font-family:'Space Grotesk';">1. La red se cae a mitad de la consulta</h4>
            <p style="font-size:14.5px; color:#94A3B8; line-height:1.5;">
              En una clínica veterinaria o en una obra remota, no hay tiempo para esperar a que regrese la señal para registrar un paciente o cobrar.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-left:4px solid #F59E0B;">
            <h4 style="color:#F6F7FA; font-size:18px; margin-bottom:6px; font-family:'Space Grotesk';">2. Privacidad comprometida</h4>
            <p style="font-size:14.5px; color:#94A3B8; line-height:1.5;">
              Subir historiales médicos o presupuestos de obra a servidores compartidos expone información estratégica de tu negocio a terceros.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-left:4px solid #C9A227;">
            <h4 style="color:#F6F7FA; font-size:18px; margin-bottom:6px; font-family:'Space Grotesk';">3. La respuesta de KADI</h4>
            <p style="font-size:14.5px; color:#94A3B8; line-height:1.5;">
              Instalar la base de datos y la lógica en tu propia computadora o red interna, con aritmética exacta y respaldos locales.
            </p>
          </div>
        </div>
      </main>
      {footer}
    """)

def get_instagram_slide_3():
    header = make_header("KADI TECH · 03/06")
    footer = make_footer("Desliza para ver los 7 sectores →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:26px; flex:1; padding: 20px 0;">
        <div class="eyebrow">ARQUITECTURA DE DATOS</div>
        <h2 class="headline" style="font-size: 40px;">
          Privacidad y Criptografía <br><span class="gold">en Cada Registro</span>
        </h2>

        <div style="display:grid; grid-template-columns:1fr; gap:18px;">
          <div class="glass-card" style="padding: 24px; border-top:3px solid #C9A227;">
            <div style="font-size:18px; font-weight:700; color:#F6F7FA; margin-bottom:6px; font-family:'Space Grotesk';">⚡ Bases de Datos Locales Robustas</div>
            <p style="font-size:14.5px; color:#94A3B8; line-height:1.5;">
              Trabajamos con PostgreSQL y SQLite embebido en Rust/Tauri. Máximo rendimiento de consulta y cero latencia de red.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-top:3px solid #C9A227;">
            <div style="font-size:18px; font-weight:700; color:#F6F7FA; margin-bottom:6px; font-family:'Space Grotesk';">🔐 Huella Criptográfica SHA-256</div>
            <p style="font-size:14.5px; color:#94A3B8; line-height:1.5;">
              Presupuestos, recibos y bitácoras generan una huella digital que garantiza que nadie alteró los números a espaldas del cliente.
            </p>
          </div>

          <div class="glass-card" style="padding: 24px; border-top:3px solid #C9A227;">
            <div style="font-size:18px; font-weight:700; color:#F6F7FA; margin-bottom:6px; font-family:'Space Grotesk';">🤖 IA Local con Gladys</div>
            <p style="font-size:14.5px; color:#94A3B8; line-height:1.5;">
              Modelos optimizados para responder consultas del expediente sin conectar con servidores externos. Tus datos jamás salen de tu clínica.
            </p>
          </div>
        </div>
      </main>
      {footer}
    """)

def get_instagram_slide_4():
    header = make_header("KADI TECH · 04/06")
    footer = make_footer("Desliza para ver el caso piloto →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:22px; flex:1; padding: 10px 0;">
        <div class="eyebrow">PORTAFOLIO DE INGENIERÍA</div>
        <h2 class="headline" style="font-size: 38px;">
          7 Sectores de Misión Crítica <br><span class="gold">Bajo la Misma Filosofía</span>
        </h2>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
          <div class="glass-card" style="padding: 18px;">
            <div style="color:#C9A227; font-size:13px; font-weight:700;">01. SALUD ANIMAL</div>
            <div style="font-size:16px; color:#F6F7FA; font-weight:600; margin-top:2px;">KADI SCV & Gladys</div>
            <div style="font-size:12.5px; color:#94A3B8; margin-top:4px;">Uso piloto cohorte founder.</div>
          </div>

          <div class="glass-card" style="padding: 18px;">
            <div style="color:#C9A227; font-size:13px; font-weight:700;">02. CONSTRUCCIÓN</div>
            <div style="font-size:16px; color:#F6F7FA; font-weight:600; margin-top:2px;">Contract ERP</div>
            <div style="font-size:12.5px; color:#94A3B8; margin-top:4px;">Escritorio Rust + SQLite.</div>
          </div>

          <div class="glass-card" style="padding: 18px;">
            <div style="color:#C9A227; font-size:13px; font-weight:700;">03. CONDOMINIOS</div>
            <div style="font-size:16px; color:#F6F7FA; font-weight:600; margin-top:2px;">TVillage</div>
            <div style="font-size:12.5px; color:#94A3B8; margin-top:4px;">Cierre con evidencia CDMX.</div>
          </div>

          <div class="glass-card" style="padding: 18px;">
            <div style="color:#C9A227; font-size:13px; font-weight:700;">04. EDUCACIÓN</div>
            <div style="font-size:16px; color:#F6F7FA; font-weight:600; margin-top:2px;">Academia</div>
            <div style="font-size:12.5px; color:#94A3B8; margin-top:4px;">WASM interactivo local.</div>
          </div>

          <div class="glass-card" style="padding: 18px;">
            <div style="color:#C9A227; font-size:13px; font-weight:700;">05. SIMULACIÓN & JUEGOS</div>
            <div style="font-size:16px; color:#F6F7FA; font-weight:600; margin-top:2px;">Vital Signs & Réquiem</div>
            <div style="font-size:12.5px; color:#94A3B8; margin-top:4px;">Diagnóstico diferencial.</div>
          </div>

          <div class="glass-card" style="padding: 18px;">
            <div style="color:#C9A227; font-size:13px; font-weight:700;">06. IA & 07. FINANZAS</div>
            <div style="font-size:16px; color:#F6F7FA; font-weight:600; margin-top:2px;">ChronoSDK & GK Docs</div>
            <div style="font-size:12.5px; color:#94A3B8; margin-top:4px;">Voz y trazabilidad interna.</div>
          </div>
        </div>
      </main>
      {footer}
    """)

def get_instagram_slide_5():
    header = make_header("KADI TECH · 05/06")
    footer = make_footer("Desliza para el llamado a la acción →")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:20px; flex:1; padding: 10px 0;">
        <div class="eyebrow">PILOTO EN PRODUCCIÓN REAL</div>
        <h2 class="headline" style="font-size: 38px;">
          KADI SCV: <br><span class="gold">Cohorte Founder #001</span>
        </h2>
        <p class="subheadline" style="margin-bottom: 14px;">
          La versión 1.7 ya opera en una clínica veterinaria activa, gestionando pacientes, agenda, farmacia y finanzas.
        </p>

        <div class="glass-card" style="padding: 16px; display:flex; flex-direction:column; align-items:center;">
          <img src="{img_scv_dash}" style="width:100%; border-radius:12px; border:1px solid rgba(201,162,39,0.3);" alt="KADI SCV Dashboard">
        </div>

        <div class="glass-card gold-border-card" style="padding: 16px 20px;">
          <p style="font-size:14px; color:#F6F7FA; line-height:1.5;">
            <strong style="color:#C9A227;">Próximo Hito (v1.8):</strong> Integración de Gladys, el asistente de IA local para apoyo en consulta sin enviar expedientes a internet.
          </p>
        </div>
      </main>
      {footer}
    """)

def get_instagram_slide_6():
    header = make_header("KADI TECH · 06/06")
    footer = make_footer("kadi.technology · Síguenos en Instagram")
    return wrap_html(f"""
      {header}
      <main style="display:flex; flex-direction:column; justify-content:center; gap:26px; flex:1; padding: 20px 0;">
        <div class="eyebrow">EL FUTURO DEL SOFTWARE B2B</div>
        <h2 class="headline" style="font-size: 42px;">
          La Tecnología Asiste. <br><span class="gold">El Criterio es Tuyo.</span>
        </h2>
        <p class="subheadline" style="font-size: 19px; line-height: 1.55;">
          No creemos en software que toma decisiones a ciegas ni en servicios que secuestran tus datos en la nube. Construimos herramientas para profesionales exigentes.
        </p>

        <div class="glass-card" style="padding: 30px; text-align:center; border: 1px solid rgba(201,162,39,0.4);">
          <div style="font-size:13px; font-weight:700; color:#C9A227; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:8px;">AGENDA TU DEMOSTRACIÓN TÉCNICA</div>
          <div style="font-size:24px; font-weight:700; color:#F6F7FA; font-family:'Space Grotesk'; margin-bottom:12px;">kadi.technology</div>
          <p style="font-size:14px; color:#94A3B8; margin-bottom:20px;">Enlace disponible en la biografía de nuestro perfil.</p>
          <div style="display:inline-block; background:#C9A227; color:#0A1220; font-weight:700; padding:12px 28px; border-radius:10px; font-size:15px; font-family:'Space Grotesk';">
            VER ECOSISTEMA COMPLETO
          </div>
        </div>
      </main>
      {footer}
    """)

# ─────────────────────────────────────────────────────────────
# 3. FACEBOOK PIECES (3 HIGH-RES PIECES)
# ─────────────────────────────────────────────────────────────

def get_facebook_piece_1(width=1200, height=630):
    return wrap_html(f"""
      <div style="display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid rgba(201,162,39,0.25); padding-bottom:16px;">
        <div style="display:flex; align-items:center; gap:14px;">
          {KADI_LOGO_SVG}
          <div>
            <span style="font-family:'Space Grotesk'; font-weight:700; font-size:18px; letter-spacing:0.12em; color:#F6F7FA;">KADI TECHNOLOGY</span>
            <span style="display:block; font-size:10px; font-weight:600; color:#C9A227; letter-spacing:0.15em;">SOLUCIONES PARA SALUD ANIMAL</span>
          </div>
        </div>
        <div style="background:rgba(201,162,39,0.12); border:1px solid rgba(201,162,39,0.4); padding:6px 16px; border-radius:999px; font-size:12px; font-weight:700; color:#C9A227;">
          COHORTE FOUNDER #001
        </div>
      </div>

      <div style="display:grid; grid-template-columns: 1.15fr 0.85fr; gap:28px; align-items:center; flex:1; padding:16px 0;">
        <div>
          <div class="eyebrow" style="margin-bottom:10px;">SOFTWARE CLÍNICO VETERINARIO LOCAL-FIRST</div>
          <h1 style="font-family:'Space Grotesk'; font-size:32px; line-height:1.2; font-weight:700; color:#F6F7FA; margin-bottom:12px;">
            KADI SCV: Gestión Veterinaria <span class="gold">Sin Depender de Internet</span>
          </h1>
          <p style="font-size:14.5px; color:#94A3B8; line-height:1.5; margin-bottom:16px;">
            Expediente clínico, agenda de citas, hospitalización/UCI, vademécum, inventario y caja en una sola plataforma instalada directamente en tu clínica.
          </p>
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Operación sin internet</span>
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Expedientes 100% privados</span>
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Asistente local Gladys</span>
          </div>
        </div>

        <div class="glass-card" style="padding:12px; border:1px solid rgba(201,162,39,0.35);">
          <img src="{img_scv_dash}" style="width:100%; border-radius:10px; display:block;" alt="KADI SCV">
        </div>
      </div>

      <div style="display:flex; align-items:center; justify-content:space-between; border-top:1px solid rgba(201,162,39,0.22); padding-top:14px; font-size:12px;">
        <div style="display:flex; align-items:center; gap:8px; color:#94A3B8;">
          <span class="gold-dot"></span>
          <span>WhatsApp Business: <strong style="color:#F6F7FA;"><TELEFONO_WHATSAPP></strong></span>
          <span style="color:#64748B;">|</span>
          <span><CORREO_CONTACTO></span>
        </div>
        <div style="color:#C9A227; font-weight:700; font-family:'Space Grotesk';">kadi.technology</div>
      </div>
    """, width=width, height=height, padding="36px 44px 28px 44px")

def get_facebook_piece_2(width=1200, height=630):
    return wrap_html(f"""
      <div style="display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid rgba(201,162,39,0.25); padding-bottom:16px;">
        <div style="display:flex; align-items:center; gap:14px;">
          {KADI_LOGO_SVG}
          <div>
            <span style="font-family:'Space Grotesk'; font-weight:700; font-size:18px; letter-spacing:0.12em; color:#F6F7FA;">KADI TECHNOLOGY</span>
            <span style="display:block; font-size:10px; font-weight:600; color:#C9A227; letter-spacing:0.15em;">CONSTRUCCIÓN Y CONTROL DE OBRA</span>
          </div>
        </div>
        <div style="background:rgba(201,162,39,0.12); border:1px solid rgba(201,162,39,0.4); padding:6px 16px; border-radius:999px; font-size:12px; font-weight:700; color:#C9A227;">
          TAURI 2 + RUST (EN DESARROLLO)
        </div>
      </div>

      <div style="display:grid; grid-template-columns: 1.15fr 0.85fr; gap:28px; align-items:center; flex:1; padding:16px 0;">
        <div>
          <div class="eyebrow" style="margin-bottom:10px;">ERP DE ESCRITORIO PARA CONTRATISTAS</div>
          <h1 style="font-family:'Space Grotesk'; font-size:32px; line-height:1.2; font-weight:700; color:#F6F7FA; margin-bottom:12px;">
            Contract ERP: Control de Obra <span class="gold">con Huella Criptográfica</span>
          </h1>
          <p style="font-size:14.5px; color:#94A3B8; line-height:1.5; margin-bottom:16px;">
            Presupuestos por partidas con historial de revisiones inmutables, órdenes de cambio formales y cálculos monetarios en enteros para eliminar errores de redondeo.
          </p>
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Funciona sin internet</span>
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Trazabilidad SHA-256</span>
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Órdenes de cambio auditables</span>
          </div>
        </div>

        <div class="glass-card" style="padding:22px; border:1px solid rgba(201,162,39,0.35); background:rgba(15,27,46,0.9);">
          <div style="font-size:12px; color:#C9A227; font-weight:700; margin-bottom:6px;">ARQUITECTURA DE ESCRITORIO</div>
          <div style="font-size:18px; font-weight:700; color:#F6F7FA; font-family:'Space Grotesk'; margin-bottom:12px;">Rust + SQLite Local</div>
          <p style="font-size:13px; color:#94A3B8; line-height:1.5; margin-bottom:14px;">
            Diseñado para computadoras portátiles en campamentos de obra. Tus licencias y datos quedan validados en tu propio hardware.
          </p>
          <div style="font-size:11px; color:#64748B;">* Herramienta de control interno; no sustituye comprobantes fiscales.</div>
        </div>
      </div>

      <div style="display:flex; align-items:center; justify-content:space-between; border-top:1px solid rgba(201,162,39,0.22); padding-top:14px; font-size:12px;">
        <div style="display:flex; align-items:center; gap:8px; color:#94A3B8;">
          <span class="gold-dot"></span>
          <span>WhatsApp Business: <strong style="color:#F6F7FA;"><TELEFONO_WHATSAPP></strong></span>
          <span style="color:#64748B;">|</span>
          <span><CORREO_CONTACTO></span>
        </div>
        <div style="color:#C9A227; font-weight:700; font-family:'Space Grotesk';">kadi.technology</div>
      </div>
    """, width=width, height=height, padding="36px 44px 28px 44px")

def get_facebook_piece_3(width=1200, height=630):
    return wrap_html(f"""
      <div style="display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid rgba(201,162,39,0.25); padding-bottom:16px;">
        <div style="display:flex; align-items:center; gap:14px;">
          {KADI_LOGO_SVG}
          <div>
            <span style="font-family:'Space Grotesk'; font-weight:700; font-size:18px; letter-spacing:0.12em; color:#F6F7FA;">KADI TECHNOLOGY</span>
            <span style="display:block; font-size:10px; font-weight:600; color:#C9A227; letter-spacing:0.15em;">PROPTECH Y ADMINISTRACIÓN CONDOMINIAL</span>
          </div>
        </div>
        <div style="background:rgba(201,162,39,0.12); border:1px solid rgba(201,162,39,0.4); padding:6px 16px; border-radius:999px; font-size:12px; font-weight:700; color:#C9A227;">
          LEY PROPIEDAD CONDOMINIO CDMX
        </div>
      </div>

      <div style="display:grid; grid-template-columns: 1.15fr 0.85fr; gap:28px; align-items:center; flex:1; padding:16px 0;">
        <div>
          <div class="eyebrow" style="margin-bottom:10px;">ADMINISTRACIÓN CON RESIDUAL JURÍDICO</div>
          <h1 style="font-family:'Space Grotesk'; font-size:32px; line-height:1.2; font-weight:700; color:#F6F7FA; margin-bottom:12px;">
            TVillage: Cierre Mensual Condominial <span class="gold">con Evidencia Real</span>
          </h1>
          <p style="font-size:14.5px; color:#94A3B8; line-height:1.5; margin-bottom:16px;">
            Cierre en 5 pasos, conciliación asistida, visto bueno del Comité de Vigilancia y acuses de recibo en el celular de cada condómino sin obligarlos a registrarse.
          </p>
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Cierre mensual en 5 pasos</span>
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Acuses móviles sin cuenta</span>
            <span style="background:rgba(15,27,46,0.85); border:1px solid rgba(201,162,39,0.3); padding:4px 12px; border-radius:6px; font-size:12px; color:#F6F7FA;">✔ Verificación pública con QR</span>
          </div>
        </div>

        <div class="glass-card" style="padding:22px; border:1px solid rgba(201,162,39,0.35); background:rgba(15,27,46,0.9);">
          <div style="font-size:12px; color:#C9A227; font-weight:700; margin-bottom:6px;">TRANSPARENCIA TOTAL</div>
          <div style="font-size:18px; font-weight:700; color:#F6F7FA; font-family:'Space Grotesk'; margin-bottom:12px;">Bitácora con Cadena de Huellas</div>
          <p style="font-size:13px; color:#94A3B8; line-height:1.5; margin-bottom:14px;">
            Constancias de no adeudo y estados de cuenta sellados digitalmente para evitar conflictos entre comités salientes y entrantes.
          </p>
          <div style="font-size:11px; color:#64748B;">* Versión 0.2 funcional probada con datos de demostración.</div>
        </div>
      </div>

      <div style="display:flex; align-items:center; justify-content:space-between; border-top:1px solid rgba(201,162,39,0.22); padding-top:14px; font-size:12px;">
        <div style="display:flex; align-items:center; gap:8px; color:#94A3B8;">
          <span class="gold-dot"></span>
          <span>WhatsApp Business: <strong style="color:#F6F7FA;"><TELEFONO_WHATSAPP></strong></span>
          <span style="color:#64748B;">|</span>
          <span><CORREO_CONTACTO></span>
        </div>
        <div style="color:#C9A227; font-weight:700; font-family:'Space Grotesk';">kadi.technology</div>
      </div>
    """, width=width, height=height, padding="36px 44px 28px 44px")


def render_all():
    print("Iniciando motor Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_EXEC,
            headless=True
        )

        # 1. LINKEDIN CAROUSEL (8 SLIDES)
        print("--- Renderizando Carrusel LinkedIn (8 láminas 1080x1350) ---")
        linkedin_slides = [
            get_linkedin_slide_1(),
            get_linkedin_slide_2(),
            get_linkedin_slide_3(),
            get_linkedin_slide_4(),
            get_linkedin_slide_5(),
            get_linkedin_slide_6(),
            get_linkedin_slide_7(),
            get_linkedin_slide_8(),
        ]
        
        slide_png_paths = []
        pil_images = []

        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)

        for i, slide_html in enumerate(linkedin_slides, 1):
            out_png = LINKEDIN_DIR / f"slide_{i:02d}_300dpi.png"
            page.set_content(slide_html, wait_until="networkidle")
            page.screenshot(path=str(out_png), type="png")
            slide_png_paths.append(out_png)
            
            # Load into PIL for PDF assembly
            pil_img = Image.open(out_png).convert("RGB")
            pil_images.append(pil_img)
            print(f"  [OK] slide_{i:02d}_300dpi.png ({out_png.stat().st_size // 1024} KB)")

        # Save multipage PDF
        pdf_path = LINKEDIN_DIR / "Carrusel_01_Arquitectura_KADI_11_Sistemas.pdf"
        pil_images[0].save(
            str(pdf_path),
            "PDF",
            save_all=True,
            append_images=pil_images[1:],
            resolution=300.0
        )
        print(f"  [OK] PDF generado: {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")

        # Verify PDF with pypdfium2
        doc = pdfium.PdfDocument(str(pdf_path))
        print(f"  [AUDITORÍA PYPDFIUM2] Páginas verificadas en PDF: {len(doc)}")
        doc.close()

        # 2. INSTAGRAM CAROUSEL (6 SLIDES)
        print("--- Renderizando Carrusel Instagram (6 láminas 1080x1350) ---")
        ig_dir = INSTAGRAM_DIR / "carrusel_01"
        ig_dir.mkdir(parents=True, exist_ok=True)

        ig_slides = [
            get_instagram_slide_1(),
            get_instagram_slide_2(),
            get_instagram_slide_3(),
            get_instagram_slide_4(),
            get_instagram_slide_5(),
            get_instagram_slide_6(),
        ]

        for i, ig_html in enumerate(ig_slides, 1):
            out_ig_sub = ig_dir / f"ig_carousel_01_slide_{i:02d}.png"
            out_ig_root = INSTAGRAM_DIR / f"ig_carousel_01_slide_{i:02d}.png"
            page.set_content(ig_html, wait_until="networkidle")
            page.screenshot(path=str(out_ig_sub), type="png")
            # Also keep in root
            page.screenshot(path=str(out_ig_root), type="png")
            print(f"  [OK] ig_carousel_01_slide_{i:02d}.png guardado en carrusel_01/ y root")

        # 3. FACEBOOK B2B GRAPHICS (3 PIECES)
        print("--- Renderizando Piezas Facebook B2B (1200x630 y 1080x1350) ---")
        fb_page_land = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
        
        fb_pieces = [
            ("fb_01_clinicas_veterinarias_kadi_scv.png", get_facebook_piece_1(1200, 630)),
            ("fb_02_constructoras_contract_erp.png", get_facebook_piece_2(1200, 630)),
            ("fb_03_condominios_tvillage.png", get_facebook_piece_3(1200, 630)),
        ]

        for fname, html_content in fb_pieces:
            out_fb = FACEBOOK_DIR / fname
            fb_page_land.set_content(html_content, wait_until="networkidle")
            fb_page_land.screenshot(path=str(out_fb), type="png")
            print(f"  [OK] {fname} ({out_fb.stat().st_size // 1024} KB)")

        # Also render portrait versions for full 1080x1350 feed coverage
        for fname, getter in [
            ("fb_01_clinicas_veterinarias_kadi_scv_portrait.png", get_facebook_piece_1),
            ("fb_02_constructoras_contract_erp_portrait.png", get_facebook_piece_2),
            ("fb_03_condominios_tvillage_portrait.png", get_facebook_piece_3),
        ]:
            out_fb_port = FACEBOOK_DIR / fname
            page.set_content(getter(1080, 1350), wait_until="networkidle")
            page.screenshot(path=str(out_fb_port), type="png")
            print(f"  [OK] {fname} (Portrait 1080x1350) ({out_fb_port.stat().st_size // 1024} KB)")

        browser.close()
        print("\nTodas las piezas visuales fueron renderizadas exitosamente con Playwright.")

if __name__ == "__main__":
    render_all()
