---
name: kadi-ultra-eco
description: Modo Ultracode Económico de KADI (La Hueste por tiers). Destila el comportamiento de ultracode (orquestar cada tarea sustantiva con Workflows masivos, verificación adversarial y síntesis por fases) pero enruta cada subagente al tier más barato capaz de hacerlo - T1 Peón (sonnet/xhigh), T2 Capitán (opus/high), T3 Estratega (fable/high) - en vez de heredar el modelo y el esfuerzo de la sesión. El orquestador es la sesión principal con el esfuerzo que el usuario elija (xhigh o max). Solo se activa con /kadi-ultra-eco.
disable-model-invocation: true
argument-hint: "<tarea> | on | off | status | plan <tarea>"
---

# KADI Ultra-Eco v1.0 — Ultracode destilado, Hueste por tiers

## 0. Qué destila y dónde está el ahorro

Ultracode son cuatro piezas: (a) opt-in permanente al tool Workflow; (b) orquestar toda tarea sustantiva con un workflow por fase (Understand → Design → Implement → Review); (c) patrones de calidad (verificación adversarial, barrido multimodal, crítico de completitud, loop-until-dry); (d) el costo no es restricción: cada `agent()` sin `model`/`effort` **hereda el modelo y el esfuerzo de la sesión**, así que con una sesión Opus/Fable en xhigh/max, cada subagente corre en Opus/Fable xhigh/max.

Ultra-Eco conserva (a), (b) y (c) y sustituye (d) por enrutamiento explícito por tiers.

| Palanca | Ultracode | Ultra-Eco |
|---|---|---|
| Modelo de subagentes | hereda la sesión | T1/T2/T3 explícito; nunca hereda |
| Esfuerzo de subagentes | hereda (xhigh/max) | xhigh solo en Sonnet; high en Opus y Fable; nunca max |
| Verificación | N votos al modelo de la sesión | 2 votos T1 con lentes distintas; T2 desempata solo si se dividen |
| Escalada | todo al tope desde el inicio | T1 → T2 → T3 solo ante rechazo o baja confianza |
| Juicio y síntesis | modelo de la sesión | T3 solo en decisiones de arquitectura o irreversibles (máx. 3 por workflow) |
| Orquestador | sesión | sesión (xhigh o max, lo elige el usuario); su esfuerzo nunca se propaga |

Precios de API por MTok, entrada / salida (caché del skill claude-api, 2026-10-06): Haiku 5.5 $0.10 / $0.50 · Sonnet 5.5 $2 / $10 · Opus 5.5 $4 / $20 · Fable 5.1 $10 / $50.

Ejemplo de mezcla (40 agentes: 30 T1, 8 T2, 2 T3): precio medio de salida ponderado = (30·10 + 8·20 + 2·50) / 40 = $14/MTok, frente a $20 si todos heredan Opus (−30 %) o $50 si todos heredan Fable (−72 %). A eso se suma el ahorro de esfuerzo (high en vez de xhigh/max en T2/T3) y de escalada (solo se paga T2/T3 cuando T1 falla). El ahorro real depende de los tokens por agente: mídelo con `scripts/eco_costos.py` (§11).

## 1. Activación y alcance

| Comando | Efecto |
|---|---|
| `/kadi-ultra-eco <tarea>` | Activa el modo y ejecuta la tarea orquestada. |
| `/kadi-ultra-eco on` | Modo permanente en la sesión: toda tarea sustantiva posterior se orquesta con workflows Ultra-Eco hasta `off`. |
| `/kadi-ultra-eco off` | Vuelve al comportamiento normal (Workflow solo con opt-in explícito). |
| `/kadi-ultra-eco status` | Muestra modo, matriz de tiers, cuotas y el ledger acumulado de la sesión. |
| `/kadi-ultra-eco plan <tarea>` | Solo planifica: fases, agentes por tier y costo estimado vs. ultracode con `scripts/eco_costos.py`. No lanza workflows. |

