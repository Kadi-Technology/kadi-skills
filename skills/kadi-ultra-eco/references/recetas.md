# Recetas Ultra-Eco por fase

Cada receta es un script completo. Donde dice `/* PRELUDIO */` pega literal el preludio de `SKILL.md` §6. Ajusta prompts, schemas y la work-list (`args`) a la tarea; conserva la asignación de tiers salvo motivo registrado con `log()`.

Convención de `args`: la work-list descubierta por el scout inline se pasa como JSON real en el parámetro `args` del tool Workflow (nunca como string JSON).

---

## 1. Understand — mapa de un sistema

N lectores T1 (uno por subsistema) en paralelo → un T2 consolida. Barrera justificada: el consolidador necesita todos los mapas.

```js
export const meta = {
  name: 'eco-understand',
  description: 'Mapa del sistema con lectores T1 y consolidación T2',
  phases: [{ title: 'Leer' }, { title: 'Consolidar' }],
}
/* PRELUDIO */
const MAPA = {
  type: 'object',
  properties: {
    subsistema: { type: 'string' },
    archivos_clave: { type: 'array', items: { type: 'string' } },
    responsabilidades: { type: 'array', items: { type: 'string' } },
    dependencias: { type: 'array', items: { type: 'string' } },
    contratos_publicos: { type: 'array', items: { type: 'string' } },
    riesgos: { type: 'array', items: { type: 'string' } },
  },
  required: ['subsistema', 'archivos_clave', 'responsabilidades', 'dependencias'],
}
const subsistemas = args.subsistemas // [{ nombre, rutas: [...] }]
const mapas = (await parallel(subsistemas.map(s => () => t1(
  `Mapea el subsistema "${s.nombre}" (rutas: ${s.rutas.join(', ')}). Lee lo necesario para describir qué hace, sus archivos clave, sus dependencias hacia otros subsistemas y sus firmas públicas. Cita archivo:línea. No propongas cambios.`,
  { label: `leer:${s.nombre}`, phase: 'Leer', schema: MAPA })))).filter(Boolean)
log(`${mapas.length}/${subsistemas.length} subsistemas mapeados`)
if (!mapas.length) { log('ningún lector respondió; no se lanza el consolidador T2'); return cierre({ mapas, consolidado: null }) }
const consolidado = await t2(
  `Consolida estos mapas en un único mapa del sistema: capas, flujo de datos, puntos de acoplamiento, contradicciones entre mapas y huecos (qué no quedó cubierto).\n\n${JSON.stringify(mapas)}`,
  { label: 'consolidar', phase: 'Consolidar' })
return cierre({ mapas, consolidado })
```

---

## 2. Design — panel de enfoques y juez

2 o 3 diseñadores T2 con lentes distintas → un juez T3 puntúa y sintetiza (gana uno, se injertan las mejores ideas del resto).

```js
export const meta = {
  name: 'eco-design',
  description: 'Panel de diseño T2 con juez T3',
  phases: [{ title: 'Proponer' }, { title: 'Juzgar' }],
}
/* PRELUDIO */
const PROPUESTA = {
  type: 'object',
  properties: {
    enfoque: { type: 'string' },
    resumen: { type: 'string' },
    archivos_a_tocar: { type: 'array', items: { type: 'string' } },
    pasos: { type: 'array', items: { type: 'string' } },
    riesgos: { type: 'array', items: { type: 'string' } },
    costo_relativo: { type: 'string' },
  },
  required: ['enfoque', 'resumen', 'archivos_a_tocar', 'pasos', 'riesgos'],
}
const LENTES = ['MVP primero: lo mínimo que cumple', 'riesgo primero: lo que no puede romperse', 'evolución: lo que escala a la siguiente ola']
const contexto = typeof ARGS.contexto === 'string' ? ARGS.contexto : JSON.stringify(ARGS.contexto) // requisito + mapa de Understand
const propuestas = (await parallel(LENTES.map((l, i) => () => t2(
  `Diseña una solución con la lente "${l}".\n\nCONTEXTO:\n${contexto}\n\nRespeta los contratos congelados; si alguno no alcanza, dilo en riesgos como CONTRACT_CHANGE_REQUEST.`,
  { label: `propuesta:${i + 1}`, phase: 'Proponer', schema: PROPUESTA })))).filter(Boolean)
const veredicto = await t3(
  `Eres el juez. Puntúa cada propuesta (0-10) en corrección, riesgo, costo y encaje con los contratos. Elige una ganadora y produce el plan final injertando las mejores ideas de las otras. Lista explícitamente lo descartado y por qué.\n\nPROPUESTAS:\n${JSON.stringify(propuestas)}`,
  { label: 'juez', phase: 'Juzgar' })
return cierre({ propuestas, veredicto })
```

