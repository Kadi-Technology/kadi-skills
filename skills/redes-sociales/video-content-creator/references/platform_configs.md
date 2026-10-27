# Configuraciones por Plataforma — Creador de Contenido

## YouTube (Documental / Técnico)
```python
PLATFORM_YOUTUBE = {
    "nombre": "YouTube",
    "output_size": (1920, 1080),
    "fps": 30,
    "duracion_objetivo_min": 4,
    "duracion_objetivo_max": 10,
    "codec": "libx264",
    "bitrate": "8000k",
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "preset": "medium",
    "subtitulos": {
        "posicion": "bottom-center",
        "fontsize": 52,
        "color_principal": "#00ffcc",
        "color_sombra": "#ff3366",
        "barra_fondo": True,
        "barra_opacidad": 160,
    },
    "intro": True,          # Slide de título al inicio
    "creditos": True,       # Créditos finales 20s
    "tts_voz_default": "es-CO-SalomeNeural",
    "musica": True,
    "musica_volumen": 0.18,
    "notas": "Contenido técnico largo. Incluir descripción SEO y timestamps en la descripción.",
}
```

## LinkedIn (Profesional / Corporativo)
```python
PLATFORM_LINKEDIN = {
    "nombre": "LinkedIn",
    "output_size": (1920, 1080),
    "fps": 30,
    "duracion_objetivo_min": 1,
    "duracion_objetivo_max": 3,
    "codec": "libx264",
    "bitrate": "6000k",
    "audio_codec": "aac",
    "audio_bitrate": "128k",
    "preset": "fast",
    "subtitulos": {
        "posicion": "bottom-center",
        "fontsize": 48,
        "color_principal": "#ffffff",
        "color_sombra": "#000000",
        "barra_fondo": True,
        "barra_opacidad": 180,
    },
    "intro": False,
    "creditos": True,       # Breve, 10s
    "tts_voz_default": "es-CO-SalomeNeural",
    "musica": True,
    "musica_volumen": 0.12,
    "notas": "Tono formal y profesional. Sin jerga. Enfocado en resultados de negocio.",
}
```

## Instagram Reels / TikTok (Vertical)
```python
PLATFORM_REELS = {
    "nombre": "Instagram Reels / TikTok",
    "output_size": (1080, 1920),  # VERTICAL
    "fps": 30,
    "duracion_objetivo_min": 0.5,
    "duracion_objetivo_max": 1.5,
    "codec": "libx264",
    "bitrate": "5000k",
    "audio_codec": "aac",
    "audio_bitrate": "128k",
    "preset": "fast",
    "subtitulos": {
        "posicion": "center",     # Centrado en pantalla vertical
        "fontsize": 65,           # MÁS GRANDE para pantallas móviles
        "color_principal": "#ffffff",
        "color_sombra": "#000000",
        "barra_fondo": True,
        "barra_opacidad": 200,
    },
    "intro": False,
    "creditos": False,
    "tts_voz_default": "es-CO-SalomeNeural",
    "musica": True,
    "musica_volumen": 0.25,
    "notas": "ALERTA: Output size es VERTICAL (1080x1920). Aplicar crop o letterbox al video horizontal.",
    "transformacion_video": "crop_vertical",  # Recortar el centro del video horizontal
}
```

## Demo Interno / Documental Técnico
```python
PLATFORM_DEMO = {
    "nombre": "Demo Interno",
    "output_size": (1920, 1080),
    "fps": 30,
    "duracion_objetivo_min": 3,
    "duracion_objetivo_max": 15,
    "codec": "libx264",
    "bitrate": "10000k",   # Alta calidad para presentaciones
    "audio_codec": "aac",
    "audio_bitrate": "256k",
    "preset": "slow",      # Mejor calidad, más tiempo de renderizado
    "subtitulos": {
        "posicion": "bottom-center",
        "fontsize": 52,
        "color_principal": "#00ffcc",
        "color_sombra": "#ff3366",
        "barra_fondo": True,
        "barra_opacidad": 140,
    },
    "intro": True,
    "creditos": True,
    "tts_voz_default": "es-CO-SalomeNeural",
    "musica": True,
    "musica_volumen": 0.15,
    "notas": "Sin restricciones de duración. Priorizar calidad sobre velocidad de renderizado.",
}
```

## Función de Detección Automática de Plataforma
```python
def detect_platform(texto_usuario: str) -> dict:
    texto = texto_usuario.lower()
    if "youtube" in texto or "yt" in texto:
        return PLATFORM_YOUTUBE
    elif "linkedin" in texto or "linked in" in texto:
        return PLATFORM_LINKEDIN
    elif "instagram" in texto or "reel" in texto or "tiktok" in texto or "vertical" in texto:
        return PLATFORM_REELS
    else:
        return PLATFORM_DEMO  # Default: demo técnico
```

## Estilos Visuales Predefinidos
```python
ESTILOS = {
    "cyberpunk": {
        "color_texto": "#00ffcc",
        "color_sombra": "#ff3366",
        "fondo_creditos": (0, 0, 0),
        "fuente": r"C:\Windows\Fonts\cour.ttf",
        "descripcion": "Neón cian + rojo sobre negro. Ideal para tech/dev content.",
    },
    "corporativo": {
        "color_texto": "#4fc3f7",
        "color_sombra": "#000000",
        "fondo_creditos": (10, 10, 46),
        "fuente": r"C:\Windows\Fonts\arial.ttf",
        "descripcion": "Azul profesional sobre oscuro. Ideal para LinkedIn/demos.",
    },
    "minimalista": {
        "color_texto": "#1a1a1a",
        "color_sombra": "#ffffff",
        "fondo_creditos": (255, 255, 255),
        "fuente": r"C:\Windows\Fonts\arial.ttf",
        "descripcion": "Texto oscuro sobre blanco. Ideal para educativo/formal.",
    },
    "matrix": {
        "color_texto": "#00ff41",
        "color_sombra": "#003300",
        "fondo_creditos": (13, 17, 23),
        "fuente": r"C:\Windows\Fonts\consola.ttf",
        "descripcion": "Verde terminal sobre negro. Ideal para hacking/coding.",
    },
}

def detect_style(texto_usuario: str) -> dict:
    texto = texto_usuario.lower()
    if "corporat" in texto or "formal" in texto or "professional" in texto:
        return ESTILOS["corporativo"]
    elif "minimal" in texto or "clean" in texto or "educativ" in texto:
        return ESTILOS["minimalista"]
    elif "matrix" in texto or "verde" in texto or "terminal" in texto:
        return ESTILOS["matrix"]
    else:
        return ESTILOS["cyberpunk"]  # Default
```