- **Parseo:** es subcomando solo si el primer token es exactamente `on`, `off`, `status` o `plan`; `on`/`off`/`status` no admiten texto adicional (si lo hay, todo es la tarea). El ledger acumulado de la sesión es la suma de los `ledger` que devuelve cada workflow.
- **Opt-in:** invocar este skill es el opt-in explícito al tool Workflow (el usuario invocó un skill cuyas instrucciones ordenan llamar a Workflow). Por eso lleva `disable-model-invocation: true`: el modelo nunca lo auto-activa.
- **Esfuerzo del orquestador:** la sesión principal es el cerebro. El usuario elige xhigh o max en el selector de la app; el skill no lo cambia. Ese esfuerzo se gasta en descomponer, escribir scripts y leer resultados, nunca en los subagentes.
- **Cuándo NO orquestar** (resuélvelo inline): turnos conversacionales, ediciones mecánicas triviales, consultas de 1 a 3 tool calls, o trabajo ya verificado.

## 2. La Hueste: matriz de tiers (inmutable)

| Tier | Nivel | `model` | `effort` | $ salida | Trabajo típico |
|---|---|---|---|---|---|
| **T1 Peón** | básico | `sonnet` | `xhigh` | 10 | leer y mapear, buscar, finders por dimensión, escribir código por archivo con spec cerrada, transformar sitios de migración, refutadores, extracción a schema |
| T1m (subperfil) | mecánico | `sonnet` | `medium` | 10 | correr gates y comandos, parsear logs, contar, listar: trabajo sin juicio |
| **T2 Capitán** | intermedio | `opus` | `high` | 20 | consolidar mapas, revisar diffs, desempatar votos, depurar causa raíz tras un fallo T1, implementar lógica no trivial cuando T1 fue rechazado, proponer enfoques de diseño, crítico de completitud |
| **T3 Estratega** | avanzado | `fable` | `high` | 50 | juez de panel de diseño, síntesis final de arquitectura, decisiones irreversibles (contratos congelados, ADR, migraciones de datos), hallazgos de severidad crítica, último escalón de la escalada |

**Ley Anti-Herencia:** cada `agent()` del script pasa `model` y `effort`, siempre a través de los helpers `t1`/`t2`/`t3`/`escalar`/`verificar` del preludio (§6). Un `agent()` sin `model` hereda la sesión y reproduce el costo de ultracode: prohibido. La misma ley rige para el tool Agent (§9).

**Cuotas por workflow** (defaults; ajustables con `args.eco`):
- Mezcla objetivo: ≥ 70 % T1, ≤ 25 % T2, ≤ 5 % T3.
- T3: máximo 3 por workflow (`eco.t3Max`). Al agotarse, el helper degrada a T2 y lo registra con `log()`.
- T0 Haiku (`haiku`/`low`) no se usa por defecto; solo si el usuario lo pide para trabajo puramente mecánico (contar, listar, formatear).

## 3. Enrutador

```
¿Lo resuelve el orquestador con ≤ 3 tool calls sin leer mucho?      → inline, sin agente
¿Leer, buscar, listar, extraer, transformar o escribir con spec cerrada? → T1
¿Juzgar trabajo ajeno (revisar, consolidar, desempatar) o depurar tras un fallo? → T2
¿Arquitectura, irreversible, juez final entre alternativas o severidad crítica? → T3
¿En duda?                                                            → el tier más bajo + escalar()
```

**Escalada por etapas:** T1 intenta → criterio de aceptación en código (schema con `confianza` y `bloqueos`, tests, o `verificar()`) → si se rechaza, T2 recibe el intento previo y el motivo → si se rechaza, T3. Empieza en T2 o T3 solo en las categorías de la tabla. Si una categoría escala más del 30 % de las veces, arráncala en T2 (pagar T1 + T2 sale más caro que T2 directo).

## 4. Escala

