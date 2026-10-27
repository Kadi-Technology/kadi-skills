# KADI LinkedIn Growth Engine R1

Estado: ACTIVO
Fecha de consolidación: 2026-09-20
Repositorio: KadiWebPage
Rama: feat/linkedin-growth-engine-r1
Sitio de conversión: https://kadi.technology

## 1. Objetivo

Convertir LinkedIn en un sistema repetible de generación de autoridad, tráfico cualificado y conversaciones comerciales para KADI.

La métrica principal no es alcance ni seguidores. El embudo canónico es:

LinkedIn -> Kadi.technology -> Lead -> Demo/Reunión -> Oportunidad -> Deal.

## 2. Audiencias prioritarias

1. Dueños, directores y administradores de clínicas y hospitales veterinarios.
2. Médicos veterinarios con influencia operativa o de compra.
3. Partners tecnológicos/comerciales relevantes.
4. Inversionistas y actores estratégicos, mediante un carril separado del funnel clínico.

No mezclar audiencias en una misma pieza si eso debilita el CTA.

## 3. Arquitectura de canales

### Perfil del fundador
Función: voz humana, build-in-public, problemas reales, aprendizajes, criterio de producto y conversaciones uno-a-uno.

### Página KADI
Función: producto, evidencia, casos de uso, lanzamientos, materiales institucionales y CTA de demo.

### Kadi.technology
Función: superficie de conversión.
Destinos principales:
- Clínicas: /clinicas/
- Producto: /producto/
- Demo: /demo/
- Profesionales: /profesionales/
- Inversión: /inversion/
- Contacto: /contacto/

### Canva
Función: sistema visual, plantillas, producción y cola creativa.
Carpeta raíz: KADI LinkedIn Growth.

### HubSpot
Función: CRM y trazabilidad.
Modelo inicial:
- CONTACT = persona.
- COMPANY = clínica/organización.
- DEAL = oportunidad real.
- Organic Social = fuente nativa cuando aplique.

## 4. Identidad visual canónica

Fuente: src/assets/styles.css del sitio público.

Paleta:
- Navy 950: #0a1220
- Navy 900: #0e1a2e
- Navy 800: #14253f
- Navy 700: #1d3559
- Gold 600: #a9821c
- Gold 500: #c9a227
- Gold 300: #e2c766
- Paper: #f6f7fa
- White: #ffffff
- Ink 900: #10161f
- Ink 700: #333d4d

Tipografía:
- Display: Outfit
- Body: Public Sans

Principio visual:
Producto primero. Capturas reales > ilustraciones genéricas.
Navy/paper como base; gold como acento, no como superficie dominante.

## 5. Posicionamiento editorial

Idea central:
"KADI conecta la operación clínica veterinaria alrededor del mismo expediente."

Narrativas primarias:
- La información fragmentada cuesta tiempo, dinero y continuidad clínica.
- KADI conecta recepción, consulta, hospitalización, caja e inventario.
- El producto debe demostrarse con evidencia, no con adjetivos.
- La construcción de KADI puede narrarse con transparencia: qué existe, qué se valida y qué falta.
- La tecnología es soporte de la operación; no es el protagonista del mensaje comercial.

## 6. Mezcla editorial R1

Objetivo mensual:
- 35% Problema operativo veterinario.
- 25% Producto/evidencia.
- 20% Founder/build-in-public.
- 10% Educación/criterio.
- 10% Mercado/partners/inversión.

Cadencia inicial:
- Lunes: problema/insight.
- Miércoles: producto/evidencia.
- Viernes: founder/aprendizaje/mercado.

No publicar por cumplir frecuencia. Si no hay evidencia o idea útil, se sustituye por investigación.

## 7. Formatos

Prioridad:
1. Texto + captura de producto.
2. Documento/carrusel de 5-8 páginas.
3. Video corto de producto o walkthrough.
4. Post founder sin pieza gráfica cuando la historia lo soporte.
5. Comparativas y checklists basados en problemas operativos verificables.

Evitar:
- Stock photos genéricas.
- Claims clínicos no demostrados.
- Métricas inventadas.
- "Revolucionario", "líder", "el mejor" sin evidencia.
- Engagement bait.
- Automatización no autorizada de conexiones, DMs, likes o comentarios.

## 8. Funnel por audiencia

### Clínica
Post -> /clinicas/ o /demo/ -> contacto -> demo -> Deal.

### Producto
Post de evidencia -> /producto/ -> /demo/ -> demo -> Deal.

### Profesional
Post educativo -> /profesionales/ -> contacto/lista -> relación.

### Inversión/partner
Post founder/mercado -> /inversion/ -> formulario/reunión -> calificación -> proceso separado.

## 9. CTA library

Clínica:
- Agenda una demo de 30 minutos.
- Mira cómo se mueve un paciente dentro de KADI.
- Si tu clínica tiene recepción, consulta, hospitalización y caja, revisemos si KADI encaja.

Producto:
- Ver KADI por dentro.
- Ver módulos y evidencia del producto.

Founder:
- ¿Cómo resuelven esto hoy en tu clínica?
- Si operas una clínica veterinaria y este problema te resulta familiar, me interesa comparar procesos.

No usar el mismo CTA en todos los posts.

## 10. Reglas de atribución

