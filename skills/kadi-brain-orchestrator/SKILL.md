---
name: kadi-brain-orchestrator
description: Workflow de orquestación de élite KADI v3.0 (Quad-Brain Engine) que combina a Fable 5.1 (Estrategia Omnisciente), Opus 5.5 (Arquitectura Técnica y DAGs) y Sonnet 5.5 (Síntesis Quirúrgica de Código) con Prompt Caching y razonamiento adaptativo, mientras Antigravity (Gemini 3.8) actúa como el Caballo de Batalla Operativo Local en Windows NTFS. Úsalo para planificar misiones técnicas, features complejas, síntesis de código de grado de producción y auditorías pre-merge.
---

# KADI Brain Orchestrator v3.0.0 — Enterprise Quad-Brain Engine

Este skill define la gobernanza, dimensionamiento y ejecución de misiones de desarrollo de software dentro de KADI Technology, uniendo lo mejor de los modelos de frontera de Anthropic con las capacidades de ejecución nativas de Antigravity (Gemini 3.8) sobre Windows NTFS.

---

## 1. Arquitectura de Roles: El Cuarteto Especializado

```
  ┌─────────────────────────────────────────────────────────────┐
  │                 PRODUCT OWNER (Humano)                      │
  │            Formula requerimiento y aprueba                  │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│       CLAUDE FABLE 5.1       │              │       CLAUDE OPUS 5.5        │
│  Estratega Omnisciente       │              │  Arquitecto Técnico Maestro  │
│  - Visión de Portafolio      │              │  - Descomposición DAG        │
│  - Roadmaps de Negocio / UX  │              │  - Esquemas DDL / Contratos  │
│  - Directivas Arquitectónicas│              │  - Auditoría de Aislamiento  │
│  ($50/MTok salida)           │              │  ($20/MTok salida)           │
└──────────────┬───────────────┘              └──────────────┬───────────────┘
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │ Plan / Especificación
                                      ▼
                      ┌──────────────────────────────┐
                      │      CLAUDE SONNET 5.5       │
                      │  Sintetizador Quirúrgico     │
                      │  - Código fuente íntegro     │
                      │  - Diffs y parches exactos   │
                      │  - Cero placeholders         │
                      │  ($15/MTok salida, $3 entrada)│
                      └──────────────┬───────────────┘
                                     │ Código / Playbook
                                     ▼
                      ┌──────────────────────────────┐
                      │    GEMINI 3.8 (ANTIGRAVITY)  │
                      │  Caballo de Batalla Local    │
                      │  - Entorno Windows NTFS      │
                      │  - Modificación de archivos  │
                      │  - Linters, cargo, npm, php  │
                      │  - Cero costo de API local   │
                      └──────────────────────────────┘
```

### ¿Por qué Gemini 3.8 es el Caballo de Batalla Operativo Local?
1. **Acceso Nativo al Sistema Operativo**: Gemini 3.8 corre dentro de Antigravity con herramientas directas de lectura/escritura (`replace_file_content`, `write_to_file`) y ejecución de comandos en PowerShell (`run_command`).
2. **Cero Fricción Financiera**: Si pusiéramos a un modelo de API (como Sonnet u Opus) a iterar directamente en el disco duro ejecutando comandos de consola mediante un bucle de agentes, cada comando, lectura y prueba consumiría tokens de API, gastando decenas de dólares innecesariamente. Gemini 3.8 ejecuta localmente con ventana de contexto de 1 millón de tokens sin generar cargos de API por comando.
3. **El Rol Óptimo de Sonnet 5.5**: En lugar de pelear con el sistema de archivos local, Sonnet 5.5 es invocado quirúrgicamente para **sintetizar el código fuente complejo** (controladores, migraciones, traits HMAC, algoritmos de cálculo, componentes frontend). Gemini 3.8 toma ese código, lo inyecta en los archivos locales, corre los linters y compila.

---

## 2. Gobernanza de Tokens y Razonamiento Adaptativo

Los modelos 5.5 y 5.1 de Anthropic emplean **Razonamiento Adaptativo** (`thinking: adaptive`). El comportamiento se controla mediante `output_config: {effort: "low" | "medium" | "high"}`:

| Modelo | Rol | Nivel de Esfuerzo (`effort`) | Tokens Salida (`max_tokens`) | Costo Salida |
|---|---|---|---|---|
| **Fable 5.1** | Visión / Roadmaps | `low` o `medium` | **8,192** | \$50 / MTok |
| **Opus 5.5** | Planificación DAG | `medium` | **16,384** | \$20 / MTok |
| **Opus 5.5** | Auditoría Pre-Merge | `low` | **8,192** | \$20 / MTok |
| **Sonnet 5.5** | Síntesis de Código | `low` (máxima velocidad) | **16,384** | \$15 / MTok |
| **Opus / Sonnet** | Código Masivo | `medium` | **32,768+** (Streaming automático) | Tarifa estándar |

