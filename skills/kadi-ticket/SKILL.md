---
name: kadi-ticket
description: Emite, valida y registra un Ticket de Despacho del KADI Harness antes de delegar trabajo a un subagente o de tocar un repo. Úsalo al empezar cualquier tarea que edite archivos en un repo del portafolio KADI o que despache un ejecutor.
---

# kadi-ticket (parte de F-01, router)

Toda tarea del Harness empieza con un Ticket (`docs/CONSTITUCION.md` C-01). Esta skill es una receta; no amplía permisos ni sustituye a la guarda.

## Pasos

1. Escribe la tarea en JSON fuera del Harness (p. ej. en tu scratch):
   `{"id":"<TAREA>","rutas":["<ruta relativa>", "..."],"dominios":[],"señales":{"documental":false,"efecto_codigo":true,"mecanico":false,"edita_codigo":true},"piso_declarado":null,"clasificacion_datos":"interno"}`.
   Dominios válidos: los que liste `node C:/KADI/harness/bin/kadi.mjs route clasificar` en su mensaje de error. Ante la duda, declara el dominio: la clase solo sube.
2. Clasifica: `node C:/KADI/harness/bin/kadi.mjs route clasificar --tarea <tarea.json>`. Lee `clase`, `piso`, `modelo` y `revisor_requerido_en_ticket`.
3. Emite: `node C:/KADI/harness/bin/kadi.mjs route ticket --tarea <tarea.json> --foto-head <git rev-parse HEAD> --foto-hora <date ISO con zona> --execution-id <id del ejecutor> [--revisor-modelo <id> --revisor-execution-id <id distinto>] --salida <ruta fuera del Harness>`. Exit 0 = `ACEPTADO`; 2 = `RECHAZADO` (lee el motivo); 6 = modelo no autorizado.
4. Registra el despacho (solo el orquestador, fuera del canal guardado): `node C:/KADI/harness/bin/kadi.mjs ledger append --json '{"tipo":"despacho","tarea":"<TAREA>","modelo_pedido":"<alias>","execution_id":"<id>","sha_ticket":"<sha256 del archivo del Ticket>"}'` con `KADI_SESION` = id de tu sesión.
5. Despacha con `model` explícito y el brief de `templates/BRIEF.md`; el write-set del brief es el del Ticket.
6. Al volver: `ledger accept --tarea <TAREA> --informe <archivo> --tokens-in N --tokens-out N --modelo-pedido <alias>` y, al terminar, `ledger close --tarea <TAREA> --resultado <PASS|…> --tests-pass N --tests-total N`.

## Reglas

- Nunca `inherit`; nunca `fable` como subagente; T3-T4 exigen revisor con `execution_id` distinto; T4 exige la frase literal del PO (`aprobacion_po`), que un agente jamás escribe por sí mismo.
- `write_set` sin `..`, sin globs vacíos (`**/**`, `*.*`); si toca `.github/`, la tarea es T4.
- Sin `claude --bare` (R-BARE); sin ejecutores dentro de un `Workflow` (R-WF). Detalle: `docs/RUNBOOK.md` y `docs/GUIA_DESPACHO.md`.