---

## 3. Implement — escritores por territorio con escalada

Un escritor por territorio disjunto. `escalar()` sube de tier si la autocomprobación falla. Después, gates con un T1 y revisión T2 del diff completo. Pipeline: cada territorio avanza sin esperar a los demás.

Patrón validado en un proyecto interno, F22: los escritores NO corren la suite global (un territorio a medio escribir rompe el parseo del proyecto compartido); un **gate central T1m** corre capas + import + suite, atribuye cada fallo a su WO y dispara hasta 2 rondas de corrección (T1 y luego T2). Barrera justificada: el gate necesita todos los territorios escritos. `args = { worktree, territorios: [{ id, archivos, spec }], gates: [comandos] }`.

```js
export const meta = {
  name: 'eco-implement',
  description: 'Escritores T1 con escalada, gate central T1m, correcciones escaladas y revisión T2',
  phases: [{ title: 'Escribir' }, { title: 'Gates' }, { title: 'Corregir' }, { title: 'Revisar' }],
}
/* PRELUDIO */
const ENTREGA = {
  type: 'object',
  properties: {
    archivos_tocados: { type: 'array', items: { type: 'string' } },
    resumen: { type: 'string' },
    autocomprobacion: { type: 'string' },
    confianza: { type: 'number' },
    bloqueos: { type: 'array', items: { type: 'string' } },
    contract_change_request: { type: 'string' },
    changelog: { type: 'string' },
  },
  required: ['archivos_tocados', 'resumen', 'autocomprobacion', 'confianza', 'bloqueos', 'changelog'],
}
const { territorios, gates } = ARGS
const dueño = new Map()
for (const t of territorios) for (const f of t.archivos) {
  const k = normRuta(f)
  if (dueño.has(k)) throw new Error(`archivo en dos territorios: ${f} (${dueño.get(k)} y ${t.id})`)
  dueño.set(k, t.id)
}
const aceptar = t => {
  const propios = new Set(t.archivos.map(normRuta))
  return r => {
    if (r.contract_change_request && String(r.contract_change_request).trim()) return true // lo decide el orquestador
    if (Array.isArray(r.bloqueos) && r.bloqueos.length) return `bloqueos: ${r.bloqueos.join('; ')}`
    if (typeof r.confianza !== 'number' || r.confianza < 0.7) return `confianza baja (${r.confianza})`
    if (!Array.isArray(r.archivos_tocados) || !r.archivos_tocados.length) return 'no reportó archivos_tocados'
    const fuera = r.archivos_tocados.map(normRuta).filter(f => !propios.has(f) && !f.endsWith('.uid'))
    if (fuera.length) return `tocó archivos fuera de su territorio: ${fuera.join(', ')}; revierte esos cambios`
    return true
  }
}
const escritor = t => `Trabaja SOLO en ${WT}. Implementa:\n${t.spec}\n\nSolo puedes editar: ${t.archivos.join(', ')}. NO corras la suite global, el import ni el motor: otros territorios se escriben en paralelo y un gate central correrá todo al final. Revisa tu código como lo haría el parser y verifica con grep cada API que uses. Si la spec o un contrato no alcanza, no improvises: decláralo en bloqueos o contract_change_request. Reporta archivos_tocados con rutas relativas al worktree.`
const entregas = await parallel(territorios.map(t => () =>
  escalar(escritor(t), { label: `escribir:${t.id}`, phase: 'Escribir', schema: ENTREGA }, aceptar(t))))
log(`${entregas.filter(Boolean).length}/${territorios.length} territorios aceptados; sin resolver: ${ledger.sinResolver.join(', ') || 'ninguno'}`)

const GATE = {
  type: 'object',
  properties: {
    verde: { type: 'boolean' },
    resumen: { type: 'string' },
    fallos: { type: 'array', items: { type: 'object', properties: { territorio: { type: 'string' }, archivo: { type: 'string' }, error: { type: 'string' } }, required: ['territorio', 'archivo', 'error'] } },
    fuera_de_frontera: { type: 'array', items: { type: 'string' } },
    salida_clave: { type: 'string' },
  },
  required: ['verde', 'resumen', 'fallos', 'fuera_de_frontera', 'salida_clave'],
}
const MAPA = territorios.map(t => `${t.id}: ${t.archivos.join(', ')}`).join('\n')
const gate = n => t1m(`GATE ${n}. En ${WT}, ejecuta en orden y captura salida y exit code de cada uno:\n${gates.join('\n')}\nDespués compara git status --porcelain contra este mapa y lista en fuera_de_frontera lo que no esté en él (los .uid de archivos nuevos del mapa están permitidos):\n${MAPA}\nAtribuye cada fallo a un territorio por la ruta (o "desconocido"). salida_clave: líneas de error literales (máx. ~60) y el resumen final. No edites nada.`,
  { label: `gate-${n}`, phase: 'Gates', schema: GATE })
const verdeDe = g => !!(g && g.verde && !g.fuera_de_frontera.length)
let g = ledger.abortado ? null : await gate(1)
const historial = [g]
for (let ronda = 1; ronda <= 2 && g && !verdeDe(g) && !ledger.abortado; ronda++) {
  const porT = territorios.map(t => ({ t, fallos: g.fallos.filter(f => f.territorio === t.id) })).filter(x => x.fallos.length)
  if (!porT.length) { log('fallos sin atribuir: vuelve al orquestador'); break }
  await parallel(porT.map(x => () => run(ronda === 1 ? 'T1' : 'T2',
    `${escritor(x.t)}\n\nCORRECCIÓN ronda ${ronda}. El gate falló con:\n${JSON.stringify(x.fallos)}\n\n${g.salida_clave}\n\nCorrige la causa raíz; no silencies tests.`,
    { label: `corregir${ronda}:${x.t.id}`, phase: 'Corregir', schema: ENTREGA })))
  g = await gate(ronda + 1)
  historial.push(g)
}
const revision = verdeDe(g) ? await t2(
  `Revisa los cambios de ${WT}: git status --porcelain y git diff HEAD, y lee completos los archivos nuevos sin trackear (git diff no los muestra). Contrasta con las specs y las reglas del proyecto. Devuelve, por territorio, si cumple su aceptación, y solo defectos reales con archivo:línea, severidad y arreglo.\n\nSPECS:\n${JSON.stringify(territorios.map(t => ({ id: t.id, spec: t.spec })))}`,
  { label: 'revisar', phase: 'Revisar' }) : null
return cierre({ entregas, gates: historial, verde: verdeDe(g), revision })
```

