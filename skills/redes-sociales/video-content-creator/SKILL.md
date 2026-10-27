---
name: video-content-creator
description: >
  Skill de producción profesional de video para Antigravity. Actívalo cuando el usuario
  use el comando /Creador.de.contenido o pida editar, producir o crear un video documental,
  promocional o técnico a partir de grabaciones de pantalla, clips de cámara o carpetas
  de medios. Opera como Orquestador de Enjambre: delega análisis a subagentes Gemini 3.7 Flash High / 3.1 Pro
  y centraliza el juicio para producir un script Python ejecutable con moviepy + edge-tts.
  Conocimiento base: sesión "Operación Leviatán" (KADI, 2026-08-07) — 29 subagentes,
  4 videos, narración TTS Salomé Colombia, subtítulos PIL neón cian, créditos cinematográficos.
---

# 🎬 SKILL: CREADOR DE CONTENIDO DE VIDEO
**Orquestador de Producción Profesional con Enjambre Gemini**

---

## ACTIVACIÓN

Este skill se activa con el comando:
```
/Creador.de.contenido [descripción del video] usando [carpeta] para [plataforma]
```

Ejemplos válidos:
```
/Creador.de.contenido edita un documental técnico usando C:\Videos\Capturas2 para YouTube
/Creador.de.contenido crea un reel promocional usando C:\Proyectos\Demos para Instagram
/Creador.de.contenido produce un video de onboarding usando C:\Capturas\ para LinkedIn
```

---

## ENTORNO TÉCNICO VERIFICADO (Windows)

### Stack de producción disponible (sin instalación adicional):
| Herramienta | Versión | Uso |
|-------------|---------|-----|
| Python | 3.13 | Runtime principal |
| moviepy | 1.0.3 | Edición, cortes, composición |
| PIL/Pillow | 12.2.0 | Overlays y subtítulos (sin ImageMagick) |
| numpy | 2.5.1 | Arrays de imagen |
| edge-tts | 7.2.8 | Narración TTS vía Microsoft Azure |
| opencv-python | 5.0.0 | Análisis de actividad visual |
| imageio-ffmpeg | 0.6.0 | FFmpeg v7.1 empaquetado |
| pydub | 0.25.1 | Manipulación de audio |

### Rutas críticas del sistema:
```python
import imageio_ffmpeg, os
os.environ['IMAGEIO_FFMPEG_EXE'] = imageio_ffmpeg.get_ffmpeg_exe()
# SIEMPRE ejecutar esto ANTES de importar moviepy
```

### Fuentes disponibles en Windows (para PIL):
```
C:\Windows\Fonts\cour.ttf      # Courier New — estilo terminal
C:\Windows\Fonts\courbd.ttf    # Courier New Bold
C:\Windows\Fonts\consola.ttf   # Consolas
C:\Windows\Fonts\arial.ttf     # Arial — fallback universal
```

### ⚠️ CRÍTICO: ImageMagick NO está instalado.
**NUNCA uses `TextClip` de moviepy directamente.** Siempre usa PIL + `ImageClip`.

---

## LECCIÓN CLAVE: BITRATE DE GRABACIONES DE PANTALLA

Las grabaciones de pantalla en Windows (OBS, Xbox Game Bar) tienen bitrate
variable que depende del movimiento en pantalla:

| Tipo de contenido | Bitrate real | Error de estimación |
|-------------------|-------------|---------------------|
| Chat/texto estático | ~1.3 Mbps | Subestima duración 10x |
| Código/terminal activo | ~3-5 Mbps | Subestima 3x |
| Video con movimiento | ~8-15 Mbps | Cercano |

**NUNCA estimes duración por tamaño de archivo.**
**SIEMPRE verifica con moviepy o OpenCV primero.**

```python
from moviepy.editor import VideoFileClip
v = VideoFileClip(path)
print(f"Duración REAL: {v.duration:.1f}s ({v.duration/60:.1f} min)")
v.close()
```

---

## PROTOCOLO DE ORQUESTACIÓN (OLEADAS DE SUBAGENTES)

### Arquitectura de roles y modelos:

| Rol | Modelo | Tarea |
|-----|--------|-------|
| R3 Cartógrafo | `flash` | Escanear carpeta, listar videos, verificar herramientas |
| R4 Analista | `pro` | Leer duración real con moviepy/OpenCV, extraer frames |
| R4 Actividad | `flash` | Calcular actividad visual con OpenCV (mejores timestamps) |
| R5 Planificador | `pro` | Diseñar estructura narrativa, guión, overlays |
| R5 Narrador | `pro` | Escribir guión TTS por segmento |
| R6 Ejecutor | `flash` | Escribir script Python ejecutable |
| R3 TTS | `flash` | Verificar voces disponibles, generar audio de prueba |
| R9 Diablo | `pro` | Identificar riesgos antes de ejecutar |

