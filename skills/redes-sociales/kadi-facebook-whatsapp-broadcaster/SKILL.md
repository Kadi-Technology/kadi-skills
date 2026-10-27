---
name: kadi-facebook-whatsapp-broadcaster
description: Orquestador de comunicados ejecutivos, cápsulas informativas y resúmenes para Facebook, WhatsApp y X en Desktop\RedesSociales, respetando el contrato de privacidad y el estado whatsapp.enabled=false del portal público.
---

# KADI Facebook, WhatsApp & X Broadcaster (`kadi-facebook-whatsapp-broadcaster`)

## Directorios de Trabajo
- Facebook: `%USERPROFILE%\Desktop\RedesSociales\Facebook\`
- WhatsApp: `%USERPROFILE%\Desktop\RedesSociales\WhatsApp\`
- X (Twitter): `%USERPROFILE%\Desktop\RedesSociales\X\`

## Reglas de Cumplimiento y Privacidad
1. **Coherencia con `site.json` (`whatsapp.enabled: false`):**
   - Mientras el canal público de WhatsApp permanezca deshabilitado en `portal/src/_data/site.json`, el llamado a la acción (CTA) oficial en todas las redes es el correo directo `<CORREO_VENTAS>` y el portal `https://kadi.technology/contacto/`.
2. **Hilos Técnicos en X y Posteos en Facebook:**
   - Respetar el gate `check-public-claims.mjs`: presentar a `kadi-scv` y la Membresía Founder #001 (Clínica Fundadora) como cohorte fundadora y despliegue piloto real, y describir con exactitud la etapa de cada uno de los 11 proyectos del portafolio.