---

## 4. Review — finders, dedup y verificación económica

Finders T1 por dimensión → dedup en código (barrera justificada) → `verificar()` por hallazgo: 2 refutadores T1, desempate T2 solo si se dividen, T3 si la severidad es crítica.

```js
export const meta = {
  name: 'eco-review',
  description: 'Revisión por dimensiones con verificación adversarial económica',
  phases: [{ title: 'Buscar' }, { title: 'Verificar' }],
}
/* PRELUDIO */
const HALLAZGOS = {
  type: 'object',
  properties: {
    hallazgos: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          archivo: { type: 'string' },
          linea: { type: 'number' },
          severidad: { type: 'string', enum: ['critica', 'alta', 'media', 'baja'] },
          descripcion: { type: 'string' },
          escenario: { type: 'string' },
        },
        required: ['archivo', 'linea', 'severidad', 'descripcion', 'escenario'],
      },
    },
  },
  required: ['hallazgos'],
}
const DIMENSIONES = ['corrección y lógica', 'concurrencia y estado de red', 'contratos y capas', 'manejo de errores y casos límite', 'tests faltantes']
const alcance = args.alcance // archivos o diff a revisar
const crudos = (await parallel(DIMENSIONES.map(d => () => t1(
  `Revisa ${alcance} SOLO en la dimensión "${d}". Reporta hallazgos concretos con archivo:línea y un escenario que falle. Nada especulativo.`,
  { label: `buscar:${d}`, phase: 'Buscar', schema: HALLAZGOS })))).filter(Boolean).flatMap(r => r.hallazgos)
// Dedup por archivo:línea conservando la severidad máxima y registrando las fusiones.
const SEV = { critica: 3, alta: 2, media: 1, baja: 0 }
const porClave = new Map()
for (const h of crudos) {
  const k = `${normRuta(h.archivo)}:${h.linea}`
  const prev = porClave.get(k)
  if (!prev) { porClave.set(k, Object.assign({}, h, { fusionados: [] })); continue }
  prev.fusionados.push(`[${h.severidad}] ${h.descripcion}`)
  if (SEV[h.severidad] > SEV[prev.severidad]) Object.assign(prev, { severidad: h.severidad, descripcion: h.descripcion, escenario: h.escenario })
}
const unicos = [...porClave.values()]
log(`${crudos.length} hallazgos crudos, ${unicos.length} únicos, ${unicos.filter(u => u.fusionados.length).length} con fusiones`)
if (!unicos.length) return cierre({ confirmados: [] })
const juzgados = (await parallel(unicos.map((h, i) => () =>
  verificar(`${h.archivo}:${h.linea} [${h.severidad}] ${h.descripcion}\nEscenario: ${h.escenario}${h.fusionados.length ? '\nTambién reportado: ' + h.fusionados.join(' | ') : ''}`,
    { label: `h${i + 1}`, phase: 'Verificar', critico: h.severidad === 'critica' })
    .then(v => Object.assign({}, h, { veredicto: v }))))).filter(Boolean)
const confirmados = juzgados.filter(h => h.veredicto.sobrevive === true)
const pendientes = juzgados.filter(h => h.veredicto.sobrevive === null) // sin decidir: los revisa el orquestador
return cierre({ confirmados, pendientes, descartados: juzgados.length - confirmados.length - pendientes.length })
```

