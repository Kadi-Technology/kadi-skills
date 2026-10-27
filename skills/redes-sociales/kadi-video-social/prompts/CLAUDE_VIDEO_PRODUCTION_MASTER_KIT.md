# KADI v1.7 — Manual Maestro de Producción de Video con Claude (Remotion + HTML5 Artifacts + FFmpeg)

> **Documento de Arquitectura y Pipeline de Producción Audiovisual con Claude**  
> **Propósito:** Reestructurar la estrategia publicitaria para que **Claude** sea el motor principal de planificación, composición, renderizado y generación de videos promocionales profesionales de KADI v1.7, eliminando la dependencia de herramientas externas complejas.

---

## 1. Selección de Modelos de Razonamiento de Claude por Fase

Para lograr la máxima calidad en los videos promocionales, se debe asignar la tarea al modelo de Claude adecuado según su fortaleza de razonamiento:

| Fase del Pipeline | Modelo Recomendado | Razón Técnica & Función Especifica |
|---|---|---|
| **1. Estrategia & Guionismo Técnico** | **Claude 3.7 Sonnet (Extended Thinking)** / **Opus 4.6** | Razonamiento profundo para estructurar storyboards, arcos narrativos B2B, ganchos de conversión y timing por segundo. |
| **2. Composición de Animaciones HTML5/CSS** | **Claude 3.7 Sonnet** / **Sonnet 4.6** | Alta capacidad de código en React, SVG y CSS3 Keyframes para crear Artifacts de animación web en tiempo real. |
| **3. Programación de Video en Remotion** | **Claude 3.7 Sonnet** / **Sonnet 4.6** | Creación de componentes React para la librería **Remotion**, permitiendo renderizar píxel a píxel videos MP4 a 60 FPS en 1080p/4K. |
| **4. Scripts de Automatización FFmpeg & TTS** | **Claude 3.5 Haiku** / **Flash 3.5** | Generación rápida de scripts de PowerShell / Node.js para procesamiento por lotes de imágenes, voz sintética y ensamble. |

---

## 2. Tres Tecnologías / Funcionalidades de Claude para Producir Videos

Claude utilizará **3 vías técnicas** para entregar los videos promocionales listos:

```
                               ┌──────────────────────────────────────────────────────────┐
                               │                    MOTOR CLAUDE                          │
                               └────────────────────────────┬─────────────────────────────┘
                                                            │
         ┌──────────────────────────────────────────────────┼──────────────────────────────────────────────────┐
         ▼                                                  ▼                                                  ▼
┌──────────────────────────────┐          ┌──────────────────────────────────┐          ┌──────────────────────────────────┐
│   VÍA 1: ARTIFACTS HTML5     │          │    VÍA 2: REMOTION (REACT MP4)   │          │  VÍA 3: FFMPEG + EDGE-TTS CLI    │
│  • Presentador visual web    │          │  • Renderizado nativo 1080p/4K   │          │  • Script de 1-Clic en PowerShell│
│  • Animación CSS3 + SVG      │          │  • Control exacto por frames     │          │  • Locución neural + Ken Burns   │
│  • Previsualización en chat  │          │  • Exporta archivo MP4 directo   │          │  • Genera archivo .mp4 final     │
└──────────────────────────────┘          └──────────────────────────────────┘          └──────────────────────────────────┘
```

### Vía 1: Artifacts HTML5 / Canvas / SVG (Previsualización e Animación en Vivo)
- **Cómo funciona:** Claude crea un reproductor HTML5 interactivo como un *Artifact* dentro de la conversación.
- **Componentes:**
  - Animaciones fluidas en CSS3 (Ken Burns, transiciones cross-fade, tipografía animada).
  - Integración directa de las capturas de pantalla reales (`_docs/marketing/assets/screenshots/*.png`).
  - Locución asistida por Web Speech API / Audio HTML5.
- **Uso ideal:** Validación rápida del guión visual antes de renderizar el archivo final.

### Vía 2: Remotion (Framework de Video Programático en React)
- **Cómo funciona:** Claude genera el código completo de un proyecto **Remotion** en React (`npx remotion render`).
- **Componentes:**
  - Componentes `<Composition />`, `<Sequence />`, `<Img />`, `<Interpolate />`.
  - Transiciones profesionales (fade, slide, zoom cinemático, Blur).
  - Superposición de marca KADI (logotipo, badges de IA Gladys, gráficas financieras).
