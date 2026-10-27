---
name: kadi-engineering-guardian
description: >
  KADI Core2 engineering workflow capability-based. Cubre Laravel, React,
  TypeScript, Docker, arquitectura, debugging, code review, documentación
  técnica, planificación de tests y deploy checklists. Usar cuando se
  modifica o audita 999_CODIGO_DEPLOY, backend services/controllers/resources,
  frontend pages/components, infraestructura o runbooks técnicos. Aplicable
  únicamente al motor y rol designados por un sobre PO vigente.
---

## Motor y rol

Esta skill es capability-based. No selecciona plataforma ni concede permisos. La ejecución mecánica se enruta por defecto a `gemini-3-5-flash` como `EXECUTOR`; cualquier motor distinto requiere una nueva decisión PO. Toda escritura exige `WRITER_OF_RECORD` y allowlist exacta.

# KADI Engineering Guardian

## Scope

Use this skill for technical work in:

- `%USERPROFILE%\Desktop\Core2\999_CODIGO_DEPLOY\backend\`
- `%USERPROFILE%\Desktop\Core2\999_CODIGO_DEPLOY\frontend\`
- `%USERPROFILE%\Desktop\Core2\999_CODIGO_DEPLOY\database\`
- `%USERPROFILE%\Desktop\Core2\999_CODIGO_DEPLOY\infrastructure\`
- `%USERPROFILE%\Desktop\Core2\02_INSTALACION\`
- `%USERPROFILE%\Desktop\Core2\08_TRANSFERENCIA\`

## Startup Checklist

1. Apply `$kadi-core2-routing-guardian`.
2. Read only `_HANDOFF/CURRENT_NEXT_AGENT.md`.
3. Inspect the smallest set of files needed with `rg`, `rg --files`, and targeted reads.
4. Identify whether the change touches a critical zone.

Critical zones:

- `backend/app/Services/CajaService.php`
- `backend/app/Services/CuentaService.php`
- `backend/app/Services/AuthService.php`
- `backend/routes/api.php`
- `backend/database/migrations/`
- auth/session middleware
- payment, credit, inventory, role, or audit behavior

## Change Rules

- Keep edits narrow and consistent with local Laravel/React patterns.
- Prefer existing services, requests, resources, and helpers over new abstractions.
- `01_CODIGO/` is absolutely intocable; no reading, writing, or analysis. No PO authorization or session allowlist can enable its modification.
- Do not edit `.env` files.
- Do not use Git.
- Do not run test suites under the Core2 Data Room rule unless there is a specific PO authorization in the active session envelope. If verification matters, state the exact command that should be run by the Tech Lead.
- For frontend changes, preserve operational density and avoid marketing-style UI.
- For backend changes, preserve role checks, auditability, and response shape compatibility.

## Review Output

When reviewing or reporting:

1. Lead with bugs, risks, regressions, and missing verification.
2. Cite file paths and line numbers when available.
3. Separate `[EVIDENCIA]`, `[RIESGO]`, `[INFERENCIA]`, and `[RECOMENDACION]`.
4. State whether code was changed or only analyzed.
5. Deliver a contract-complete replacement for `_HANDOFF/CURRENT_NEXT_AGENT.md` for the next engineering or QA step.
6. End with `Prompt inmediato para el siguiente agente` and all fields required by `.agents/contracts/HANDOFF_CONTRACT.json`.
7. Persist the replacement only when the PO envelope authorizes that write; otherwise return it in chat and declare `HANDOFF_WRITE_AUTHORIZATION_REQUIRED`.
