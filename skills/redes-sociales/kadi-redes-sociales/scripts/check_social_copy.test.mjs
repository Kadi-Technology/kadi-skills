import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { buildRuleSet, lintText, resolveHostSync } from './check_social_copy.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CLI = path.join(HERE, 'check_social_copy.mjs');
// DNS determinista: por defecto ningun host de demo resuelve (como el 2026-10-21).
process.env.KADI_DNS_OVERRIDE = '{}';
const ruleSet = buildRuleSet();
const U = 'https://kadi.technology/contacto/?utm_source=instagram&utm_medium=organic_social&utm_campaign=founders_cohort01';

function rulesFor(text) {
  return lintText(text, { file: 'caso.md', ruleSet }).map((f) => f.rule);
}

test('carga las reglas de claims R1 y R2 del portal y agrega las propias', () => {
  const ids = ruleSet.rules.map((r) => r.id);
  assert.ok(ids.some((i) => i.startsWith('R1_')), 'faltan reglas R1');
  assert.ok(ids.some((i) => i.startsWith('R2_')), 'faltan reglas R2');
  assert.ok(ids.some((i) => i.startsWith('KADI_')), 'faltan reglas KADI');
  assert.ok(ruleSet.rules.length >= 30);
});

const mustFail = [
  ['R1: absolutos de seguridad', 'Nuestro sistema es 100 % seguro.', 'R1_ABSOLUTE_SECURITY'],
  ['R2: superlativo lider', 'Somos lider en software veterinario.', 'R2_SUPERLATIVE_LEADER'],
  ['R2: promesa cero', 'Cero errores en tu clinica.', 'R2_PROMISE_ZERO'],
  ['R2: nube', 'Todo vive en la nube.', 'R2_CAPABILITY_CLOUD'],
  ['KADI: inhackeable', 'Un expediente inhackeable.', 'KADI_ABSOLUTE_ADJECTIVE'],
  ['KADI: primera del mundo', 'La primera clinica del mundo con visor 3D.', 'KADI_ABSOLUTE_ADJECTIVE'],
  ['KADI: certificacion inventada', 'Cumplimos ISO 27001.', 'KADI_UNVERIFIED_CERTIFICATION'],
  ['KADI: 11 sistemas', 'KADI tiene 11 sistemas conectados.', 'KADI_CANON_COUNT'],
  ['KADI: once sistemas', 'Arquitectura de once sistemas.', 'KADI_CANON_COUNT'],
  ['KADI: 14 sistemas sin anatomia', 'Un portafolio de 14 sistemas.', 'KADI_CANON_COUNT'],
  ['KADI: host de produccion', 'Mira https://prod-cliente.kadi.technology/ ahora.', 'KADI_FORBIDDEN_HOST'],
  ['KADI: host de academia', 'Entra a academia-privada.kadi.technology.', 'KADI_FORBIDDEN_HOST'],
  ['KADI: IP prohibida', 'Servidor 203.0.113.50.', 'KADI_FORBIDDEN_IP'],
  ['KADI: IP prohibida 2', 'Servidor 203.0.113.51.', 'KADI_FORBIDDEN_IP'],
  ['KADI: host sin DNS', 'Prueba demo-privada.kadi.technology.', 'KADI_NONPUBLIC_HOST'],
  ['KADI: cliente real', 'Gracias a Cliente Ejemplo.', 'KADI_PROHIBITED_CLIENT'],
  ['KADI: resenador', 'Opina Nombre R. en la resena.', 'KADI_PII_REVIEWER_NAME'],
  ['KADI: 3 clics', 'La Urgencia Express en 3 clics.', 'KADI_URGENCIA_3_CLICS'],
  ['KADI: tres clics', 'Pre-admision en tres clics.', 'KADI_URGENCIA_3_CLICS'],
  ['KADI: visor solo perro y gato', 'El visor 3D del portal cubre solo perro y gato.', 'KADI_VISOR_SOLO_PERRO_GATO'],
  ['KADI: visor únicamente perro y gato', 'El visor del portal ofrece únicamente perro y gato con 14 sistemas.', 'KADI_VISOR_SOLO_PERRO_GATO'],
  ['KADI: solo perro y gato antes del visor', 'Solo perro y gato: así es el visor 3D.', 'KADI_VISOR_SOLO_PERRO_GATO'],
  ['KADI: UTM ausente', 'Visita https://kadi.technology/contacto/ hoy.', 'KADI_UTM_MISSING'],
  ['KADI: UTM incompleto', 'Visita https://portal-cliente.kadi.technology/?utm_source=instagram&utm_medium=organic_social hoy.', 'KADI_UTM_MISSING'],
  ['KADI: dominio sin esquema ni UTM', 'Escribe a kadi.technology/contacto para mas.', 'KADI_UTM_MISSING'],
  ['KADI: medio incorrecto', 'https://kadi.technology/?utm_source=tiktok&utm_medium=organic_social&utm_campaign=founders_cohort01', 'KADI_UTM_SCHEME'],
  ['KADI: campana sin snake_case', 'https://kadi.technology/?utm_source=linkedin&utm_medium=organic_social&utm_campaign=Founders-Cohort01', 'KADI_UTM_SCHEME'],
  ['KADI: enlace fuera del canon', 'Mas informacion en https://ejemplo.com/pagina', 'KADI_LINK_NOT_CANONICAL'],
  ['KADI: plaza #011', 'Plazas #011 y #012 abiertas.', 'KADI_FOUNDERS_PLAZA'],
  ['KADI: plaza #1', 'Founders #1 asignada.', 'KADI_FOUNDERS_PLAZA'],
  ['KADI: cantidad de plazas', 'Quedan 5 plazas para clinicas.', 'KADI_FOUNDERS_PLAZA'],
  ['KADI: escasez inventada', 'Ultimas plazas disponibles.', 'KADI_FOUNDERS_SCARCITY'],
  ['KADI: privilegio contractual', 'Tarifa congelada para fundadores.', 'KADI_FOUNDERS_LIFETIME_PROMISE'],
  ['KADI: Three.js afirmativo', 'El visor esta hecho con Three.js.', 'KADI_THREEJS_AFFIRMATIVE'],
  ['KADI: Gladys diagnostica', 'Gladys diagnostica por ti.', 'KADI_GLADYS_OVERCLAIM'],
  ['KADI: etapa inflada', 'Contract ERP ya disponible para todos.', 'KADI_STAGE_OVERCLAIM'],
  ['KADI: telefono de la clinica', 'Llama al 55 8347 4800.', 'KADI_CLINIC_PHONE'],
  ['KADI: buzon sin confirmar', 'Escribe a ventas@example.com', 'KADI_UNCONFIRMED_MAILBOX'],
  ['KADI: correo personal', 'Escribeme a alguien@gmail.com', 'KADI_PII_EMAIL'],
  ['KADI: placeholder', 'Titulo TODO cambiar.', 'KADI_PLACEHOLDER'],
  ['KADI: AES en respaldos', 'Tus respaldos cifrados con AES-256-GCM.', 'KADI_AES_BACKUPS'],
  ['KADI: AES en respaldos (orden inverso)', 'AES-256-GCM protege los respaldos de la clinica.', 'KADI_AES_BACKUPS'],
  ['KADI: CFDI', 'Emite CFDI desde el sistema.', 'KADI_CFDI'],
  ['KADI: timbrado', 'Con timbrado incluido.', 'KADI_CFDI'],
  ['KADI: enlace a demo-privada sin DNS', 'Prueba https://demo-privada.kadi.technology/?utm_source=instagram&utm_medium=organic_social&utm_campaign=demo', 'KADI_NONPUBLIC_HOST'],
  ['KADI: demasiados hashtags', '#a1 #b2 #c3 #d4 #e5 #f6 #g7', 'KADI_HASHTAGS_EXCESS'],
];

