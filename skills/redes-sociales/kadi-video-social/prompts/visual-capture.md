# Sistema de Recolección y Captura Visual de Marketing — KADI v1.7-rc1

> **Documento oficial:** Guía técnica y operativa para la generación de material gráfico y audiovisual del sistema KADI.
> **Ubicación de scripts:** `_workflows/scripts/`
> **Ubicación de assets generados:** `_docs/marketing/assets/screenshots/`
> **Estado:** 100% Desacoplado (cero referencias a entornos externos o `Core2/`).

---

## 1. Objetivo y Arquitectura

El sistema de captura visual automatizada utiliza **Playwright** para navegar de forma autónoma por la aplicación KADI, autenticarse y tomar capturas de pantalla de alta resolución en múltiples resoluciones de pantalla (Desktop 1080p, Laptop HD 1360×768, Tablet, Móvil).

Estas capturas se utilizan para:
- Material promocional y folletos comerciales.
- Demostración de producto en la web institucional.
- Pipeline de producción de video (Remotion / AI Studio).
- Verificación visual de regresión y responsive layout.

---

## 2. Scripts Disponibles en `_workflows/scripts/`

| Script | Descripción | Comando NPM |
|---|---|---|
| `capture_marketing_screenshots.js` | Captura de vistas principales (Dashboard, Ficha Cliente, Agenda, Caja, POS) en alta resolución con datos demo. | `npm run capture:marketing` |
| `capture_screenshots.js` | Recorrido exhaustivo por todas las páginas del sistema para auditoría de UI. | `npm run capture` |
| `test_auth.js` | Prueba automatizada de autenticación y verificación de login. | `node test_auth.js` |

---

## 3. Requisitos de Ejecución

1. El entorno KADI (backend y frontend) debe estar corriendo en `http://localhost:5173` (o vía Nginx en `http://localhost:8000`).
2. Se requiere tener cargada la base de datos de demostración (`php artisan db:seed --class=DemoMasterSeeder`).

---

## 4. Guía de Ejecución Rápida

```bash
# 1. Navegar al directorio de scripts
cd _workflows/scripts

# 2. Instalar dependencias locales de Playwright (solo la primera vez)
npm install

# 3. Ejecutar captura de marketing
npm run capture:marketing
```

---

## 5. Salida de Assets

Las imágenes generadas se organizan en:
`_docs/marketing/assets/screenshots/`

- `dashboard_1080p.png` — Tablero principal de control
- `ficha_cliente_1080p.png` — Ficha médica del paciente y tutor
- `caja_1080p.png` — Estado de caja y cobros
- `agenda_1080p.png` — Calendario de citas