| Escala | Agentes por workflow | Cuándo |
|---|---|---|
| S | ≤ 5 | tarea acotada, una fase |
| M | 6–20 | feature o auditoría de un subsistema (default del skill) |
| L | 21–60 | barrido de repositorio, migración, auditoría exhaustiva |
| XL | 61–200 | solo con presupuesto explícito del usuario (`+500k`, etc.) |

- Si la sesión trae una guía de tamaño de workflow (p. ej. "small"), respétala salvo que el mensaje del usuario pida escala mayor ("masivo", "exhaustivo", un `+Nk`). Al lanzar, di en una línea qué escala usas y por qué.
- Con presupuesto `+Nk`, los loops se gobiernan con `budget.remaining()` y se reserva el 15 % para la síntesis final.
- Concurrencia real: min(16, CPUs − 2) agentes a la vez; el resto se encola.

## 5. Ciclo operativo

1. **Scout inline** (orquestador, barato): Glob/Grep para descubrir la work-list y el alcance. No leas completos los archivos que un T1 va a leer.
2. **Un workflow por fase.** Lee el resultado de cada fase antes de diseñar la siguiente; tú permaneces en el loop.
3. **Cada script** empieza con `export const meta = {...}` (literal puro) seguido del **preludio de §6 copiado literal**. Script en JS plano, pasado inline en `script` (no lo escribas antes a un archivo). Para iterar: edita el archivo que devuelve el tool y relanza con `scriptPath` (+ `resumeFromRunId`).
4. **Prompts de subagentes:** objetivo, rutas y criterio de aceptación; nunca volcados de archivos. Los subagentes ya reciben los CLAUDE.md: nombra solo la regla puntual que la etapa necesita. Todo resultado que el código consuma va con `schema`.
5. **`pipeline()` por defecto.** Barrera `parallel()` solo para dedup global, early-exit por conteo cero o un juez que necesita todos los resultados.
6. **Cierre:** el script hace `return cierre(resultado)`. Reporta al usuario el **Informe Ultra-Eco**: agentes por tier, escaladas, degradaciones T3→T2, tokens de salida (`budget.spent()`) y ahorro estimado vs. ultracode (`scripts/eco_costos.py --t1 .. --t2 .. --t3 .. --base <modelo de la sesión> --base-effort <esfuerzo de la sesión>`).

## 6. Preludio obligatorio (copiar literal justo después de `meta`)