---

## 5. Research — barrido multimodal y síntesis

Buscadores T1 con modalidades distintas (cada uno ciego a lo que encuentran los otros) → lectores profundos T1 por fuente → síntesis T2 (T3 si `args.estrategico`).

```js
export const meta = {
  name: 'eco-research',
  description: 'Barrido multimodal T1, lectura profunda T1, síntesis T2/T3',
  phases: [{ title: 'Barrer' }, { title: 'Leer' }, { title: 'Sintetizar' }],
}
/* PRELUDIO */
const FUENTES = {
  type: 'object',
  properties: { fuentes: { type: 'array', items: { type: 'object', properties: { ref: { type: 'string' }, por_que: { type: 'string' } }, required: ['ref', 'por_que'] } } },
  required: ['fuentes'],
}
const MODALIDADES = ['por contenedor (directorios y módulos)', 'por contenido (grep de términos y símbolos)', 'por entidad (tipos, clases, contratos)', 'por tiempo (git log y cambios recientes)']
const pregunta = args.pregunta
const listas = (await parallel(MODALIDADES.map(m => () => t1(
  `Pregunta: ${pregunta}\nBusca fuentes relevantes SOLO ${m}. Devuelve referencias (ruta, símbolo, commit o URL) y por qué importan. No las resumas aún.`,
  { label: `barrer:${m.split(' ')[1]}`, phase: 'Barrer', schema: FUENTES })))).filter(Boolean)
const refs = [...new Set(listas.flatMap(l => l.fuentes.map(f => f.ref)))]
const TOPE = (args.eco && args.eco.maxFuentes) || 24
if (refs.length > TOPE) log(`recortadas ${refs.length - TOPE} fuentes por tope ${TOPE}: ${refs.slice(TOPE).join(', ')}`)
const lecturas = await pipeline(refs.slice(0, TOPE), r => t1(
  `Lee a fondo ${r} y extrae solo lo que responde a: ${pregunta}. Cita líneas. Marca qué es hecho verificado y qué es inferencia.`,
  { label: `leer:${r}`, phase: 'Leer' }))
const sintetizar = args.estrategico ? t3 : t2
const sintesis = await sintetizar(
  `Sintetiza una respuesta a: ${pregunta}\nUsa solo las lecturas; señala contradicciones y lo que sigue sin respuesta.\n\n${JSON.stringify(lecturas.filter(Boolean))}`,
  { label: 'sintesis', phase: 'Sintetizar' })
return cierre({ refs, sintesis })
```

---

## 6. Migrate — transformar, verificar y auditar por muestra

Por sitio: transformación T1 → verificación T1 independiente. Al final, un T2 audita una muestra determinista (cada k-ésimo sitio) y todos los rechazados.

