---
name: kadi-core2-routing-guardian
description: >-
  Guardrail principal para cualquier tarea de KADI en Core2. Fuerza workspace
  Core2-only, separación entre motor/rol/autoridad, sobre default-deny,
  protección de secretos y continuidad mediante un handoff canónico.
---

# KADI Core2 Routing Guardian

## Routing activo

- `gpt-sol-5-6`: arquitectura y auditoría; `READ_ONLY` por defecto.
- `fable-5`: análisis y consolidación; `READ_ONLY` por defecto.
- `gemini-3-5-flash`: executor y QA mecánico mediante sobres separados.
- Ningún motor, plataforma, workflow, skill o herramienta concede autoridad.
- GPT o FABLE sólo pueden editar cuando el PO lo autoriza expresamente para una tarea.
- Gemini sólo escribe bajo `EXECUTION_ENVELOPE` PO; su sobre QA es read-only.
- Subagentes y ejecución desatendida permanecen denegados mientras no exista autorización y calificación separadas.

## Required startup

1. Confirmar `%USERPROFILE%\Desktop\Core2`, `AGENTS.md` y `999_CODIGO_DEPLOY/`.
2. No usar `%USERPROFILE%\Desktop\Core` como fuente activa.
3. Leer la constitución y los contratos canónicos.
4. Leer el briefing, objetivo aplicable y únicamente `_HANDOFF/CURRENT_NEXT_AGENT.md`.
5. Leer los `PENDIENTES_*.md` de cualquier carpeta que pueda cambiar.
6. Declarar el sobre operativo. Campo omitido = `DENIED`.

## Hard stops

- No leer ni tocar `.env`, secretos o credenciales.
- `01_CODIGO/` permanece `DENEGADO` por defecto. Sólo puede tocarse mediante el gate constitucional `PROMOCION_UNICA_01_CODIGO`, activado por decisión PO literal y por un sobre operativo nuevo, completo, separado y de un solo uso.
- El gate de promoción es no transferible y no heredable; su estado vive en `_HANDOFF/CURRENT_NEXT_AGENT.md`, se consume al cerrar el sobre de promoción y nunca suspende los demás hard stops.
- No usar Git.
- No borrar, mover ni reescribir histórico o evidencia.
- No tocar producción ni distribuir externamente sin decisión PO literal.
- `999_CODIGO_DEPLOY/` es la única fuente técnica viva y permanece denegada salvo allowlist específica.
- No declarar buyer-ready, legal, seguridad, QA, UAT, staging, producción o cero regresiones sin evidencia y aceptación aplicables.

## Evidence discipline

Usar `[EVIDENCIA]`, `[SIN EVIDENCIA]`, `[RIESGO]`, `[CONTRADICCIÓN]`, `[INFERENCIA]`, `[RECOMENDACIÓN]`, `[BLOQUEANTE]`, `[DECISIÓN PO]`, `[NO TOCAR]` y `[BORRADOR — PENDIENTE VALIDACIÓN]`.

## Closeout

Sólo el writer-of-record puede materializar el cierre.

1. Separar archivos creados, modificados, validaciones, límites y pendientes.
2. Actualizar únicamente `_HANDOFF/CURRENT_NEXT_AGENT.md` cuando exista continuidad.
3. Cumplir `.agents/contracts/HANDOFF_CONTRACT.json`.
4. Entregar un `Prompt inmediato para el siguiente agente` sin placeholders con:
   - motor y rol;
   - objetivo y estado;
   - primeras fuentes;
   - allowlists;
   - comandos;
   - prohibiciones;
   - evidencia;
   - aceptación;
   - stop conditions;
   - primera acción.
5. El prompt nunca transfiere permisos, writer, PASS o calificación.

Un auditor o QA read-only reporta por el canal y no escribe salvo nueva autorización PO explícita.