```js
// ===== PRELUDIO KADI ULTRA-ECO v1.1 =====
const TIERS = Object.freeze({
  T1: Object.freeze({ model: 'sonnet', effort: 'xhigh' }),   // Peón
  T1m: Object.freeze({ model: 'sonnet', effort: 'medium' }), // Peón mecánico: correr comandos, parsear logs, contar
  T2: Object.freeze({ model: 'opus', effort: 'high' }),      // Capitán
  T3: Object.freeze({ model: 'fable', effort: 'high' }),     // Estratega
})
const RANGO = { sonnet: 1, opus: 2, fable: 3 }
const ARGS = (typeof args !== 'undefined' && args) || {}
const ECO = Object.assign({ t3Max: 3, techo: 'fable', maxFallosInfra: 3 }, ARGS.eco || {})
if (!RANGO[ECO.techo]) throw new Error('eco.techo inválido: ' + ECO.techo)
const ledger = { T1: 0, T1m: 0, T2: 0, T3: 0, escaladas: 0, degradadas: 0, reintentos: 0, fallosInfra: 0, sinResolver: [], abortado: false }
let nullsSeguidos = 0

// Guarda KADI: el worktree de escritura debe vivir en C:\KADI\.worktrees\<ID> o C:\KADI\wt\<ID>; nunca en C:\KADI\repos.
const WT = ARGS.worktree ? String(ARGS.worktree).replace(/\//g, '\\').replace(/\\+$/, '') : ''
if (WT && /^C:\\KADI\\/i.test(WT) && !/^C:\\KADI\\(\.worktrees|wt)\\[^\\]+$/i.test(WT)) {
  throw new Error('worktree KADI fuera de C:\\KADI\\.worktrees o C:\\KADI\\wt: ' + WT)
}
const CLAUSULA = '\n\nREGLAS KADI: C:\\KADI\\repos\\* es de SOLO LECTURA. Usa rutas absolutas' + (WT ? ' bajo ' + WT : '') +
  '. Si tu tarea es leer, revisar, buscar o verificar, NO edites ningún archivo.'
// Ruta relativa al worktree, con '/', en minúsculas (NTFS no distingue mayúsculas).
function normRuta(p) {
  let s = String(p).replace(/\\/g, '/').replace(/^\.\//, '')
  const base = WT.replace(/\\/g, '/').toLowerCase()
  if (base && s.toLowerCase().startsWith(base + '/')) s = s.slice(base.length + 1)
  return s.toLowerCase()
}

// Tier efectivo: aplica el techo de la sesión y la cuota de T3. Con estricto=true, T3 agotado devuelve null.
function resolver(tier, label, estricto) {
  if (!TIERS[tier]) throw new Error('tier inválido: ' + tier)
  let t = tier
  if (RANGO[TIERS[t].model] > RANGO[ECO.techo]) {
    t = ECO.techo === 'sonnet' ? 'T1' : 'T2'
    ledger.degradadas++
    log(`${tier} supera el techo de la sesión (${ECO.techo}) -> ${t}: ${label}`)
  }
  if (t === 'T3' && ledger.T3 >= ECO.t3Max) {
    if (estricto) return null
    t = 'T2'
    ledger.degradadas++
    log(`cuota T3 agotada (${ECO.t3Max}) -> T2: ${label}`)
  }
  return t
}

// Único punto que llama a agent(): impone model+effort y la cláusula KADI. Ante una caída (null) reintenta una
// vez en el MISMO tier; con maxFallosInfra caídas seguidas activa el cortacircuitos y no lanza más agentes.
async function run(tier, prompt, opts) {
  const o = opts || {}
  const label = o.label || 'agente'
  const t = resolver(tier, label, false)
  for (let intento = 0; intento < 2; intento++) {
    if (ledger.abortado) return null
    ledger[t]++
    const r = await agent(prompt + CLAUSULA, Object.assign({}, o, TIERS[t], { label: `${t}:${label}${intento ? ':reintento' : ''}` }))
    if (r !== null && r !== undefined) { nullsSeguidos = 0; return r }
    ledger.fallosInfra++
    nullsSeguidos++
    if (nullsSeguidos >= ECO.maxFallosInfra) {
      ledger.abortado = true
      log(`CORTACIRCUITOS: ${nullsSeguidos} agentes seguidos sin resultado (red o API caída); no se lanzan más agentes`)
      return null
    }
    if (intento === 0) { ledger.reintentos++; log(`sin resultado; reintento único en ${t}: ${label}`) }
  }
  return null
}
const t1 = (p, o) => run('T1', p, o)
const t1m = (p, o) => run('T1m', p, o)
const t2 = (p, o) => run('T2', p, o)
const t3 = (p, o) => run('T3', p, o)

// Escalada por etapas. accept(r) devuelve true o un string con el motivo del rechazo.
// Una caída de infraestructura (null) NO escala: se pagaría un tier superior por un fallo de red.
async function escalar(prompt, opts, accept, desde) {
  const orden = ['T1', 'T2', 'T3']
  const i = orden.indexOf(desde || 'T1')
  if (i < 0) throw new Error('tier inicial inválido: ' + desde)
  const o = opts || {}
  const label = o.label || 'agente'
  let previo = null
  let ultimo = null
  for (const pedido of orden.slice(i)) {
    const t = resolver(pedido, label, true)
    if (t === null || t === ultimo) {
      log(`sin tier superior disponible: ${label} vuelve al orquestador`)
      ledger.sinResolver.push(label)
      return null
    }
    ultimo = t
    const p = previo
      ? `${prompt}\n\nINTENTO PREVIO RECHAZADO (${previo.tier}): ${previo.motivo}\nEvalúa lo que dejó ese intento: conserva lo correcto, corrige o revierte el resto y no repitas el mismo enfoque.`
      : prompt
    const r0 = await run(t, p, o)
    if (r0 === null) { ledger.sinResolver.push(label); return null }
    const r = r0 && typeof r0 === 'object' ? r0 : { valor: r0 }
    let ok
    try { ok = accept(r) } catch (e) { ok = 'el criterio de aceptación lanzó: ' + (e && e.message) }
    if (ok === true) return Object.assign({}, r, { _tier: t })
    ledger.escaladas++
    previo = { tier: t, motivo: typeof ok === 'string' ? ok : 'no cumplió el criterio de aceptación' }
  }
  log(`escalada agotada sin aceptación: ${label}`)
  ledger.sinResolver.push(label)
  return null
}

// Verificación económica: ≥ 2 refutadores T1 con lentes distintas; juez T2 solo si se dividen o hay inconclusos.
// Los hallazgos críticos SIEMPRE pasan por un juez T3. sobrevive === null significa "sin decidir" (vuelve al orquestador).
const VEREDICTO = {
  type: 'object',
  properties: { refutado: { type: 'boolean' }, evidencia: { type: 'string' }, razon: { type: 'string' } },
  required: ['refutado', 'razon'],
}
async function verificar(afirmacion, opts) {
  const o = opts || {}
  const lentes = o.lentes && o.lentes.length >= 2 ? o.lentes : ['corrección', 'reproducibilidad']
  const base = o.label || 'verif'
  const votos = (await parallel(lentes.map(l => () => t1(
    `Intenta REFUTAR la afirmación con la lente "${l}". Compruébala en el código o en las fuentes y cita archivo:línea en "evidencia". refutado=true SOLO si encuentras evidencia en contra; si no puedes concluir, refutado=false y "razon" empieza por "inconcluso".\n\nAFIRMACIÓN:\n${afirmacion}`,
    { label: `${base}:${l}`, phase: o.phase, schema: VEREDICTO })))).filter(Boolean)
  const refutan = votos.filter(v => v.refutado).length
  const inconclusos = votos.filter(v => !v.refutado && /^inconcluso/i.test(v.razon || '')).length
  const unanime = votos.length === lentes.length && inconclusos === 0 && (refutan === 0 || refutan === votos.length)
  if (unanime && !o.critico) return { sobrevive: refutan === 0, votos, desempate: false }
  const juez = o.critico ? t3 : t2
  const d = await juez(
    `Decide la verificación. Votos previos: ${JSON.stringify(votos)}\nVerifícala tú mismo en el código o las fuentes; refutado=true solo con evidencia en contra.\n\nAFIRMACIÓN:\n${afirmacion}`,
    { label: `${base}:juez`, phase: o.phase, schema: VEREDICTO })
  return { sobrevive: d ? !d.refutado : null, votos: d ? votos.concat([d]) : votos, desempate: true }
}

function cierre(resultado) {
  return { resultado, ledger, tokensSalida: budget.spent() }
}
// ===== FIN PRELUDIO =====
```