```js
export const meta = {
  name: 'eco-migrate',
  description: 'Migración por sitio con verificación T1 y auditoría muestral T2',
  phases: [{ title: 'Transformar' }, { title: 'Verificar' }, { title: 'Auditar' }],
}
/* PRELUDIO */
const RES = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, detalle: { type: 'string' } },
  required: ['ok', 'detalle'],
}
const { worktree, sitios, regla } = args // sitios: [{ archivo, simbolo }]
const resultados = await pipeline(
  sitios,
  s => t1(`En ${worktree}, aplica la regla de migración a ${s.archivo} (${s.simbolo}). Toca solo ese sitio.\nREGLA:\n${regla}`,
    { label: `transformar:${s.archivo}`, phase: 'Transformar', schema: RES }),
  (r, s) => (!r || !r.ok)
    ? { sitio: s, transformacion: r, verificacion: null } // no se paga un verificador para un sitio no transformado
    : t1(`Verifica de forma independiente que ${s.archivo} (${s.simbolo}) en ${worktree} cumple la regla y compila. No edites nada.\nREGLA:\n${regla}`,
      { label: `verificar:${s.archivo}`, phase: 'Verificar', schema: RES })
      .then(v => ({ sitio: s, transformacion: r, verificacion: v })),
)
// Conserva la identidad del sitio aunque una etapa haya lanzado (pipeline deja null).
const rechazados = resultados
  .map((x, i) => x || { sitio: sitios[i], transformacion: null, verificacion: null })
  .filter(x => !x.verificacion || !x.verificacion.ok)
const K = 5
const muestra = resultados.filter((x, i) => x && i % K === 0)
log(`${rechazados.length} rechazados; auditoría muestral de ${muestra.length} sitios (1 de cada ${K})`)
const auditoria = await t2(
  `Audita esta muestra y todos los rechazados. ¿La regla se aplicó de forma consistente? ¿Hay un patrón de fallo que exija cambiar la regla?\n\nMUESTRA:\n${JSON.stringify(muestra)}\n\nRECHAZADOS:\n${JSON.stringify(rechazados)}`,
  { label: 'auditar', phase: 'Auditar' })
return cierre({ total: sitios.length, rechazados: rechazados.length, auditoria })
```

---

## 7. Loop-until-dry — descubrimiento de tamaño desconocido

Rondas de finders T1 hasta 2 rondas seguidas sin novedades; dedup contra todo lo visto (no solo contra lo confirmado, o no converge).

```js
export const meta = {
  name: 'eco-until-dry',
  description: 'Descubrimiento por rondas T1 hasta agotar novedades',
  phases: [{ title: 'Buscar' }, { title: 'Verificar' }],
}
/* PRELUDIO */
const ITEMS = {
  type: 'object',
  properties: { items: { type: 'array', items: { type: 'object', properties: { clave: { type: 'string' }, descripcion: { type: 'string' } }, required: ['clave', 'descripcion'] } } },
  required: ['items'],
}
const ANGULOS = ['casos límite de entrada', 'rutas de error', 'estado compartido']
const objetivo = args.objetivo
const vistos = new Set()
const confirmados = []
let secas = 0
let ronda = 0
let rondasFallidas = 0
while (secas < 2 && ronda < 6 && !ledger.abortado) {
  ronda++
  const respuestas = (await parallel(ANGULOS.map(a => () => t1(
    `Ronda ${ronda}. ${objetivo}\nÁngulo: ${a}. Ya conocidos (no los repitas): ${[...vistos].join(' | ') || 'ninguno'}`,
    { label: `r${ronda}:${a}`, phase: 'Buscar', schema: ITEMS })))).filter(Boolean)
  // Una ronda donde murió la mayoría de los finders no cuenta como "seca".
  if (respuestas.length < Math.ceil(ANGULOS.length / 2)) {
    rondasFallidas++
    log(`ronda ${ronda}: solo ${respuestas.length}/${ANGULOS.length} finders respondieron; no cuenta como seca`)
    if (rondasFallidas >= 2) { log('dos rondas fallidas: se detiene con cobertura incompleta'); break }
    continue
  }
  const nuevos = []
  for (const x of respuestas.flatMap(r => r.items)) {
    const k = String(x.clave).trim().toLowerCase()
    if (vistos.has(k)) continue
    vistos.add(k) // dedup también dentro de la ronda
    nuevos.push(x)
  }
  if (!nuevos.length) { secas++; continue }
  secas = 0
  const v = await parallel(nuevos.map((x, i) => () =>
    verificar(`${x.clave}: ${x.descripcion}`, { label: `r${ronda}-${i + 1}`, phase: 'Verificar' }).then(r => ({ x, r }))))
  confirmados.push(...v.filter(Boolean).filter(y => y.r.sobrevive).map(y => y.x))
  log(`ronda ${ronda}: ${nuevos.length} nuevos, ${confirmados.length} confirmados en total`)
}
if (ronda >= 6 && secas < 2) log('tope de 6 rondas alcanzado sin secarse: la cobertura puede estar incompleta')
return cierre({ confirmados, rondas: ronda })
```
