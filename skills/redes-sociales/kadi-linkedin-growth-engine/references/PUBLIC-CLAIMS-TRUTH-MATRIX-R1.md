# KADI Public Claims Truth Matrix R1

Estado: CANÓNICO PARA LINKEDIN R1

Enforcement machine-readable: `docs/linkedin/public-claims-r1.json`. El Markdown explica la política; el manifest alimenta el gate CI.
Corte técnico: 2026-09-20/21
Fuentes primarias:
- KadiWebPage/main
- kadi-scv/main
- producción pública kadi.technology cuando aplique

## Regla

Un claim público sólo puede clasificarse como:

- GREEN: puede publicarse con la redacción indicada.
- YELLOW: existe evidencia, pero requiere contexto o actualización antes de usarlo.
- RED: no publicar hasta resolver evidencia/contradicción.

## GREEN — claims habilitados

| Claim público | Redacción segura | Evidencia |
|---|---|---|
| KADI es software para clínicas y hospitales veterinarios | “KADI es software para clínicas y hospitales veterinarios.” | KadiWebPage src/index.html, src/clinicas.html |
| Conecta recepción, consulta, hospitalización, caja e inventario | “KADI conecta recepción, consulta, hospitalización, caja e inventario alrededor del mismo expediente/contexto operativo.” | src/index.html, src/producto.html |
| Recepción está entregada | “Recepción está disponible para conocerla en la demo.” | src/producto.html |
| Consulta está entregada | “Consulta está disponible para conocerla en la demo.” | src/producto.html |
| Hospitalización está entregada | “Hospitalización está disponible para conocerla en la demo.” | src/producto.html |
| Caja está entregada | “Caja y cuentas están disponibles; algunos controles de caja por turnos siguen en endurecimiento.” | src/producto.html |
| Inventario está entregado | “Inventario y vademécum están disponibles para conocerlos en la demo.” | src/producto.html |
| Reportes están entregados | “KADI dispone de reportes operativos y financieros habilitados según la instancia.” | src/producto.html |
| Gladys existe dentro del producto | “Gladys es un asistente de consulta dentro de KADI.” | src/producto.html + screenshot 03 |
| Gladys no diagnostica autónomamente | “Gladys apoya la consulta; el criterio clínico y la decisión permanecen en el médico veterinario.” | src/producto.html |
| Existen roles/permisos | “Recepción, médicos, caja y administración trabajan con accesos según su función.” | src/producto.html + screenshot 15 |
| Existen acciones con trazabilidad | “KADI registra acciones con usuario y momento para apoyar la trazabilidad operativa.” | src/producto.html |
| Personalización por instancia existe | “La instancia puede configurarse con identidad de la clínica.” | src/producto.html + screenshot 14 |
| Multi-sede unificada NO está disponible | “Hoy cada instalación opera de forma independiente; la administración multi-sede unificada está en evaluación.” | src/producto.html |
| El producto tiene evidencia responsive | “La galería pública muestra 38 vistas: 16 desktop, 11 tablet y 11 smartphone.” | src/producto.html |
| KADI usa Laravel/React/PostgreSQL | “El núcleo técnico usa Laravel, React/TypeScript y PostgreSQL.” | kadi-scv/INVENTORY.md |
| main de core está consolidado tras P-136 | “El repositorio canónico integró P-136 y su cierre está documentado.” | kadi-scv/_handoff/CURRENT.md |
| Idempotencia de cartera fue integrada | Usar sólo en contenido técnico: “P-136 de idempotencia de cartera fue integrado en main.” | CURRENT.md + commit 5025e73 / cierre 54026d1 |

## YELLOW — usar sólo con contexto

| Claim | Riesgo | Acción |
|---|---|---|
| “CI 100% verde” | CURRENT.md registra 21/21 checks verdes tras P-136, pero INVENTORY.md conserva una sección de salud anterior con errores/fallos preexistentes de suite global. | No usar en marketing hasta reconciliar inventario/fecha/scope. En ingeniería citar exactamente el run/scope. |
| “103 migraciones / 126 endpoints / 88 backend tests / 34 frontend tests” | INVENTORY declara bloque auto verificado al 2026-09-08, pero también conserva notas históricas con cifras distintas. | Sólo usar con fecha y referencia al bloque CIFRAS-AUTO. No convertir en claim evergreen. |
| “Producto en validación operativa” | La web lo afirma, pero marketing debe evitar convertirlo en número de clínicas, clientes o pilotos. | Redacción permitida: “validación controlada” sin cuantificar. |
| “Despliegues controlados” | Debe distinguirse deploy técnico de cliente comercial activo. | No inferir clientes pagadores ni uso clínico en producción. |
| “Backups automáticos” | INVENTORY los marca verdes en corte anterior. | Sólo usar en material técnico tras confirmar alcance del deployment objetivo. |
| “Gladys 93.33% NLU” | INVENTORY conserva ese dato de auditoría anterior. | No usar en LinkedIn R1 sin revisar prueba, dataset y fecha. |
| “487/487 / 460/460 tests” | Varias cifras corresponden a cortes/suites distintos. | No usar como claim promocional. |
| “v1.7” | INVENTORY aún titula KADI v1.7 mientras existen ramas release/v1.8-deploy. | No afirmar versión comercial actual hasta definir fuente de versión canónica. |

## RED — no publicar

- “Sociedad formalizada” hasta existir verificación jurídica inequívoca.
- “KADI es una empresa constituida” sin documento jurídico vigente verificado.
- “Ronda semilla abierta”, “valuación”, “monto objetivo”, “participación disponible” sin aprobación formal.
- Revenue, ARR, MRR, número de clientes, número de clínicas activas o crecimiento sin fuente verificable.
- “El mejor software veterinario”, “líder”, “#1”, “único” sin investigación comparativa válida.
- Ahorro porcentual o recuperación de ingresos atribuida a KADI sin estudio.
- Resultados clínicos, reducción de errores médicos o mejoras de salud sin evidencia clínica adecuada.
- “Multi-sucursal disponible” mientras src/producto.html lo marca Roadmap.
- “Programa de distribución disponible” mientras src/producto.html lo marca Roadmap.
- “100% seguro”, “sin vulnerabilidades”, “HIPAA compliant”, “certificado” o equivalentes sin certificación aplicable.
- “IA que diagnostica” o “IA que decide tratamiento”.
- Fechas de roadmap como compromisos contractuales.

## Claims por tipo de contenido

### Clínicas
Priorizar:
- menos recaptura;
- contexto compartido;
- continuidad entre áreas;
- producto visible en demo;
- módulos efectivamente entregados.

### Producto
Priorizar:
- screenshots;
- estados Entregado/Endurecimiento/Roadmap;
- flujos concretos.

### Founder
Priorizar:
- decisiones;
- aprendizajes;
- proceso de construcción;
- distinción explícita entre hecho, validación y propuesta.

### Inversión
Priorizar:
- producto y activos verificables;
- problema;
- arquitectura;
- proceso de due diligence;
- necesidades de aceleración sin presentar términos financieros no aprobados.

## Gate editorial

Antes de publicar una frase con número, certificación, estatus jurídico, cliente, seguridad, inversión o resultado clínico:
1. localizar fuente;
2. verificar fecha/scope;
3. comprobar que otra fuente canónica no la contradiga;
4. si contradice: RED hasta reconciliación.
