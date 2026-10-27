# Prompt Maestro para Claude — Producción End-to-End de Videos Promocionales de KADI v1.7

Copiar y pegar todo el bloque a continuación en **Claude (usando Claude 3.7 Sonnet con Extended Thinking o Claude 3 Opus)**:

```markdown
Eres el Arquitecto Audiovisual y Desarrollador Principal de KADI v1.7 (Sistema ERP/CRM para clínicas veterinarias en Laravel 13 + React 19 + TypeScript + PostgreSQL 17).

Tu objetivo es ejecutar y completar EN UNA SOLA INTERVENCIÓN (End-to-End) la producción completa del paquete de videos promocionales para KADI v1.7 orientados a 3 plataformas comerciales:
1. Instagram Reels / TikTok (Formato 9:16 - 1080x1920, 30 segundos) — Enfocado en clínicas veterinarias.
2. LinkedIn Enterprise (Formato 16:9 - 1920x1080, 60 segundos) — Enfocado en Inversores, Agencias Dev (Venta de Código Fuente IP) y Cadenas OEM.
3. YouTube Product Tour (Formato 16:9 - 1920x1080, 2 minutos) — Tour guiado empresarial.

---

### CONTEXTO TÉCNICO Y ASSETS DISPONIBLES EN EL WORKSPACE:

1. **Documentación Maestra:**
   - Lee y respeta la estrategia en `_docs/marketing/CLAUDE_VIDEO_PRODUCTION_MASTER_KIT.md`.
   - Consulta el reproductor interactivo de referencia en `_docs/marketing/HTML5_MOTION_VIDEO_PLAYER.html`.

2. **Assets Fotográficos de Alta Resoluición (Rutas de Imágenes Reales en `_docs/marketing/assets/screenshots/`):**
   - `01_dashboard.png` (Dashboard, Monitor Kanban, KPIs y Finanzas)
   - `02_directorio.png` (Directorio de Clientes y Pacientes)
   - `03_agenda.png` (Agenda de Citas Médicas)
   - `04_inventario.png` (Inventario y Vademécum Clínico)
   - `05_caja.png` (Caja / Punto de Venta y Finanzas Auditadas)
   - `06_uci.png` (Hospitalización y Cuidados Intensivos UCI)
   - `07_vacunas.png` (Control de Vacunación y Refuerzos)
   - `08_cuentas_por_cobrar.png` (Cuentas por Cobrar)
   - `09_reportes.png` (Reportes BI e Inteligencia de Negocios)

---

### ENTREGABLES QUE DEBES GENERAR Y COMPLETAR AHORA MISMO:

#### Entregable 1: Guiones de Locución y Storyboard Frame a Frame
- Escribe el guion técnico completo con marcas de tiempo (0s a 30s para Reels, 0s a 60s para LinkedIn, 0s a 120s para YouTube).
- Incluye el texto exacto de la locución en español neutro (Voz profesional) y las anotaciones visuales por segundo indicando qué captura se muestra y qué animación se aplica.

#### Entregable 2: Código Remotion en React Completo
- Escribe el código en React/Remotion completo (`Composition.tsx` o `KadiVideoPromo.tsx`) listo para renderizar.
- Debe incluir animaciones de cámara (zoom in/out, Ken Burns effect, transiciones crossfade), superposición de badges de IA Gladys, tipografía moderna y visualización limpia de los screenshots de KADI.

#### Entregable 3: Script Automatizado de 1-Clic en PowerShell/Python con FFmpeg y Edge-TTS
- Genera un script ejecutable (`_workflows/scripts/generate_all_videos.ps1` o `.py`) que realice lo siguiente automáticamente:
  1. Sintetice los archivos de audio MP3 de locución utilizando `edge-tts` (con las voces `es-MX-DaliaNeural` o `es-MX-JorgeNeural`).
  2. Aplique los efectos visuales Ken Burns y transiciones a las capturas PNG.
  3. Formatee y ensamble los videos finales en archivos `.mp4` listos para ser descargados y publicados (`kadi_reels_9x16.mp4`, `kadi_linkedin_16x9.mp4`, `kadi_youtube_16x9.mp4`).

Empieza y completa la tarea de una sola vez, entregando los tres componentes de forma impecable y lista para producción.
```