for (const [name, text, rule] of mustFail) {
  test(`debe fallar: ${name}`, () => {
    assert.ok(rulesFor(text).includes(rule), `se esperaba ${rule}, se obtuvo ${rulesFor(text).join(',') || 'nada'}`);
  });
}

const mustPass = [
  ['canon 10 mas 2', 'KADI Technology reune 10 sistemas principales y 2 módulos clínicos vinculados.'],
  ['visor con 14 sistemas anatomicos', 'El visor 3D ofrece cuatro especies (canino, felino, conejo y ave) y 14 sistemas anatómicos.'],
  ['visor con 4 especies ya no es hallazgo', 'Visor 3D de 4 especies.'],
  ['vinculacion clinica de KADI SCV con perro y gato', 'En KADI SCV la vinculación clínica del atlas con el expediente cubre perro y gato.'],
  ['plazas del canon', 'Cohorte KADI Founders #01: #001 asignada y plazas #002 a #010 abiertas. Son 10 plazas.'],
  ['enlace UTM completo', `Conoce la cohorte: ${U}`],
  ['enlace UTM de youtube horizontal', 'https://portal-cliente.kadi.technology/?utm_source=youtube&utm_medium=video_horizontal&utm_campaign=visor3d_cliente'],
  ['whatsapp y agenda canonicos', 'https://wa.me/5210000000000 y https://calendar.app.google/ID_AGENDA_EJEMPLO'],
  ['uno clic', 'La pre-admisión express se hace en 1 clic desde el portal.'],
  ['Gladys con gobernanza humana', 'Gladys sugiere y estructura; la decisión clínica es del médico veterinario. Gladys no diagnostica.'],
  ['etapa honesta', 'Contract ERP está en desarrollo y no tiene fecha de lanzamiento.'],
  ['evidencia del harvester: AES-256-GCM y 96 bits', 'La demo usa WebCrypto con AES-256-GCM y un IV de 96 bits.'],
  ['sin Three.js verificado', 'El visor está escrito en WebGL puro, sin Three.js.'],
  ['hashtags moderados', '#KADI #VisorAnatomico3D #SoftwareVeterinario'],
  ['color hexadecimal no es plaza', 'El color es #0F1F1A en el diseño.'],
  ['Acta Cero es un nombre de proyecto', 'Réquiem: Acta Cero es un juego táctico en desarrollo.'],
];

