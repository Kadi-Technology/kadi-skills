# KADI LinkedIn UTM + CRM Contract R1

Estado: CANÓNICO PARA R1
Fecha: 2026-09-20

## 1. Objetivo

Asegurar que cualquier tráfico y conversación comercial originada en LinkedIn pueda rastrearse desde la publicación hasta HubSpot sin depender de memoria manual.

## 2. Parámetros obligatorios

Todos los enlaces publicados desde LinkedIn deben incluir:

- utm_source=linkedin
- utm_medium=organic
- utm_campaign=kadi_linkedin_launch_r1
- utm_content=<identificador_unico>

Formato recomendado de utm_content:
pNN_tema_corto

Ejemplos:
- p01_islas_operativas
- p02_uso_cobro_inventario
- p05_senales_fragmentacion

## 3. Destinos por intención

Clínica:
https://kadi.technology/clinicas/

Producto:
https://kadi.technology/producto/

Demo:
https://kadi.technology/demo/

Hospitalización:
https://kadi.technology/hospitalizacion-veterinaria/

Inventario:
https://kadi.technology/inventario-veterinario/

Profesionales:
https://kadi.technology/profesionales/

Inversión:
https://kadi.technology/inversion/

Sobre KADI:
https://kadi.technology/sobre/

## 4. Convención de campaña

R1 orgánico:
kadi_linkedin_launch_r1

No reutilizar esta campaña para:
- paid social;
- email;
- WhatsApp;
- eventos;
- tráfico personal sin relación con LinkedIn.

Si se activa LinkedIn Ads:
utm_source=linkedin
utm_medium=paid_social
utm_campaign=<campaña_paid>

## 5. Modelo HubSpot

### CONTACT

Crear/actualizar sólo cuando exista una persona identificable.

Propiedades estándar disponibles verificadas:
- lifecyclestage
- hs_lead_status
- hs_analytics_source
- hs_latest_source

Valores útiles de hs_analytics_source / hs_latest_source:
- SOCIAL_MEDIA = Organic Social
- PAID_SOCIAL = Paid Social

Lifecycle recomendado:
- lead: persona con intención identificable.
- marketingqualifiedlead: encaja con ICP y muestra interés relevante.
- salesqualifiedlead: existe conversación comercial concreta.
- opportunity: ya existe una oportunidad asociada.
- customer: sólo cuando exista relación comercial confirmada.

Lead status recomendado:
- NEW
- OPEN
- IN_PROGRESS
- ATTEMPTED_TO_CONTACT
- CONNECTED
- OPEN_DEAL
- UNQUALIFIED
- BAD_TIMING

### COMPANY

Crear cuando exista una clínica u organización identificable y relevante.

Propiedades estándar:
- name
- domain
- industry
- numberofemployees / hs_employee_range
- hs_analytics_source

No inventar tamaño de clínica si no está verificado.

### DEAL

Crear sólo cuando exista oportunidad comercial real.

Pipeline actual verificado:
Sales Pipeline

Stages actuales verificados:
- Appointment Scheduled
- Qualified To Buy
- Presentation Scheduled
- Decision Maker Bought-In
- Contract Sent
- Closed Won
- Closed Lost

Regla:
Una conversación de LinkedIn no es automáticamente un Deal.

## 6. Definición operativa

Follower:
No CRM salvo que exista razón comercial.

Engaged user:
No CRM automáticamente.

Lead:
Persona identificable que pide demo, información, reunión, partnership o inicia conversación comercial relevante.

MQL:
Encaja con audiencia objetivo y existe necesidad/intención.

SQL:
Existe posibilidad real de demo/compra/partnership.

Opportunity:
Debe abrirse Deal.

## 7. Registro manual mínimo cuando LinkedIn no esté integrado

Para cada lead real registrar:
- nombre;
- apellido;
- correo si fue proporcionado legítimamente;
- empresa/clínica;
- cargo;
- fuente = Organic Social cuando aplique;
- lifecycle stage;
- lead status;
- nota con origen: LinkedIn;
- URL del perfil sólo en nota si es necesaria para seguimiento y fue obtenida de forma legítima;
- post/utm_content que originó la conversación si se conoce.

No usar scraping ni enriquecer datos personales con fuentes dudosas.

## 8. Convención de Deal

Nombre:
<KADI> - <Clínica/Organización> - <Tipo>

Ejemplos:
KADI - Clínica ABC - Demo
KADI - Partner XYZ - Partnership

Deal Type:
newbusiness para nuevas oportunidades.

Amount:
Dejar vacío hasta que exista oferta comercial real.
No usar una estimación ficticia para inflar pipeline.

## 9. Revisión semanal

Cada domingo medir:
- leads LinkedIn nuevos;
- MQL;
- SQL;
- demos;
- deals;
- closed won/lost;
- posts que originaron conversaciones;
- destino con mejor conversión.

## 10. Regla de atribución

Si no puede probarse que LinkedIn originó el lead:
No marcar LinkedIn como fuente sólo porque el contacto tenga perfil en LinkedIn.

Si LinkedIn originó el primer contacto pero posteriormente llegó por otro canal:
Conservar la evidencia del origen y usar las propiedades automáticas de HubSpot cuando estén disponibles.

## 11. Futuras propiedades custom, sólo si R1 lo justifica

No crear todavía salvo necesidad demostrada:
- kadi_lead_type
- kadi_clinic_size
- kadi_interest
- kadi_linkedin_post_id
- kadi_utm_content
- kadi_qualification_notes

Primero explotar campos estándar. Añadir custom properties sólo cuando eviten pérdida real de información.
