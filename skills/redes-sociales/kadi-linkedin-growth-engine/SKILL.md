---
name: kadi-linkedin-growth-engine
description: Sistema de crecimiento en LinkedIn para KADI. Define el embudo LinkedIn a sitio a lead a demo, la arquitectura de canales (perfil del fundador, página de empresa, sitio, Canva y CRM), la cola de 12 publicaciones, el contrato UTM hacia el CRM, la matriz de claims públicos (GREEN, YELLOW, RED) y el checklist previo a publicar. Úsala para planear, redactar y auditar contenido de LinkedIn con trazabilidad comercial.
---

# KADI LinkedIn Growth Engine

Playbook operativo para convertir LinkedIn en un sistema repetible de autoridad, tráfico cualificado y conversaciones comerciales. La métrica principal no es alcance ni seguidores; el embudo canónico es:

`LinkedIn -> sitio web -> Lead -> Demo/Reunión -> Oportunidad -> Deal`

Es la capa de estrategia y trazabilidad. Para redactar cada post usa `linkedin-manager`; para linter de claims, plantillas y reels usa `kadi-redes-sociales`.

## Contenido

| Archivo | Para qué sirve |
|---|---|
| `references/KADI-LINKEDIN-GROWTH-ENGINE-R1.md` | Documento rector: objetivo, audiencias, arquitectura de canales, identidad visual, pilares, cadencia, CRM y criterios de lanzamiento. |
| `references/CONTENT-QUEUE-R1.md` | Cola de 12 publicaciones (P01 a P12) con audiencia, objetivo, destino, UTM, visual y copy; cadencia sugerida lunes, miércoles y viernes. |
| `references/UTM-CRM-CONTRACT-R1.md` | Contrato de atribución: parámetros UTM por publicación y modelo CRM (contacto, empresa, oportunidad). |
| `references/PUBLIC-CLAIMS-TRUTH-MATRIX-R1.md` | Política de claims públicos: GREEN (publicable con redacción segura), YELLOW (requiere contexto) y RED (no publicar). |
| `references/P01-PRE-PUBLICATION-CHECKLIST-R1.md` | Checklist previo a publicar una pieza. |
| `references/CANVA-BRAND-SPEC-R1.md` | Especificación de marca para plantillas en Canva. |
| `references/LINKEDIN-PROFILE-PAGE-COPY-R1.md` | Copy del perfil del fundador y de la página de empresa. |
| `references/LINKEDIN-PRODUCT-PAGE-COPY-R1.md` | Copy de la página de producto. |
| `templates/canva-template-briefs-r1.json` | Briefs de plantillas de Canva en formato máquina. |
| `templates/content-manifest-r1.json` | Manifiesto de contenido con destino y UTM por pieza. |

## Reglas

- No inventar cifras, clientes, validaciones, resultados clínicos ni métricas.
- Cada post tiene una audiencia principal y, si es comercial, un UTM.
- Capturas de producto solo con datos sintéticos o autorizados.
- Sin engagement bait; tono sobrio, técnico-comercial y humano.
- No mezclar audiencias (clínicas, partners, inversión) en una misma pieza si debilita el CTA.

## Marcadores a configurar

Los documentos son plantillas de un lanzamiento real. Sustituye por los tuyos: el nombre del fundador (`<NOMBRE_FUNDADOR>` en la especificación de marca), el dominio y las rutas del sitio (`kadi.technology` y sus páginas), los nombres de campaña UTM y las etiquetas de repositorio del documento rector. La skill no usa credenciales; los pasos que involucran un CRM o automatizaciones se describen como proceso y no incluyen identificadores de cuenta.
