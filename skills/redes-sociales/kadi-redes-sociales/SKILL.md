---
name: kadi-redes-sociales
description: Community manager y lead audiovisual de KADI para Instagram, LinkedIn, Facebook, TikTok y YouTube. Redacta copys por plataforma, arma la parrilla semanal, construye enlaces UTM, valida claims con un linter (lint:claims) y genera carruseles, PDFs y reels listos para publicar. Solo produce borradores; nada se publica sin aprobación del PO.
---

# KADI Redes Sociales (Community Manager y Audiovisual Lead)

Skill de operación de redes de KADI Technology. Genera contenido **Scene-Locked** (cada pieza se apoya en capturas reales y claims verificables): reels, carruseles, PDFs para LinkedIn y comunicados B2B. Es el paquete multi-plataforma; para el estilo y la estrategia específicos de LinkedIn usa también `linkedin-manager`, y para video usa `kadi-video-social`.

## Regla de oro

Todo lo que produce esta skill es **BORRADOR**. No tiene tokens ni APIs de redes y no publica. El paso de borrador a cola de publicación exige la firma explícita del Product Owner (ver `plantillas/APPROVAL_GATE.md`).

## Contenido de la skill

| Ruta | Qué es |
|---|---|
| `scripts/check_social_copy.mjs` | Linter de claims y seguridad editorial: reglas de claims, certificaciones no auditadas, hosts e IPs en cuarentena, clientes prohibidos, correos personales, UTM obligatorios, enlaces fuera del canon, hashtags de más. Pruebas en `check_social_copy.test.mjs` (`node --test`). |
| `scripts/kadi_social_core.py` | Núcleo: construcción de enlaces UTM con el esquema oficial, lectura de activos publicables desde un índice semántico, calendario del lote y exportación de la cola de borradores. |
| `scripts/kadi_social_mcp.py` | Servidor MCP local (stdio) con las herramientas `list_assets`, `get_calendar`, `build_utm_link`, `lint_copy` y `export_draft_queue`. Solo lectura y borrador. |
| `scripts/verified_claims.json` | Formato de afirmaciones técnicas verificadas en código que el linter acepta como evidencia. Reemplázalo por las tuyas. |
| `claims-base/` | Reglas de claims bloqueados (`blocked_rules`) que carga el linter. |
| `build/common.py`, `build_carousel.py`, `build_video.py` | Pipeline de piezas: lienzo con Pillow, verificación de contraste WCAG AA, carrusel de Instagram 4:5, reel 9:16 y gemelo 16:9 con subtítulos. |
| `build/linkedin_generate_assets.py` | Genera con Playwright el carrusel de LinkedIn (PDF multipágina y PNG a 300 DPI), el de Instagram y las gráficas de Facebook. |
| `plantillas/copy_{instagram,linkedin,facebook,tiktok,youtube}_01.md` | Copys de ejemplo por plataforma (hooks, descripción, hashtags, pieza gráfica asociada). |
| `plantillas/PARRILLA_LOTE_01.md` | Calendario semanal de 20 piezas con mezcla de contenido 40/35/25 y horarios CDMX. |
| `plantillas/APPROVAL_GATE.md` | Puerta de aprobación: qué se aprueba, decisiones pendientes del PO y qué no está verificado. |

## Flujo de trabajo

1. **Brief y pilares.** Define pilares (por ejemplo Demostrar 40 %, Prueba y criterio 35 %, Comunidad y conversión 25 %), audiencia por pieza y un solo CTA por pieza.
2. **Copy por plataforma.** Parte de `plantillas/copy_*_01.md`: hook en las dos primeras líneas, cuerpo corto, CTA, alt text y hashtags acotados.
3. **Enlaces UTM.** `build_utm_link(url, channel, campaign)`; canales: `instagram`, `linkedin`, `facebook`, `youtube_short`, `youtube_horizontal`, `tiktok`. La campaña va en `snake_case` y solo se permiten hosts propios.
4. **Lint obligatorio.** `node scripts/check_social_copy.mjs <carpeta-de-piezas>`; con 0 hallazgos se continúa. Un claim técnico sin evidencia en `verified_claims.json` o en el índice semántico se marca como hallazgo.
5. **Activos.** Corre `build/` para carruseles, PDFs y reels; usa solo capturas con datos sintéticos o autorizados y recorta datos de contacto reales.
6. **Parrilla y aprobación.** Completa la parrilla con horarios, exporta `draft_queue.json` y entrega al PO con `APPROVAL_GATE.md`.

