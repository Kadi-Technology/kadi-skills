---
name: kadi-linkedin-publisher
description: Orquestador de artículos técnicos, carruseles PDF y publicaciones corporativas B2B para LinkedIn de KADI Technology en Desktop\RedesSociales\LinkedIn, sincronizado con los contratos check-linkedin-growth.mjs y check-p01-launch.mjs.
---

# KADI LinkedIn Publisher (`kadi-linkedin-publisher`)

## Directorio de Trabajo
- Raíz: `%USERPROFILE%\Desktop\RedesSociales\LinkedIn\`
- Contratos y Manifiestos Web: `%USERPROFILE%\Desktop\KadiWebPage\scripts\check-linkedin-growth.mjs` y `scripts\check-p01-launch.mjs`

## Reglas de Gobernanza Editorial B2B
1. **Atribución Local Determinista:** Todo enlace compartido hacia `https://kadi.technology` debe incluir parámetros UTM canónicos (`utm_source=linkedin&utm_medium=organic_social&utm_campaign=...`) validados por `npm run lint:growth`.
2. **Estado P01 y Evidencia Técnica:** Ninguna publicación se marca como `"published"` o `"approved"` en el manifiesto sin que su paquete de evidencia asociado esté verificado y autorizado por el Product Owner.
3. **Tono Ejecutivo Multi-Sector:** Destacar la ingeniería de software a la medida de KADI Technology en sus 7 verticales (Salud y Veterinaria, Construcción y Obra, Hospitalidad, Educación, Gaming Lab, Herramientas IA/Voz y Finanzas/Documentos).
