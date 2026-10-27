---
name: kadi-tiktok-youtube-shorts
description: Productor y empaquetador de videos verticales técnicos (TikTok y YouTube Shorts 9:16 1080x1920) en Desktop\RedesSociales\TikTok y Desktop\RedesSociales\YouTube usando el motor Scene-Locked de KADI.
---

# KADI TikTok & YouTube Shorts Producer (`kadi-tiktok-youtube-shorts`)

## Directorios de Trabajo
- TikTok: `%USERPROFILE%\Desktop\RedesSociales\TikTok\`
- YouTube Shorts: `%USERPROFILE%\Desktop\RedesSociales\YouTube\`

## Reglas de Producción Vertical
1. **Motor Obligatorio:** Utilizar exclusivamente `kadi-scene-locked-video` (`scene_locked_engine.py`) con locución `es-CO-SalomeNeural` y duración bloqueada por escena ($T_i = d_i + 0.35\text{ s}$).
2. **Zonas Seguras (Safe Zones 9:16):**
   - Mantener titulares y tarjetas de código entre $Y = 160\text{ px}$ y $Y = 1540\text{ px}$ para evitar superposición con la interfaz de usuario de TikTok y YouTube Shorts.
3. **Evidencia Real:** Mostrar únicamente capturas, diagramas de arquitectura y flujos reales de los 11 productos del portafolio KADI.