### Oleada 1 — Reconocimiento (desplegar en paralelo):
```
REQ_01: R3 Cartógrafo    | flash | Listar videos en carpeta, tamaños, fechas
REQ_02: R3 Herramientas  | flash | Verificar Python, moviepy, edge-tts, ffmpeg
REQ_03: R4 Duraciones    | flash | Leer duraciones REALES con moviepy de todos los videos
REQ_04: R4 Actividad     | flash | Análisis OpenCV de actividad visual (top timestamps)
REQ_05: R3 TTS           | flash | Verificar voz solicitada en edge-tts
```

### Oleada 1.5 — Análisis Semántico Visual (NUEVA FASE OBLIGATORIA):
```
REQ_EXTRA: R4 Visión     | flash | Extraer frames de los timestamps detectados en OpenCV.
REQ_EXTRA: R5 Analista   | pro   | Analizar visualmente los frames extraídos (usando capacidades de visión).
OBJETIVO: Generar un semantic_map.json que describa qué sucede realmente en cada clip (ej. "Pantalla de Login", "Doctora atendiendo"). NUNCA asumir el contenido por el nivel de actividad de píxeles.
```

### Oleada 2 — Diseño (después de recibir datos de Oleada 1.5):
```
REQ_06: R5 Narrativa     | pro   | Diseñar estructura por actos según plataforma
REQ_07: R5 Narrador      | pro   | Escribir guión TTS completo (frase por segmento)
REQ_08: R5 Overlays      | pro   | Diseñar overlays PIL: textos, posiciones, colores
REQ_09: R9 Riesgos       | pro   | Identificar fallos: RAM, timestamps, audio, codecs
```

### Oleada 3 — Producción (después de aprobar diseño):
```
REQ_10: R6 Script        | flash | Escribir operacion_leviatan.py completo y ejecutable
REQ_11: R3 TTS-Gen       | flash | Generar todos los archivos MP3 de narración
REQ_12: R4 Frames        | flash | Extraer frames de preview en timestamps seleccionados
```

---

## CONFIGURACIONES POR PLATAFORMA

Lee el archivo de referencia completo en:
`references/platform_configs.md`

Resumen rápido:

| Plataforma | Duración | Resolución | Subtítulos | Música | TTS |
|-----------|----------|------------|------------|--------|-----|
| YouTube | 4-10 min | 1920×1080 | Sí, bottom-center | Ambient/cyberpunk | Sí |
| LinkedIn | 1-3 min | 1920×1080 | Sí, formal | Instrumental suave | Sí |
| Instagram Reel | 30-90s | 1080×1920 (vertical) | Sí, grande | Trending | Opcional |
| TikTok | 30-60s | 1080×1920 (vertical) | Sí, centrado | Trending | Opcional |
| Twitter/X | 30-140s | 1280×720 | Opcional | No necesaria | Opcional |
| Interno/Demo | Sin límite | 1920×1080 | Técnico | Cyberpunk | Sí |

---

## VOCES TTS DISPONIBLES (edge-tts)

Ver lista completa en: `references/tts_voices.md`

Recomendadas para español:
```
es-CO-SalomeNeural    ← FAVORITA: Colombiana, acento neutro profesional, femenina
es-CO-GonzaloNeural   ← Colombiano, masculino, formal
es-MX-DaliaNeural     ← Mexicana, cálida, femenina
es-MX-JorgeNeural     ← Mexicano, grave, masculino
es-ES-AlvaroNeural    ← España, masculino, documental
es-ES-ElviraNeural    ← España, femenina, elegante
```

---

## PALETAS VISUALES POR ESTILO

| Estilo | Fondo | Texto principal | Acento | Fuente |
|--------|-------|-----------------|--------|--------|
| Cyberpunk Dark | #000000 | #00ffcc | #ff3366 | cour.ttf |
| Corporativo | #0a0a2e | #ffffff | #4fc3f7 | arial.ttf |
| Documental Netflix | #1a1a1a | #ffffff | #e50914 | arial.ttf |
| Minimalista Blanco | #ffffff | #1a1a1a | #0066ff | arial.ttf |
| Tech Verde | #0d1117 | #00ff41 | #ffffff | consola.ttf |