- **Uso ideal:** Producción en calidad broadcast de 60 FPS en 1080p y 4K para YouTube y LinkedIn.

### Vía 3: Script Automatizado FFmpeg + Edge-TTS (Pipeline de 1-Clic)
- **Cómo funciona:** Claude escribe un script en PowerShell (`_workflows/scripts/build_kadi_video.ps1`) que automatiza todo el proceso sin necesidad de editores de video.
- **Pasos del Script:**
  1. Sintetiza la locución en español neutro profesional utilizando `edge-tts` (Voz `es-MX-DaliaNeural` o `es-MX-JorgeNeural`).
  2. Lee los screenshots PNG de `_docs/marketing/assets/screenshots/`.
  3. Aplica efectos de movimiento de cámara (Efecto Ken Burns pan & zoom) vía FFmpeg.
  4. Superpone títulos, subtítulos y marca de agua.
  5. Une el audio y el video en un archivo ejecutable `.mp4`.

---

## 3. Adaptación de Formatos por Red Social

| Red Social | Formato | Duración | Enfoque de Contenido | Assets Clave Utilizados |
|---|---|---|---|---|
| **Instagram Reels / TikTok** | 9:16 (1080x1920) | 15 - 30s | Dinámico, problemas reales de clínicas, solución inmediata con Gladys IA y Caja. | `01_dashboard.png`, `05_caja.png`, `07_vacunas.png` |
| **LinkedIn Enterprise** | 16:9 / 1:1 (1080p) | 45 - 60s | Métricas de ROI, adquisición de código fuente completo, arquitectura Laravel 13 + React 19. | `01_dashboard.png`, `04_inventario.png`, `09_reportes.png` |
| **YouTube Product Tour** | 16:9 (1080p/4K) | 2 - 3 min | Tour guiado por los 9 módulos, demostración financiera y consulta médica asistida. | Todas las 9 capturas (`01` a `09`) |

---

## 4. Guiones y Prompts de Estructura para Claude

### A. Estructura de Prompts para generar componentes Remotion en Claude:
```text
"Actúa como un Desarrollador Senior de Remotion (React Video Framework). Genera un componente de video en React de 30 segundos (900 frames a 30fps) en formato 16:9 para KADI v1.7. 
Usa las siguientes imágenes ubicadas en '_docs/marketing/assets/screenshots/':
1. Frame 0-150: 01_dashboard.png con un zoom in suave de 1.0 a 1.15 y título superpuesto 'Gestión Clínica de Última Generación'.
2. Frame 151-400: 02_directorio.png con transición de desplazamiento lateral y título 'Expediente Único y Control de Pacientes'.
3. Frame 401-650: 06_uci.png y 07_vacunas.png mostrando monitoreo crítico y esquemas de vacunación.
4. Frame 651-900: 05_caja.png con llamado a la acción final 'KADI v1.7 — Adquiere el Software o la Licencia OEM'."
```

---

## 5. Instrucciones para la Ejecución Local

Para generar los videos directamente en este espacio de trabajo con Claude:

1. **Vía Automatizada FFmpeg (Recomendada por rapidez):**
   - Asegurarse de tener Python y FFmpeg instalados.
   - Ejecutar el script automatizado que crearemos en `_workflows/scripts/generate_kadi_video.py` o `.ps1`.

2. **Vía Remotion (Recomendada para la más alta calidad gráfica):**
   - Ejecutar `npx create-video` o inicializar Remotion en una carpeta temporal.
   - Copiar el código React que Claude genere directamente dentro del proyecto y correr `npx remotion render`.

---

## 6. Inventario de Assets Disponibles para Claude

Claude utilizará las capturas reales ya generadas y ubicadas en `_docs/marketing/assets/screenshots/`:

- `01_dashboard.png` (Dashboard con Monitor Kanban y KPIs)
- `02_directorio.png` (Directorio de Pacientes y Clientes)
- `03_agenda.png` (Agenda de Citas Médicas)
- `04_inventario.png` (Inventario y Vademécum Clínico)
- `05_caja.png` (Caja / Punto de Venta y Cobros)
- `06_uci.png` (Hospitalización y Cuidados Intensivos)
- `07_vacunas.png` (Registro de Vacunas y Refuerzos)
- `08_cuentas_por_cobrar.png` (Cuentas por Cobrar)
- `09_reportes.png` (Reportes de Inteligencia de Negocios BI)

---
*Documento maestro actualizado para el pipeline nativo con Claude en KADI v1.7.*
