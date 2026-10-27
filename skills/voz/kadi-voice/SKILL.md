---
name: kadi-voice
description: Orquestador de voz para Antigravity en el proyecto KADI. Garantiza que los audios no se encimen usando --blocking siempre. Salomé para reportes normales, Opus para alertas críticas.
---

# KADI Voice — Protocolo de Voz Sin Encimamiento

## Regla Absoluta: SIEMPRE `--blocking`

Nunca lances `chrono speak` sin `--blocking`. Sin este flag, el siguiente audio
puede arrancar mientras el anterior aún reproduce — esto desorienta al PO.

```bash
# ✅ CORRECTO
chrono speak "mensaje" --agent salome --blocking

# ❌ PROHIBIDO
chrono speak "mensaje" --agent salome
```

## Selección de Voz

| Situación | Agente | Cuándo usarlo |
|---|---|---|
| Actualización de progreso | `salome` | Subagente arrancó/terminó sin problemas |
| Reporte de hallazgo menor | `salome` | Información útil pero no urgente |
| Bug crítico encontrado | `opus` | Algo que puede costar dinero o romper el sistema |
| Decisión requerida del PO | `opus` | El agente necesita aprobación antes de continuar |
| Fix completado exitosamente | `salome` | Confirmación de tarea terminada |
| Error irrecuperable | `opus` | El agente se detiene y escala |

## Flujo Estándar Por Tarea

```
1. [salome --blocking] "Arrancando [nombre de tarea]..."
   ↓ (audio termina completamente)
2. [trabajo real ocurre — subagentes, código, etc.]
   ↓ (trabajo termina)
3a. [salome --blocking] "Completado: [resumen corto]"   ← si todo OK
3b. [opus   --blocking] "ALERTA: [descripción del problema]"  ← si hay problema
```

## Mensajes de Audio — Guía de Estilo

- **Duración máxima:** 4-5 oraciones. El PO está ocupado.
- **Estructura:** Qué pasó → Qué significa → Qué sigue (o qué decide el PO).
- **Sin tecnicismos en Salomé.** Opus puede ser más técnico y directo.
- **Salomé habla en primera persona del agente:** "Terminé de analizar..."
- **Opus habla con peso:** "DETENCIÓN REQUERIDA. El siguiente cambio afecta..."

## Wrapper Rápido (uso directo)

### Reporte normal (Salomé):
```bash
chrono speak "<mensaje corto>" --agent salome --blocking
```

### Alerta crítica (Opus):
```bash
chrono speak "<mensaje de alerta>" --agent opus --blocking
```

## Lo que NO hacer

- ❌ Lanzar dos `chrono speak` en el mismo bloque de comandos sin `--blocking` en el primero
- ❌ Usar Opus para reportes de rutina (reservar para cuando realmente importa)
- ❌ Mensajes de más de 6 oraciones (el PO está ocupado, no puede escuchar un podcast)
- ❌ Pasar sin audio cuando hay un evento crítico — siempre notificar al PO