for (const [name, text] of mustPass) {
  test(`debe pasar: ${name}`, () => {
    const found = rulesFor(text);
    assert.deepEqual(found, [], `hallazgos inesperados: ${found.join(',')}`);
  });
}

test('DNS en tiempo de ejecucion: demo-privada que resuelve a una IP no prohibida deja de ser hallazgo, pero exige UTM', () => {
  process.env.KADI_DNS_OVERRIDE = JSON.stringify({ 'demo-privada.kadi.technology': ['203.0.113.10'] });
  try {
    const rs = buildRuleSet();
    const conUtm = 'https://demo-privada.kadi.technology/?utm_source=instagram&utm_medium=organic_social&utm_campaign=demo_scv';
    assert.deepEqual(lintText(`Prueba ${conUtm}`, { file: 'a.md', ruleSet: rs }).map((f) => f.rule), []);
    const sinUtm = lintText('Prueba https://demo-privada.kadi.technology/ hoy', { file: 'a.md', ruleSet: rs }).map((f) => f.rule);
    assert.ok(sinUtm.includes('KADI_UTM_MISSING'), sinUtm.join(','));
  } finally {
    process.env.KADI_DNS_OVERRIDE = '{}';
  }
});

test('DNS en tiempo de ejecucion: si resuelve a una IP prohibida sigue siendo hallazgo', () => {
  process.env.KADI_DNS_OVERRIDE = JSON.stringify({ 'demo-privada.kadi.technology': ['203.0.113.51'] });
  try {
    const rs = buildRuleSet();
    assert.ok(lintText('Visita demo-privada.kadi.technology', { file: 'a.md', ruleSet: rs }).some((f) => f.rule === 'KADI_NONPUBLIC_HOST'));
  } finally {
    process.env.KADI_DNS_OVERRIDE = '{}';
  }
});

