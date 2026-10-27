---
name: kadi-instagram-publisher
description: Orquestador de publicaciones, Reels (9:16 1080x1920) y Carruseles (4:5 1080x1350) para Instagram de KADI Technology en Desktop\RedesSociales\Instagram. Garantiza cumplimiento estricto de lint:claims y motor Scene-Locked sin estilo neón.
---

# KADI Instagram Publisher (`kadi-instagram-publisher`)

## Directorio de Trabajo
- Raíz: `%USERPROFILE%\Desktop\RedesSociales\Instagram\`
- Salida de Reels y Activos: `%USERPROFILE%\Desktop\RedesSociales\Instagram\output\`

## Especificaciones Técnicas
1. **Reels (9:16):** `1080x1920`, 30 fps, codec `libx264` (`yuv420p`), audio `aac` 44.1 kHz estéreo, producidos mediante `kadi-scene-locked-video`.
2. **Carruseles Técnicos (4:5):** `1080x1350` PNG/JPG con tipografía institucional (`#0A1220` fondo, `#C9A227` acento dorado, `#F6F7FA` texto).
3. **Compuerta de Veracidad (`check-public-claims.mjs`):**
   - Prohibido afirmar certificaciones externas no otorgadas, métricas de adopción masiva no auditadas o confundir despliegues piloto (`validacion`) con producción general.
   - Antes de publicar cualquier copy, verificar contra `portal/src/_data/projects.json`.