## Servidor MCP (opcional)

```bash
claude mcp add kadi-social -- python scripts/kadi_social_mcp.py
```

Usa FastMCP si el paquete `mcp` está instalado; si no, implementa un JSON-RPC 2.0 mínimo. Para forzar la implementación mínima: `KADI_SOCIAL_MCP_FORCE_MINIMAL=1`.

## Estructura de workspace esperada

Los scripts asumen que `scripts/` cuelga de una raíz de trabajo con estas carpetas (créalas o ajusta las constantes `ROOT`, `INDEX_PATH` y `CAMPAIGNS_DIR` en `kadi_social_core.py` y `build/common.py`):

```
<raiz>/scripts/              # esta carpeta scripts/
<raiz>/Campanas/LOTE-NN/     # piezas: <fecha>_<canal>_<slug>/{copy.md, alt_text.txt, meta.json}
<raiz>/WebPage/assets_por_proyecto/semantic_visual_index.json   # índice de capturas publicables
```

Pruebas: `node --test scripts/check_social_copy.test.mjs` (71 pruebas del linter, no requieren nada más). `python scripts/test_kadi_social_mcp.py` es una prueba de humo del servidor MCP; su paso `list_assets` necesita el índice semántico de arriba, por lo que falla hasta que lo proporciones.

## Credenciales y valores que debes configurar

Esta skill **no necesita tokens, API keys ni cookies**: no llama a ninguna API de redes. Los valores de contacto del repo original se reemplazaron por marcadores; sustitúyelos por los tuyos antes de publicar:

| Marcador | Qué poner |
|---|---|
| `<CORREO_CONTACTO>` | Correo de contacto público de tu marca. |
| `<TELEFONO_WHATSAPP>` / `<WHATSAPP_E164>` | Teléfono de WhatsApp Business (formato legible y formato E.164 para `wa.me`). En el linter y sus pruebas se usa el número ficticio `5210000000000`. |
| `<ID_AGENDA>` / `ID_AGENDA_EJEMPLO` | ID de tu enlace de agenda (`calendar.app.google/...`). |
| `<NOMBRE_COFUNDADOR_1>`, `<NOMBRE_COFUNDADOR_2>`, `<PERFIL_LINKEDIN>` | Firma y perfil públicos del equipo. |
| `KADI_CHROME_EXEC` (variable de entorno) | Ruta al Chromium de Playwright para `build/linkedin_generate_assets.py`. |
| `KADI_WEBPAGE_DIR` (variable de entorno, opcional) | Carpeta del sitio con `docs/linkedin/public-claims-r1.json`; por defecto el linter usa `claims-base/`. |

Los hosts `portal-cliente`, `prod-cliente`, `academia-privada`, `demo-privada` y `demo-retirada` bajo `kadi.technology` son nombres ficticios que demuestran las reglas de cuarentena; reemplázalos por los hosts de producción de tu propio entorno. Igual con las IPs de documentación `203.0.113.50` y `203.0.113.51`.

## Seguridad editorial

- Nunca publiques datos de clientes ni pacientes reales, aunque estén anonimizados; usa mascotas y casos ficticios.
- Nada de cifras, certificaciones o resultados sin evidencia vigente; lo que no puedas verificar se presenta como trabajo en curso o no se publica.
- No mezcles audiencias en una misma pieza si debilita el CTA.
- Material educativo no sustituye el criterio del médico veterinario.