test('prod-cliente y academia-privada nunca se consideran publicos aunque la resolucion DNS los devuelva', () => {
  process.env.KADI_DNS_OVERRIDE = JSON.stringify({ 'prod-cliente.kadi.technology': ['203.0.113.11'], 'academia-privada.kadi.technology': ['203.0.113.12'] });
  try {
    const rs = buildRuleSet();
    const r = lintText('https://prod-cliente.kadi.technology/ y academia-privada.kadi.technology', { file: 'a.md', ruleSet: rs }).map((f) => f.rule);
    assert.ok(r.includes('KADI_FORBIDDEN_HOST'));
  } finally {
    process.env.KADI_DNS_OVERRIDE = '{}';
  }
});

test('resolveHostSync real: devuelve estructura valida sin conectar (solo consulta DNS)', () => {
  delete process.env.KADI_DNS_OVERRIDE;
  try {
    const r = resolveHostSync('demo-privada.kadi.technology');
    assert.equal(r.host, 'demo-privada.kadi.technology');
    assert.ok(Array.isArray(r.addresses));
    assert.equal(typeof r.public, 'boolean');
  } finally {
    process.env.KADI_DNS_OVERRIDE = '{}';
  }
});

test('Acta Cero pasa pero una promesa de cero errores sigue fallando', () => {
  assert.ok(rulesFor('Cero errores en tu clinica.').includes('R2_PROMISE_ZERO'));
  assert.ok(!rulesFor('Acta Cero y GK Docs.').includes('R2_PROMISE_ZERO'));
});

test('JSON: el salto de linea escapado no se pega al utm_campaign', () => {
  const json = JSON.stringify({ copy: `Escribenos: ${U}
WhatsApp: https://wa.me/5210000000000` }, null, 2);
  const rules = lintText(json, { file: 'meta.json', ruleSet }).map((f) => f.rule);
  assert.deepEqual(rules, []);
});

test('el hallazgo informa archivo, linea y columna', () => {
  const findings = lintText('linea uno\nlinea dos con 3 clics\n', { file: 'x.md', ruleSet });
  const f = findings.find((x) => x.rule === 'KADI_URGENCIA_3_CLICS');
  assert.ok(f);
  assert.equal(f.file, 'x.md');
  assert.equal(f.line, 2);
  assert.equal(f.col, 15);
});

test('CLI: exit 1 con hallazgos, exit 0 limpio, exit 2 sin argumentos y archivo interno omitido', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kadi-lint-'));
  try {
    const bad = path.join(dir, 'malo.md');
    const good = path.join(dir, 'bueno.md');
    const internal = path.join(dir, 'auditoria.md');
    fs.writeFileSync(bad, 'Somos el mejor software.\nVisita https://kadi.technology/\n', 'utf8');
    fs.writeFileSync(good, `Copy limpio con enlace: ${U}\n`, 'utf8');
    fs.writeFileSync(internal, '<!-- social-lint: internal -->\nprod-cliente.kadi.technology es produccion.\n', 'utf8');

    const rBad = spawnSync(process.execPath, [CLI, bad], { encoding: 'utf8' });
    assert.equal(rBad.status, 1);
    assert.match(rBad.stdout, /malo\.md:1:\d+ {2}\[/);
    assert.match(rBad.stdout, /KADI_UTM_MISSING/);

    const rGood = spawnSync(process.execPath, [CLI, good], { encoding: 'utf8' });
    assert.equal(rGood.status, 0, rGood.stdout);
    assert.match(rGood.stdout, /0 hallazgos/);

    const rDir = spawnSync(process.execPath, [CLI, dir], { encoding: 'utf8' });
    assert.equal(rDir.status, 1);
    assert.match(rDir.stdout, /OMITIDO \(interno/);
    assert.doesNotMatch(rDir.stdout, /auditoria\.md:\d/);

    const rNone = spawnSync(process.execPath, [CLI], { encoding: 'utf8' });
    assert.equal(rNone.status, 2);

    const rMissing = spawnSync(process.execPath, [CLI, path.join(dir, 'no_existe.md')], { encoding: 'utf8' });
    assert.equal(rMissing.status, 2);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
