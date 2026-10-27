# Arquitectura del Ecosistema KADI Technology: 11 Sistemas de Misión Crítica

¿Por qué construimos software empresarial con arquitectura **Local Primero** en lugar de depender ciegamente de la conectividad remota?

En sectores como la atención médica veterinaria, la construcción de obra civil o la gestión de condominios residenciales, la conectividad a internet no es homogénea ni infalible. Cuando una clínica veterinaria pierde señal a mitad de una consulta, o cuando un campamento de obra en terracería no tiene enlace de datos, la operación no puede detenerse.

Frente a esta realidad, en **KADI Technology** diseñamos y construimos un ecosistema de **11 sistemas de software** concebidos bajo cuatro principios de ingeniería determinista:

---

### 1. Cuatro Principios de Ingeniería No Negociables
1. **Local Primero (Offline-First Real):** Cada sistema corre con motores de base de datos locales (PostgreSQL o SQLite embebido). La operación continúa sin interrupciones independientemente del estado de la red.
2. **Privacidad Desde el Diseño:** Los expedientes clínicos, contratos y finanzas viven en la infraestructura del cliente. Recolectamos lo indispensable y nada sale del equipo sin una razón técnica fundamentada y autorización explícita.
3. **Integridad Criptográfica:** Presupuestos, órdenes de cambio y comprobantes generan huellas digitales SHA-256 inmutables para auditoría y control interno.
4. **Decisión Humana al Centro:** La tecnología y los modelos analíticos asisten, organizan y explican sus sugerencias; el criterio y la decisión final son siempre de las personas facultadas.

---

### 2. Estado de Madurez de las Verticales Principales

- **Salud Animal — KADI SCV & Gladys (Cohorte Founder #001):**
  Sistema clínico veterinario integral (expediente, agenda, hospitalización/UCI, inventario/vademécum, caja y reportes). Actualmente en **despliegue piloto con la versión 1.7** en una clínica activa; la **versión 1.8** está en preparación e integrará a **Gladys**, asistente de inteligencia artificial local que responde sobre antecedentes y signos vitales sin transferir datos a internet. *(Herramienta de gestión clínica; no sustituye el criterio médico veterinario).*

- **Construcción — Contract ERP (En Desarrollo):**
  Aplicación de escritorio para Windows construida en **Tauri 2 + Rust + React 19 + SQLite**. Permite gestionar obras y presupuestos por partidas con historial de revisiones sellado con hash SHA-256, órdenes de cambio formales y aritmética monetaria exacta en enteros para evitar discrepancias por redondeo. *(Herramienta de control interno; no sustituye comprobantes fiscales).*

- **Condominios — TVillage (En Desarrollo):**
  Plataforma para administración de condominios con evidencia alineada a la Ley de Propiedad en Condominio de la Ciudad de México. Presenta un cierre mensual en 5 pasos con conciliación explicada, visto bueno del Comité de Vigilancia, acuses individuales desde el teléfono móvil sin forzar registro y bitácora verificable mediante código QR. *(Versión 0.2 funcional probada con datos de demostración; en preparación de edificio piloto).*

- **Educación, Videojuegos, Infraestructura y Finanzas:**
  Complementan el portafolio **Academia** (motor adaptativo que ejecuta Python en navegador con WebAssembly sin conexión), **Vital Signs Vet** (simulación clínica veterinaria interactiva), **ChronoSDK** (infraestructura de voz asíncrona para auditoría de sistemas multiagente) y **GK Docs Recibos** (motor de comprobantes de control interno con sello criptográfico).

---

### 3. Vinculación y Handoff Ejecutivo
Invitamos a directores médicos, contratistas y administradores a conocer la documentación técnica de nuestros proyectos y evaluar la incorporación a próximas cohortes piloto:

- **Portal Institucional y Portafolio Completo:**  
  [https://kadi.technology?utm_source=linkedin&utm_medium=organic_social&utm_campaign=lote_inaugural_01](https://kadi.technology?utm_source=linkedin&utm_medium=organic_social&utm_campaign=lote_inaugural_01)

- **Contacto de Ingeniería y Alianzas:**  
  <NOMBRE_COFUNDADOR_1> & <NOMBRE_COFUNDADOR_2> · Cofundadores  
  Correo directo: `<CORREO_CONTACTO>`  
  Agenda de demostración técnica: [Agendar Demostración](https://calendar.app.google/<ID_AGENDA>)

---

#SoftwareEngineering #LocalFirst #EnterpriseSoftware #B2BSoftware #KADITechnology #HealthTech #PropTech #ConTech #RustLang #PostgreSQL
