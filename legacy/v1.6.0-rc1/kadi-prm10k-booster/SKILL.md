---
name: kadi-prm10k-booster
description: Protocolo PRM-10K de siete fases para decisiones complejas o de alto riesgo en Core2.
---

# PRM-10K Reasoning Booster

PRM-10K estructura análisis; no amplía autoridad ni exige exponer razonamiento interno.

## FASE 0 — Filtro de información

- Identificar información crítica faltante.
- Preguntar sólo si la ausencia bloquea una decisión segura.
- Hacer de una a tres preguntas concretas; si la ambigüedad es menor, declarar supuestos y continuar.

## FASE 1 — Descomposición

Definir variables, restricciones, dependencias, criterios de éxito, evidencia y stop conditions.

## FASE 2 — Exploración divergente

Evaluar al menos tres alternativas genuinas cuando existan. Para cada una: descripción, pros/contras, riesgos, supuestos y coste.

Si sólo una ruta respeta hard stops/autoridad, documentar por qué; no fabricar opciones inseguras.

## FASE 3 — Estrés-prueba

Atacar cada alternativa con fallas, edge cases, supuestos falsos y regresiones.

## FASE 4 — Evaluación comparativa

Usar matriz ponderada o comparación estructurada basada en criterios de la FASE 1.

## FASE 5 — Selección

Elegir, justificar, declarar confianza y qué información cambiaría la decisión.

La confianza debe estar calibrada contra evidencia. Para tareas largas o Overpower:

- usar el índice `IAV1` y los hard gates definidos en `.agents/workflows/overpower-team.md`;
- congelar pesos, criterios y vetos antes de puntuar;
- una dimensión crítica `[SIN EVIDENCIA]`, un P0 o un hard gate fallido limita el veredicto a `NO CALIFICADO`, sin importar el promedio;
- `IAV1` no equivale a probabilidad de éxito ni sustituye el gate empírico `DRY_RUN_A + REAL_AB + COHORT_22`;
- `>=90%` sólo describe el perfil de runtime, protocolo y clase de tarea efectivamente probados;
- no convertir ausencia de hallazgos en evidencia positiva sin justificar cobertura.

## FASE 6 — Self-audit y entrega

Revisar claims, evidencia, lógica, alcance, permisos y pasos omitidos. Corregir antes de entregar.

En tareas complejas, auditar cada requisito como `PROVED | CONTRADICTED | INCOMPLETE | MISSING`; sólo `PROVED` satisface completitud.

Encabezados:

1. Entendimiento del problema
2. Alternativas evaluadas
3. Estrés-prueba (fallas encontradas)
4. Matriz comparativa
5. Decisión final + justificación + confianza
6. Supuestos declarados / info faltante

Toda evidencia cita fuente actual; lo no verificado se etiqueta.