### Reglas de Oro Financieras:
1. **Prompt Caching Efímero (90% Descuento)**: Todos los llamados inyectan la radiografía de repositorios (`13_` y `14_`) con `cache_control: {"type": "ephemeral"}`. La relectura de 20,000+ tokens cuesta solo **\$0.30 a \$0.40 por millón**, ahorrando un 90% en la entrada.
2. **Techo No-Streaming de 16,384 tokens**: La API de Anthropic rechaza llamadas estándar superiores a 16,384 tokens. El motor conmuta automáticamente a **Streaming** (`client.messages.stream`) cuando la tarea requiere más de 16k tokens.
3. **Control de Esfuerzo (`effort: low`)**: Para tareas de código con Sonnet 5.5, `effort: low` garantiza que el modelo dedique sus tokens a redactar código fuente y no a divagar en razonamientos abstractos.

---

## 3. Comandos CLI del Motor (`brain_orchestrator.py`)

Ubicación del script ejecutable:
```powershell
python "%USERPROFILE%\.claude\skills\kadi-brain-orchestrator\scripts\brain_orchestrator.py" <subcomando> [opciones]
```

### 3.1 Planificación Quirúrgica con Opus 5.5 (`plan`)
```powershell
python "%USERPROFILE%\.gemini\config\skills\kadi-brain-orchestrator\scripts\brain_orchestrator.py" plan \
  --goal "Diseñar la arquitectura de firma HMAC y anti-replay en Core" \
  --repo "Core" \
  --effort "medium" \
  --output "%USERPROFILE%\Desktop\plan_hmac.md"
```

### 3.2 Directiva Estratégica con Fable 5.1 (`strategy`)
```powershell
python "%USERPROFILE%\.gemini\config\skills\kadi-brain-orchestrator\scripts\brain_orchestrator.py" strategy \
  --topic "Estrategia de lanzamiento y monetización de la Cartilla Digital" \
  --effort "low" \
  --output "%USERPROFILE%\Desktop\estrategia_cartilla.md"
```

### 3.3 Síntesis Quirúrgica de Código con Sonnet 5.5 (`synthesize`)
```powershell
python "%USERPROFILE%\.gemini\config\skills\kadi-brain-orchestrator\scripts\brain_orchestrator.py" synthesize \
  --spec "Crear trait PHP 8.2 para validar firmas HMAC-SHA256 con ventana anti-replay de 300s" \
  --repo "Core" \
  --effort "low" \
  --output "%USERPROFILE%\Desktop\ValidatesHmacSignature.php"
```

### 3.4 Auditoría Pre-Merge de Parches con Opus 5.5 (`audit`)
```powershell
python "%USERPROFILE%\.gemini\config\skills\kadi-brain-orchestrator\scripts\brain_orchestrator.py" audit \
  --diff "cambios_locales.patch"
```

### 3.5 Flujo de Trabajo Multietapa en Cascada (`workflow`)
Para features completas y misiones complejas que encadenan los modelos:
```powershell
python "%USERPROFILE%\.gemini\config\skills\kadi-brain-orchestrator\scripts\brain_orchestrator.py" workflow \
  --goal "Implementar el módulo completo de exportación a PDF nativo en Contract ERP" \
  --repo "Contract" \
  --effort "medium"
```
*Este comando automatizado produce en `Desktop\KADI_NOTEBOOKLM_KNOWLEDGE_BASE\workflows\<timestamp>_<slug>\`:*
1. `01_PLAN_ARQUITECTONICO.md` (Opus 5.5 con desglose de interfaces y comandos Rust).
2. `02_CODIGO_SINTETIZADO.md` (Sonnet 5.5 con código Rust y SolidJS listo para compilar).
3. `03_PLAYBOOK_ANTIGRAVITY.md` (Opus 5.5 con instrucciones exactas de terminal para Gemini 3.8).
4. `04_CRITERIOS_ACEPTACION_Y_ROLLBACK.md` (DoD estricto y plan de reversión).
5. `REPORTE_CONSOLIDADO_WORKFLOW.md` (Reporte integral para el Product Owner).

---

## 4. Matriz de Decisión Rápida

```
¿La tarea requiere planificar o modificar múltiples archivos?
  ├── NO (Consulta puntual, typo, correr comandos de consola) 
  │     └──► BYPASS: Gemini 3.8 (Antigravity) ejecuta directo en local.
  └── SÍ
        ├── ¿Es estrategia de producto, portafolio o UX? 
        │     └──► FABLE 5.1 (`strategy --effort low`)
        ├── ¿Es arquitectura técnica o desglose DAG? 
        │     └──► OPUS 5.5 (`plan --effort medium`)
        ├── ¿Es redacción de código complejo o difícil? 
        │     └──► SONNET 5.5 (`synthesize --effort low`)
        └── ¿Es una misión compleja de punta a punta? 
              └──► QUAD-BRAIN WORKFLOW (`workflow --goal ...`)
                   1. Opus 5.5 diseña el plan.
                   2. Sonnet 5.5 sintetiza el código.
                   3. Gemini 3.8 aplica, compila y prueba en Windows.
                   4. Opus 5.5 audita el diff final.
```