---

## COMPONENTES PYTHON REUTILIZABLES

Lee el archivo de referencia: `references/python_components.md`

Incluye funciones probadas y listas para copiar:
- `safe_subclip()` — carga clips validando timestamps vs duración real
- `make_subtitle_overlay()` — overlays PIL con barra semitransparente
- `make_credits_sequence()` — créditos cinematográficos de N pantallas
- `generate_all_tts()` — genera todos los audios TTS en paralelo con asyncio
- `analyze_video_activity()` — OpenCV para encontrar los mejores timestamps

---

## FLUJO DE EJECUCIÓN COMPLETO

```
1. PARSEAR comando del usuario
   └─ extraer: carpeta_fuente, plataforma, estilo, voz_tts, duración_objetivo

2. OLEADA 1 — Reconocimiento (subagentes flash en paralelo)
   ├─ Listar videos en carpeta
   ├─ Verificar entorno Python
   ├─ Leer duraciones REALES con moviepy
   └─ Calcular actividad visual con OpenCV

3. CENTRALIZAR datos → Orquestador decide timestamps candidatos

4. OLEADA 1.5 — Análisis Semántico Visio-Espacial
   ├─ Extraer frames de los mejores timestamps (OpenCV)
   └─ Describir contenido real de los frames (semantic_map.json)

5. OLEADA 2 — Diseño (subagentes pro en paralelo)
   ├─ Estructura narrativa basada ESTRICTAMENTE en semantic_map.json
   ├─ Guión TTS por segmento (garantizando coherencia visual)
   ├─ Sistema de overlays PIL
   └─ Análisis de riesgos (R9)

5. ORQUESTADOR revisa plan y mitiga riesgos

6. OLEADA 3 — Producción (subagentes flash)
   ├─ Script Python ejecutable
   ├─ Generación de audio TTS
   └─ Frames de preview

7. ORQUESTADOR valida script y entrega al PO con instrucciones de ejecución
```

---

## REGLAS DE ORO DEL ORQUESTADOR

1. **NUNCA estimes duración por tamaño de archivo** → Siempre leer con moviepy
2. **NUNCA uses TextClip** → Siempre PIL + ImageClip
3. **SIEMPRE configura IMAGEIO_FFMPEG_EXE** antes de importar moviepy
4. **SIEMPRE usa safe_subclip()** → valida timestamps contra duración real
5. **NUNCA cargues todos los videos en RAM** → procesa clip a clip y cierra
6. **SIEMPRE escala todos los clips a OUTPUT_SIZE** → evita mismatch resoluciones
7. **SIEMPRE silencia el audio original si hay TTS** → Si el segmento usa narración TTS, el volumen del clip original DEBE ser 0 (o no mezclarse) para evitar que voces pre-grabadas colisionen con la voz TTS.
8. **SIEMPRE genera TTS primero** → async gather paralelo, luego ensambla
9. **El bitrate de salida MÍNIMO es 4000k** → mitiga degradación de fuentes
10. **CERO TOLERANCIA A ATAJOS** → El orquestador tiene ESTRICTAMENTE PROHIBIDO saltarse fases o ignorar la Oleada 1.5. No se puede construir narrativa a ciegas basada en "actividad de píxeles".
11. **Si edge-tts falla** → continúa sin TTS, no abortes el renderizado

---

## INSTRUCCIONES PARA EL AGENTE

Cuando este skill sea activado:

1. **LEE** `references/platform_configs.md` para la configuración de plataforma
2. **LEE** `references/python_components.md` para las funciones reutilizables
3. **PARSEA** el comando del usuario extrayendo: carpeta, plataforma, estilo deseado
4. **DESPLIEGA OLEADA 1** de subagentes flash para reconocimiento
5. **ESPERA** callbacks y centraliza la inteligencia
6. **DESPLIEGA OLEADA 2** de subagentes pro para diseño narrativo
7. **MITIGA** los riesgos identificados por R9 en el script
8. **DESPLIEGA OLEADA 3** para producción del script final
9. **ENTREGA** al usuario:
   - Script Python ejecutable `produccion_[nombre].py`
   - Comando exacto para ejecutarlo
   - Instrucciones para agregar música y videos adicionales
   - Tiempo estimado de renderizado

**PROHIBIDO:** Alucinaciones de timestamps. Todo timestamp debe ser verificado con moviepy o OpenCV por un subagente antes de incluirlo en el script.
