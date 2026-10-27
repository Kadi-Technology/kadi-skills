---
name: kadi-teamwork-elite
description: >-
  DORMANT_UNQUALIFIED. Especificación histórica de orquestación multiagente para
  Core2. No invocar mientras subagentes o ejecución desatendida estén DENIED.
  Su existencia no concede autoridad ni calificación.
---

# KADI Teamwork Elite — DORMANT_UNQUALIFIED

## Estado operativo

Esta skill no participa en routing activo. El estado vigente de Core2 exige ejecución single-agent y mantiene:

- `subagents: DENIED`;
- unattended execution: `DENIED`;
- transferencia de calificación: `DENIED`;
- Overpower: `DORMANT_UNQUALIFIED`.

No usar primitivas de colaboración, swarms, procesos en background ni delegación por el solo hecho de que el runtime las exponga.

## Requisitos para una futura reactivación

Sólo el PO puede abrir una misión separada que incluya, como mínimo:

1. necesidad demostrada;
2. calificación del runtime exacto;
3. sobre operativo específico;
4. un writer-of-record único;
5. subagentes read-only con allowlists no solapadas;
6. evidencia, timeouts, stop conditions y fallback single-agent;
7. auditoría adversarial y aceptación PO.

Una reactivación no hereda permisos, PASS, modelo, writer ni evidencia histórica.

## Preservación histórica

El protocolo multiagente anterior se conserva como antecedente en el histórico del workspace y en `.agents/contracts/LEGACY_INDEX.md`. No debe reinterpretarse como permiso actual.
