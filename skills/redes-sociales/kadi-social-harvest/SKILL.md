---
name: kadi-social-harvest
description: Cosechador automatizado de activos visuales reales (capturas UI con Playwright Headless y renderizado de PDFs con pypdfium2) de los 11 productos del portafolio KADI. Úsalo para extraer evidencia gráfica 100% real antes de publicar en la web o redes sociales.
---

# KADI Social Asset Harvester (`kadi-social-harvest`)

## Reglas de Integridad Visual
1. **Cero Imágenes Prestadas Entre Sectores:** Ningún proyecto no veterinario (`Contract`, `TVillage`, `Academia`, `Requiem`, `ChronoSDK`, `GK Docs`) puede usar capturas clínicas veterinarias.
2. **Binario Chromium Headless en este Host:**
   Al usar Playwright desde Python 3.13, especifica siempre la ruta verificada del ejecutable local:
   ```python
   EXECUTABLE_PATH = r"<RUTA_CHROMIUM_PLAYWRIGHT>"
   ```
3. **Renderizado de PDFs Reales (`pypdfium2`):**
   Para cosechar páginas de contratos o recibos PDF (`Desktop\Generador de recibos\recibo_final.pdf`, `Desktop\Trabajos\propuesta_final.pdf`), utiliza `pypdfium2` a escala `2.5` para obtener PNGs nítidos.

## Mapa de Orígenes Reales por Proyecto
- **KADI SCV / Gladys / Anatomía 3D / Biblioteca por Raza:** `%USERPROFILE%\Desktop\Core\core\frontend` + `<URL_PRODUCCION_CLIENTE>`
- **Contract ERP:** `%USERPROFILE%\Desktop\Contract\artifacts\verification\` (`1_dashboard.png` .. `7_projects.png`)
- **GK Docs & Recibos:** `%USERPROFILE%\Desktop\Generador de recibos\recibo_final.pdf` y `%USERPROFILE%\Desktop\Trabajos\propuesta_final.pdf`
- **TVillage:** `%USERPROFILE%\Desktop\TVillage\frontend` y `C:\x\packages\web`
- **Academia:** `%USERPROFILE%\Desktop\academia` y `<URL_ACADEMIA_PUBLICA>`
- **Vital Signs Vet:** `%USERPROFILE%\Desktop\KadiVet\dist\index.html` (más `docs\screenshots\` y `gallery.html`)
- **Réquiem: Acta Cero:** `%USERPROFILE%\Desktop\Requiem\prototype\index.html` (más `output\opus-review\capturas\` y `output\playwright\`)
- **ChronoSDK:** `%USERPROFILE%\Desktop\ChronoSDK_Distribucion\ChronoSDK`