Todos los enlaces desde LinkedIn deben llevar:
- utm_source=linkedin
- utm_medium=organic
- utm_campaign=<campaña>
- utm_content=<pieza>

Campaña base R1:
kadi_linkedin_launch_r1

Ejemplo:
https://kadi.technology/clinicas/?utm_source=linkedin&utm_medium=organic&utm_campaign=kadi_linkedin_launch_r1&utm_content=p01_islas_operativas

## 11. Definición de lead

No considerar lead a:
- Like.
- Follow.
- Impresión.
- Visita anónima.
- Comentario sin intención comercial.

Lead:
Persona identificable que inicia una conversación relevante, completa un formulario, solicita demo, pide información comercial o demuestra intención clara.

MQL:
Lead que encaja con ICP y expresa un problema/uso relevante.

SQL:
MQL con conversación activa y posibilidad real de demo/compra.

Opportunity:
Existe una oportunidad comercial concreta y debe abrirse Deal.

## 12. HubSpot R1

Usar propiedades estándar antes de crear personalizaciones.

CONTACT:
- lifecyclestage
- hs_lead_status
- hs_analytics_source
- hs_latest_source

COMPANY:
- domain
- industry
- numberofemployees / hs_employee_range
- hs_analytics_source

DEAL:
- pipeline
- dealstage
- dealtype
- amount sólo cuando exista una cifra comercial real
- hs_analytics_source

No crear Deal por cada contacto. Deal sólo cuando exista oportunidad.

## 13. Canva R1

Estructura ya creada:
- 01 Brand & Templates
- 02 Content Queue
- 03 Published
- 04 Product Proof
- 05 Founder & Build-in-Public
- 06 Clinics & Buyers
- 07 Investors & Partners

Plantillas mínimas a producir:
1. Product proof 1200x1200.
2. Insight 1200x1200.
3. Founder quote/lesson 1200x1200.
4. Carousel/documento 1080x1350.
5. Video cover 1080x1350.
6. Banner de LinkedIn para fundador.
7. Banner de Company Page.

## 14. Operación semanal

Domingo:
- Revisar métricas y pipeline.
- Elegir 3 temas.

Lunes:
- Publicar problema/insight.

Martes:
- Responder comentarios cualificados.
- Investigar perfiles/organizaciones relevantes manualmente.

Miércoles:
- Publicar evidencia de producto.

Jueves:
- Follow-up a conversaciones reales.
- Mover contactos en HubSpot si corresponde.

Viernes:
- Publicar founder/aprendizaje.
- Documentar feedback recibido.

## 15. KPIs R1

North-star:
- Demos/reuniones cualificadas originadas o influidas por LinkedIn.

Secundarios:
- Visitas con UTM desde LinkedIn.
- Leads identificados.
- Conversaciones cualificadas.
- MQL.
- SQL.
- Deals creados.
- Tasa visita -> lead.
- Tasa lead -> demo.
- Tasa demo -> opportunity.

Diagnóstico:
- Impresiones.
- Engagement.
- Follows.
- CTR.

## 16. Automatización

Permitido:
- Investigación.
- Drafts.
- Diseño.
- Programación mediante herramientas oficiales/autorizadas.
- UTM.
- CRM.
- Reporting.

Requiere supervisión humana:
- Publicación final mientras no exista conector autorizado.
- Conexiones.
- Mensajes directos.
- Comentarios en nombre del fundador.
- Cambios sensibles de perfil.
- Claims comerciales, clínicos, legales o de inversión.

## 17. Fase de lanzamiento de 30 días

Semana 1:
- Completar perfil founder y Company Page.
- Crear 4 plantillas Canva.
- Publicar 3 posts.
- Validar enlaces UTM.
- Definir baseline.

Semana 2:
- 3 posts.
- Primer carousel.
- Primer post con evidencia directa de producto.
- Empezar clasificación de leads.

Semana 3:
- 3 posts.
- Primer video corto.
- Analizar temas con mejor CTR/conversaciones.
- Duplicar lo que funciona.

Semana 4:
- 3 posts.
- Recap de aprendizaje.
- Revisión funnel completo.
- Decidir si vale la pena añadir Ads, API o herramientas de prospección.

## 18. Gate para pago/ads/API

No pagar herramientas adicionales ni construir integración LinkedIn API hasta que:
- exista ritmo editorial real;
- existan al menos 12 publicaciones;
- tengamos UTMs funcionando;
- HubSpot reciba leads reales;
- sepamos qué mensaje genera conversaciones;
- podamos medir al menos una conversión útil.

## 19. Regla de verdad

Distinguir siempre:
- VERIFICADO: existe evidencia directa.
- INFERIDO: conclusión razonable.
- PROPUESTO: decisión estratégica.
- PENDIENTE: no verificable todavía.

Nunca convertir mensajes del PO, recuerdos del modelo o copy anterior en hechos sin comprobar cuando la evidencia pueda verificarse.

## 20. Resultado esperado de R1

Al terminar R1 KADI debe tener:
- identidad editorial coherente;
- cola de contenido;
- 12 publicaciones;
- 1 carousel;
- 1 video;
- página/perfil preparados;
- enlaces UTM consistentes;
- HubSpot listo para leads;
- reporting semanal;
- criterio de qué escalar en R2.
