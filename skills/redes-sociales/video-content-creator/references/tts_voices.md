# Voces TTS Disponibles — edge-tts 7.2.8

## Español — Voces verificadas en el sistema (2026-08-07)

### 🇨🇴 Colombia (RECOMENDADAS)
| ShortName | Género | Notas |
|-----------|--------|-------|
| `es-CO-SalomeNeural` | Femenina | ⭐ FAVORITA. Acento neutro, profesional, cálida |
| `es-CO-GonzaloNeural` | Masculino | Formal, claro, bueno para demos técnicos |

### 🇲🇽 México
| ShortName | Género | Notas |
|-----------|--------|-------|
| `es-MX-DaliaNeural` | Femenina | Cálida y expresiva, buena para contenido casual |
| `es-MX-JorgeNeural` | Masculino | Grave, autoritario, bueno para documentales |

### 🇪🇸 España
| ShortName | Género | Notas |
|-----------|--------|-------|
| `es-ES-AlvaroNeural` | Masculino | Formal europeo, documentales serios |
| `es-ES-ElviraNeural` | Femenina | Elegante, corporativa |
| `es-ES-XimenaNeural` | Femenina | Joven, moderna |

### 🇦🇷 Argentina
| ShortName | Género | Notas |
|-----------|--------|-------|
| `es-AR-ElenaNeural` | Femenina | Acento porteño, expresiva |
| `es-AR-TomasNeural` | Masculino | Casual, para contenido informal |

### Todas las disponibles en español
```
es-AR-ElenaNeural, es-AR-TomasNeural
es-BO-MarceloNeural, es-BO-SofiaNeural
es-CL-CatalinaNeural, es-CL-LorenzoNeural
es-CO-GonzaloNeural, es-CO-SalomeNeural ← RECOMENDADA
es-CR-JuanNeural, es-CR-MariaNeural
es-CU-BelkysNeural, es-CU-ManuelNeural
es-DO-EmilioNeural, es-DO-RamonaNeural
es-EC-AndreaNeural, es-EC-LuisNeural
es-ES-AlvaroNeural, es-ES-ElviraNeural, es-ES-XimenaNeural
es-GQ-JavierNeural, es-GQ-TeresaNeural
es-GT-AndresNeural, es-GT-MartaNeural
es-HN-CarlosNeural, es-HN-KarlaNeural
es-MX-DaliaNeural, es-MX-JorgeNeural
es-NI-FedericoNeural, es-NI-YolandaNeural
es-PA-MargaritaNeural, es-PA-RobertoNeural
es-PE-AlexNeural, es-PE-CamilaNeural
es-PR-KarinaNeural, es-PR-VictorNeural
es-PY-MarioNeural, es-PY-TaniaNeural
es-SV-LorenaNeural, es-SV-RodrigoNeural
es-UY-MateoNeural, es-UY-ValentinaNeural
es-VE-PaolaNeural, es-VE-SebastianNeural
```

## Código para verificar y generar TTS

```python
import asyncio
import edge_tts
import os

async def list_spanish_voices():
    """Lista todas las voces en español disponibles."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v['Locale'].startswith('es')]

async def generate_tts(text: str, path: str, voice: str = 'es-CO-SalomeNeural') -> bool:
    """
    Genera archivo MP3 de narración.
    Retorna True si exitoso, False si falló.
    REQUIERE conexión a internet (Microsoft Azure).
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
        return True
    except Exception as e:
        print(f"TTS error ({voice}): {e}")
        return False

# Verificar voz antes de producción masiva
async def verify_voice(voice: str) -> bool:
    voices = await edge_tts.list_voices()
    names = [v['ShortName'] for v in voices]
    exists = voice in names
    print(f"Voz '{voice}': {'✅ DISPONIBLE' if exists else '❌ NO ENCONTRADA'}")
    return exists

# Ejemplo de uso
if __name__ == '__main__':
    asyncio.run(verify_voice('es-CO-SalomeNeural'))
```

## Notas importantes sobre edge-tts

1. **Requiere internet**: Conecta a servidores Microsoft Azure. Sin internet = fallo silencioso.
2. **Rate limiting**: Si generas muchos audios rápido, Microsoft puede throttlear. 
   Solución: `asyncio.gather()` los genera en paralelo sin saturar.
3. **Caracteres especiales**: Evita tildes y ñ en el texto si hay errores. 
   Alternativa: usar texto sin acentos para el archivo, el TTS los interpreta bien igual.
4. **Duración del audio**: No puedes saber la duración del MP3 antes de generarlo.
   Siempre recorta con `.subclip(0, min(tts_audio.duration, clip_duration - 0.2))`.
5. **Caching**: Si el archivo ya existe, reutilizarlo ahorra tiempo y evita rate limit.
