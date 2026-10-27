---
name: chrono-tts
description: Genera y reproduce audios asíncronos utilizando ChronoSDK (el motor oficial de la Hueste). Úsalo cuando el usuario pida un "resumen de voz", "hablar" o "narrar".
---

# Generación de Audio con ChronoSDK

Esta skill define el procedimiento estándar para que la Hueste (agentes) hable y narre utilizando el SDK oficial del ecosistema.

## Flujo de Trabajo Obligatorio

1. **Uso del Comando CLI (Principal):**
   - Para narrar un texto de forma asíncrona (sin bloquear tu ejecución ni la del humano), utiliza el comando `chrono speak` a través de la herramienta `run_command`.
   - Sintaxis: `chrono speak "<texto_a_narrar>" --agent <opus|flash|sonnet>`
   - No necesitas limpiar el texto de caracteres especiales, el módulo `sanitizer.py` de Chrono lo hace automáticamente.

2. **Uso Programático en Python (Avanzado):**
   - Si estás creando un script, importa la librería:
     ```python
     from chrono import speak
     speak("El sistema está estable", agent="flash", use_fillers=True)
     ```
   
3. **Restricción Arquitectónica:**
   - **PROHIBIDO** utilizar comandos crudos de `edge-tts`. ChronoSDK ya lo envuelve, maneja el caché SHA1, inyecta muletillas y lo reproduce en un Worker desprendido.
