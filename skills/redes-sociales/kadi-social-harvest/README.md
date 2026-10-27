# KADI Social Asset Harvester

Cosecha de capturas UI reales (Playwright headless) y páginas de PDF (pypdfium2 a escala 2.5) de los proyectos del portafolio, con regla de no reutilizar capturas entre sectores.

## Requisitos y notas

- El mapa de orígenes apunta a carpetas locales del autor (`%USERPROFILE%\Desktop\...`); reemplázalo por las tuyas.
- Requiere Playwright (Python) y pypdfium2.

## Marcadores y variables a configurar

| Marcador | Qué poner |
|---|---|
| `<RUTA_CHROMIUM_PLAYWRIGHT>` | Ruta al `chrome.exe` de Chromium de Playwright en tu equipo. |
| `<URL_PRODUCCION_CLIENTE>` | URL de producción real de un cliente, que en el original era zona prohibida para cosechar; ponla solo si tienes permiso expreso. |
| `<URL_ACADEMIA_PUBLICA>` | URL del entorno público de Academia en el original. |

## Credenciales

No requiere credenciales. Cosecha solo capturas con datos sintéticos o autorizados.