Notas:
- `run()` es el único que llama a `agent()`. Antes de lanzar, comprueba que en el script la única aparición de `agent(` está dentro de `run()`.
- Pasa `args.worktree` (activa la guarda KADI y `normRuta`) y `args.eco.techo` = modelo de tu sesión cuando sea `sonnet` (con `opus` o `fable` deja el default `fable`: la matriz pide Fable como tier avanzado).
- Pasa `phase` en los opts dentro de `pipeline()`/`parallel()` para no depender del estado global de `phase()`.
- `ledger.sinResolver` y `sobrevive === null` vuelven al orquestador: nunca los descartes en silencio.
- En pipelines concurrentes, la degradación por cuota depende del orden de llegada; puede reducir los aciertos de caché al reanudar con `resumeFromRunId`. Es aceptable.

## 7. Recetas por fase

Scripts completos y listos para adaptar en `references/recetas.md`; léelo la primera vez que compongas cada tipo de fase en la sesión.

| Fase | Forma | Tiers |
|---|---|---|
| Understand | lectores por subsistema → mapa consolidado | N×T1 → 1×T2 |
| Design | panel de 2–3 enfoques con lentes distintas → juez que sintetiza | 2–3×T2 → 1×T3 |
| Implement | un escritor por territorio disjunto con `escalar()` → gate central → hasta 2 rondas de corrección → revisión | N×T1(→T2→T3) → 1×T1m gate → corrección T1 y luego T2 → 1×T2 review |
| Review | finders por dimensión → dedup en código → `verificar()` por hallazgo | N×T1 → 2×T1 por hallazgo (+T2 si división; T3 si crítico) |
| Research | barrido multimodal → lectura profunda → síntesis | N×T1 → N×T1 → 1×T2 (T3 si es estratégico) |
| Migrate | transformar sitio → verificar sitio → auditoría muestral | N×T1 → N×T1 → 1×T2 |
| Loop-until-dry | rondas de finders T1 hasta 2 rondas sin novedades | T1 + `verificar()` |

