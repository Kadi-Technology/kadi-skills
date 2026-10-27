# APPROVAL_GATE · LOTE-01

Firma requerida para pasar de BORRADOR a cola de publicación: `APROBADO-SOCIAL-LOTE-01`.

Hasta que el Product Owner la escriba en el chat, el estado de las 20 piezas es BORRADOR y no se programa ni se publica nada. Buffer no está conectado y este agente no tiene tokens ni APIs de redes.

## Qué se aprueba

- 20 piezas listadas en `PARRILLA_LOTE_01.md` y en `draft_queue.json`.
- Los activos de `assets/` (carrusel de Instagram, PDF de LinkedIn, reel 9:16 y video 16:9, derivados).
- Las piezas con activo pendiente (LOTE01-P17, LOTE01-P18) no entran en la aprobación hasta que la fase 2 entregue las capturas de la demo.

## Decisiones que necesito del PO antes de firmar

1. Teléfono y marca de la clínica. Las capturas completas del portal de la clínica muestran el teléfono comercial y la dirección. Los activos nuevos de este lote están recortados sin la barra de navegación, pero la insignia Socio Fundador #001 y el nombre de la clínica sí aparecen. Confirma con la clínica el uso de su nombre y marca.
2. Especies y versiones de KADI Anatomy 3D. La Demo Pública Básica del portal ofrece cuatro especies (canino, felino, conejo y ave) y 14 sistemas anatómicos, verificado en el archivo público anatomia3d.js el 21 de octubre de 2026. Dentro de KADI SCV (v1.8.0-rc.4, en validación para despliegue), la Suite Clínica Pro vincula el atlas clínico con el expediente y la nota SOAP (cubriendo perro y gato). Se distingue con precisión la Demo Pública Básica (apoyo visual al tutor) de la Suite Clínica Pro (en validación para despliegue).
3. Lenguaje de la cohorte. El portal de KADI muestra privilegios de la cohorte con lenguaje contractual (tarifa y acceso de largo plazo). Ninguna pieza lo usa. Si quieres hablar de ellos en redes, define el texto aprobado.
4. TVillage. Las capturas salen de una presentación estática marcada como borrador interno con datos sintéticos. Confirma que se puede mostrar en público.
5. Academia y Réquiem. Las capturas salen de builds y prototipos locales. Academia no se enlaza a su host público porque ese host está en cuarentena.
6. Voz. Salomé (es-CO) se generó con edge-tts, que usa un servicio de síntesis en línea de Microsoft. Si prefieres una voz local, hay que regenerar los dos videos.
7. Enlaces de WhatsApp y agenda en las piezas de la cohorte, tal como indica el canon.

## Verificaciones hechas

- `node scripts/check_social_copy.mjs Campanas/LOTE-01`: 0 hallazgos (ver LINT_REPORT.txt).
- Contraste WCAG AA verificado de forma programática en carrusel, PDF, derivados y subtítulos de los videos.
- sha256 de cada activo referenciado igual al del índice semántico.
- ffprobe de cada mp4 nuevo en `assets/assets_manifest.json`.

## Qué no está verificado

- Que los horarios rindan más: son hipótesis.
- Cómo se ven las piezas dentro de cada app (recorte de pantalla, zonas seguras reales).
- Las capturas del visor 3D se tomaron en un navegador sin GPU; los fotogramas por segundo que muestran no son representativos.
