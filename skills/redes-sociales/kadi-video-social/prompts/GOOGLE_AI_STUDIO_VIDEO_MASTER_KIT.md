# KADI v1.7 — Manual Maestro de Producción de Video en Google AI Studio (Veo + Imagen 3 + Gemini Audio)

> **Documento de Arquitectura Audiovisual B2B y Estrategia Comercial**
> **Propósito:** Proporcionar las directrices, prompts, storyboards y configuraciones técnicas para que el equipo humano o agentes produzcan videos de alta conversión comercial, calidad cinematográfica empresarial y acabado profesional utilizando exclusivamente el ecosistema nativo de **Google AI Studio** (Google Veo, Imagen 3, Gemini Audio/TTS).

---

## 1. Diagnóstico de Estrategia Audiovisual

### ¿Por qué fallaba el enfoque previo dentro del IDE?
1. **Falta de Fotografía Cinemática:** El renderizado sintético web o de capturas crudas carece de profundidad de campo (bokeh), iluminación volumétrica y presencia humana realista.
2. **Ausencia de Dirección de Cámara:** La grabación de pantalla es estática y aburrida; carece de movimientos orbitales, zooms dramáticos, panorámicas y planos de reacción.
3. **Falta de Narrativa de Alto Impacto:** Un video comercial exitoso no muestra solo botones; vende **transformación, ROI, escalabilidad y la visión de la Inteligencia Artificial (Gladys)**.

### La Solución: Pipeline en Google AI Studio (Ecosistema Veo & Imagen 3)
```
[ Gemini 1.5/2.5/3 Pro ] ---> Generación de Guiones, Estructura de Escena y SFX Prompts
          │
          ├───> [ Imagen 3 / 4 ] ---> Fotogramas Clave (Keyframes UI + Realistic Scenes)
          │                                  │
          │                                  ▼
          ├───> [ Google Veo 2 ]  <--- Image-to-Video & Text-to-Video 1080p/4K
          │
          └───> [ Gemini Voice / Audio ] ---> Narración en Off (Locución Pro Hipernatural)
                                                     │
                                                     ▼
                                            [ Ensamblado Final ]
```

---

## 2. Parámetros Técnicos por Plataforma

| Criterio | Instagram / TikTok / Shorts | LinkedIn Enterprise / Inversores | YouTube Product Tour |
|---|---|---|---|
| **Relación de Aspecto** | 9:16 (Vertical 1080x1920) | 16:9 u 1:1 (1080x1080 / 1920x1080) | 16:9 (Horizontal 1920x1080 / 4K) |
| **Duración Ideal** | 15 - 30 segundos | 45 - 90 segundos | 2 a 4 minutos |
| **Target Principal** | Veterinarios, Médicos, Administradores | Inversores, Agencias Dev (Venta IP/Código), Cadenas OEM | Comités Tecnológicos, Directores de Clínicas |
| **Ritmo de Edición** | Ultrarrápido (Cortes cada 1.5 - 2.5s) | Moderado, sobrio y elegante (Cortes cada 3 - 5s) | Explicativo, fluido, inmersivo (Cortes cada 4 - 8s) |
| **Hook Inicial** | Problema dramático en < 3s | Métrica de ROI / Oportunidad de Adquisición de IP | Frase de visión empresarial + Gladys IA |

---

## 3. Guía de Estructuración de Prompts para Google Veo (Veo Prompt Syntax)

Para obtener resultados de nivel Hollywood/Comercial de Apple en **Google Veo**, los prompts deben seguir la estructura de **6 Bloques Clave**:

```text
[CAMERAMOVEMENT] + [SUBJECT & ACTION] + [ENVIRONMENT & LIGHTING] + [STYLE & AESTHETICS] + [AUDIO/MOOD] + [TECHNICAL SPECIFICATIONS]
```

### Ejemplos de Vocabulario Clave para Veo Prompts:

- **Cámara:** `Cinematic slow orbital sweep`, `Macro extreme close-up with shallow depth of field`, `Smooth FP-1 tracking shot`, `Dolly zoom effect`.
- **Iluminación:** `Volumetric soft studio lighting`, `Neon teal and warm golden accent lights`, `Clean clinical morning sunlight piercing through glass window`.
- **Sujeto/Ambiente:** `Modern high-end veterinary clinic with sleek glass panels`, `Dr. Sarah, a confident female veterinarian holding a tablet showing KADI interface`, `Futuristic AI holographic overlay representing Gladys AI`.
- **Estilo:** `Photorealistic 8K, commercial quality, shot on 35mm lens, ARRI Alexa Mini, clean color grade, architectural Digest aesthetic`.
- **Restricciones Negativas (en AI Studio):** `no blur, no distorted hands, no glitchy text, no low resolution, no artifacts`.

---

## 4. Estrategia Comercial de Triples Vertientes de Venta

Google AI Studio nos permitirá producir piezas adaptadas a **3 modelos de negocio de KADI**:

1. **Venta de Licencias SaaS / Mensuales a Clínicas Veterinarias:**
   - Enfoque: Reducción de tiempos administrativos, control financiero antiderrames, consulta clínica potenciada por Gladys IA.
2. **Venta de Licencias OEM en Marca Blanca (White-Label):**
   - Enfoque: Para distribuidores o cadenas que desean revender KADI bajo su propia marca, colores, dominio y configuración.
3. **Venta Total de Propiedad Intelectual (IP) + Código Fuente Completo:**
   - Enfoque: Para Agencias de Software o Inversores que buscan comprar el 100% de la solución lista para producción (Laravel 13 + React 19 + TypeScript + PostgreSQL 17), ahorrándose 2 años de desarrollo enterprise.

---

## 5. Próximos Pasos en el Workspace
1. Consultar los archivos específicos de guiones y prompts en `_docs/marketing/`:
   - `SCRIPTS_AND_PROMPTS_INSTAGRAM_REELS.md`
   - `SCRIPTS_AND_PROMPTS_LINKEDIN_ENTERPRISE.md`
   - `SCRIPTS_AND_PROMPTS_YOUTUBE_PRODUCT_TOUR.md`
2. Copiar los prompts directamente a **Google AI Studio** (`veo-2` e `imagen-3`).
3. Descargar las tomas generadas, ensamblarlas con la locución de Gemini Audio y publicar en los canales oficiales.

---

## 6. Evidencias Reales Capturadas (Assets de UI del Frontend)

Para alimentar a **Google Veo 2** e **Imagen 3** en modo *Image-to-Video* o *Keyframe Reference*, se capturaron imágenes reales del sistema en la carpeta `_docs/marketing/assets/screenshots/`:

| Módulo / Pantalla | Archivo 16:9 (Desktop) | Archivo 9:16 (Vertical) |
|---|---|---|
| **Pantalla de Login** | `00_login_page_16x9.png` | `00_login_page_9x16.png` |
| **Dashboard Principal / Monitor del Día** | `01_dashboard_principal_16x9.png` | `01_dashboard_principal_9x16.png` |
| **Directorio de Clientes & Pacientes** | `02_directorio_clientes_16x9.png` | — |
| **Ficha Clínica con Asistente Gladys IA** | `03_ficha_clinica_gladys_ia_16x9.png` | `03_ficha_clinica_gladys_ia_9x16.png` |
| **Agenda Médica & Citas** | `04_agenda_citas_16x9.png` | — |
| **Caja Registradora & Finanzas Auditadas** | `05_caja_finanzas_16x9.png` | — |