En escala L/XL, cierra con un **crítico de completitud** T2 ("¿qué modalidad no se corrió, qué fuente no se leyó, qué afirmación quedó sin verificar?"); lo que encuentre es la siguiente ronda.

## 8. Reglas KADI

- **Repos base de solo lectura:** ningún agente escribe en `C:\KADI\repos\*`. Antes de una fase Implement, el orquestador abre el ticket y crea el worktree con el harness; los escritores trabajan en `C:\KADI\.worktrees\<TICKET-ID>\`.
- **Sin `isolation: 'worktree'` dentro de KADI:** crea worktrees fuera del protocolo. Los escritores paralelos reciben territorios disjuntos (un dueño por archivo, validado en código con `normRuta`) dentro del worktree del ticket.
- **Escritores paralelos en un proyecto compartido** (Godot, bundlers, caches): los escritores NO corren la suite global ni el import, porque un archivo a medio escribir de otro territorio rompe el parseo. Un **gate central** T1m corre capas + import + suite al final de la ola, atribuye cada fallo a su WO y dispara rondas de corrección (ronda 1 en T1, ronda 2 en T2). Receta 3.
- **Locks con el kernel `kadi-swarm-orchestrator`:** el orquestador registra el escuadrón y publica contratos con `--model opus-5.5-xhigh` (el modelo Claude de su lista blanca de orquestador). Bajo lock escriben solo los T1 declarados como `sonnet-5.5-high` (lista blanca de subagentes); T2/T3 entregan diffs que aplica un T1.
- **Fuera de KADI:** `isolation: 'worktree'` solo para escritores paralelos que tocarían los mismos archivos (es caro).
- **Ola masiva por dueño de archivo** (validado en un proyecto interno, F23-F25): cuando el blueprint encadena olas solo por archivos hub compartidos, reparticiona por dueño único de archivo, congela los contratos entre particiones (señales, propiedades, firmas) en el prompt y lanza todas las particiones a la vez; la unidad de "sin referencias adelantadas" pasa a ser la ola. Cierra con una ola integral: gate → correcciones por dueño → auditoría T2 por partición + auditoría visual → remediación → gate → juez T3.
- **Corte por límite de sesión o de red:** el cortacircuitos detiene la ola; reanuda con `Workflow({scriptPath, resumeFromRunId})`: los agentes completados vuelven de caché sin costo y solo corre lo pendiente. Tras reanudar, comprueba que el gate posterior a la remediación sí se ejecutó (con `abortado` el script reutiliza el gate anterior).
- **Rendimiento con la máquina cargada:** un gate que corre mientras otros procesos renderizan puede dar falsos rojos de presupuesto (visto: 18.9 ms frente a 11.3 ms en reposo). Repite la medición antes de asignar una corrección de rendimiento.
- **Gates:** el cierre de cada fase Implement corre los gates del proyecto con un T1 (p. ej. `pwsh tools/ci.ps1`, `pwsh tools/check_layers.ps1`, `node C:\KADI\harness\bin\kadi.mjs gate check --ticket <ID>`) y devuelve la salida literal.
- **Contratos y ADR** (firmas congeladas, cambios de arquitectura): la decisión es siempre T3, y si toca un contrato congelado se emite `CONTRACT_CHANGE_REQUEST` en vez de editar.
- **Cierre del ciclo (cero residuos):** con gates verdes y aprobación del usuario, el orquestador ejecuta `kadi.mjs gate check --ticket <ID>`, `ticket close` y `worktree remove`. La entrega sigue el §12 del proyecto: archivos tocados, salida literal de los gates, checklist de aceptación, riesgos y entrada en `docs/CHANGELOG.md` (los escritores entregan el snippet y el orquestador lo integra).

## 9. Sin tool Workflow (fallback)

Si Workflow no está disponible, despacha con el tool Agent pasando `model` y `effort` por tier (`sonnet`/`xhigh`, `opus`/`high`, `fable`/`high`), con las llamadas independientes en un solo mensaje. Este skill pide explícitamente esos esfuerzos, lo que autoriza pasar `effort`. Rigen las mismas cuotas, la Ley Anti-Herencia y el Informe Ultra-Eco (llevas el ledger a mano).

## 10. Anti-patrones (prohibidos)

1. `agent()` o Agent sin `model`/`effort` (herencia = costo ultracode).
2. T3 para leer, buscar o escribir código rutinario.
3. `effort: 'max'` en subagentes: solo el orquestador puede ir a max, porque lo eligió el usuario.
4. Barreras `parallel()` entre etapas sin dependencia cruzada.
5. Tres o más verificadores idénticos de tier alto por hallazgo (usa `verificar()`).
6. Volcar archivos completos en los prompts (pasa rutas).
7. El orquestador leyendo archivos que un T1 va a leer (doble gasto).
8. Recortar cobertura (top-N, muestreo, sin reintento) sin registrarlo con `log()`.
9. `Date.now()`, `Math.random()` o `new Date()` sin argumentos en scripts (rompen el resume).
10. Escalar de tier ante una caída de red o API (`null`): se reintenta una vez en el mismo tier y, si persiste, salta el cortacircuitos. Incidente real del 2026-10-25: 13 agentes escalados de T1 a T3 por un ENOTFOUND quemaron 613k tokens sin producir nada.
11. Revisar solo con `git diff`: no muestra archivos nuevos. Usa `git status --porcelain` + `git diff HEAD` y lee completos los archivos sin trackear.
12. Aceptar o rechazar por un campo de texto libre (p. ej. `bloqueos` no vacío). Los agentes meten riesgos ahí ("Sin bloqueos. Riesgo 1…") y provocan escaladas falsas: un T2 que ya había bajado el render de 25.6 a 10.07 ms fue rechazado así. Decide por campos tipados (`bloqueado: boolean`, métricas numéricas) y deja los riesgos en su propio campo.

## 11. Calibración y costos

- El ahorro real no es el cociente de precios: Sonnet en xhigh puede gastar más tokens que Opus en high. Tras 2 o 3 workflows, compara `tokensSalida` por tipo de tarea y reajusta el enrutador.
- Antes de una cascada larga, prueba la alternativa simple: un solo tier más capaz con menos esfuerzo puede salir más barato por tarea completada.
- Estimador (Python, solo librería estándar, salida JSON):

```powershell
python "%USERPROFILE%\.claude\skills\kadi-ultra-eco\scripts\eco_costos.py" --t1 30 --t2 8 --t3 2 --base opus --base-effort xhigh
```

  Parámetros: `--in-tok`/`--out-tok` (tokens medios por agente), `--cache-hit` (fracción de la entrada leída de caché), `--base`/`--base-effort` (lo que heredaría ultracode). Los multiplicadores de esfuerzo son supuestos calibrables (`--mult-*`); el informe lo indica.
