#!/usr/bin/env node
/**
 * KADI Social Copy Linter
 *
 * Uso:
 *   node scripts/check_social_copy.mjs <directorio|archivo...> [--webpage <ruta>] [--quiet]
 *
 * Carga SOLO LECTURA las reglas de claims del portal:
 *   <KadiWebPage>/docs/linkedin/public-claims-r1.json   (blocked_rules)
 *   <KadiWebPage>/scripts/claims/web-claims-r2.json     (blocked_rules)
 * y agrega reglas KADI propias (adjetivos absolutos, conteos del canon, hosts
 * prohibidos, UTM, plazas Founders, afirmaciones tecnicas sin evidencia, PII).
 *
 * Salida: una linea por hallazgo con formato  archivo:linea:columna  [REGLA]  motivo
 * Codigos de salida: 0 sin hallazgos, 1 con hallazgos, 2 error de uso o de configuracion.
 *
 * Un archivo interno (por ejemplo una auditoria que debe nombrar texto prohibido) se omite
 * si en sus primeras 10 lineas contiene la marca  social-lint: internal  y el omitido se
 * reporta de forma explicita en la salida.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, '..');
const CANDIDATE_WEBPAGE_DIRS = [
  process.env.KADI_WEBPAGE_DIR,
  path.resolve(ROOT, '..', '..', '02_WEBSITES', 'kadi-webpage'),
  path.resolve(ROOT, '..', 'KadiWebPage'),
  // Reglas de claims de ejemplo incluidas en la skill (copia sanitizada)
  path.resolve(ROOT, 'claims-base'),
].filter(Boolean);
const DEFAULT_WEBPAGE = CANDIDATE_WEBPAGE_DIRS.find((dir) => {
  try {
    return fs.existsSync(path.join(dir, 'docs', 'linkedin', 'public-claims-r1.json'));
  } catch {
    return false;
  }
}) || CANDIDATE_WEBPAGE_DIRS[0];
const INDEX_PATH = path.join(ROOT, 'WebPage', 'assets_por_proyecto', 'semantic_visual_index.json');
const VERIFIED_PATH = path.join(SCRIPT_DIR, 'verified_claims.json');

const SCAN_EXTENSIONS = new Set(['.md', '.txt', '.json', '.csv', '.html']);
const SKIP_DIRS = new Set(['node_modules', '.git', 'assets', '_build', '.swarm_state']);
const SKIP_FILES = new Set(['LINT_REPORT.txt']);
const INTERNAL_MARK = /social-lint:\s*internal/i;
const MAX_HASHTAGS = 6;

const CANON_UTM = {
  instagram: ['organic_social'],
  linkedin: ['organic_social'],
  facebook: ['organic_social'],
  youtube: ['video_short', 'video_horizontal'],
  tiktok: ['video_vertical'],
};
const SNAKE_CASE = /^[a-z0-9]+(?:_[a-z0-9]+)*$/;

const NUMBER_WORDS = {
  un: 1, una: 1, uno: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8,
  nueve: 9, diez: 10, once: 11, doce: 12, trece: 13, catorce: 14, quince: 15,
};

export function normalize(text) {
  return String(text).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

function toNumber(token) {
  const t = normalize(token);
  if (/^\d+$/.test(t)) return parseInt(t, 10);
  return Object.prototype.hasOwnProperty.call(NUMBER_WORDS, t) ? NUMBER_WORDS[t] : null;
}

/* ----------------------------------------------------------------------------------------
 * Carga de reglas
 * ------------------------------------------------------------------------------------- */

export function loadClaimRules(webpageDir = DEFAULT_WEBPAGE) {
  const files = [
    { file: path.join(webpageDir, 'docs', 'linkedin', 'public-claims-r1.json'), prefix: 'R1' },
    { file: path.join(webpageDir, 'scripts', 'claims', 'web-claims-r2.json'), prefix: 'R2' },
  ];
  const rules = [];
  for (const { file, prefix } of files) {
    let data;
    try {
      data = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, ''));
    } catch (err) {
      throw new Error(`No se pudo leer las reglas de claims ${file}: ${err.message}`);
    }
    if (!Array.isArray(data.blocked_rules)) {
      throw new Error(`El archivo ${file} no contiene blocked_rules`);
    }
    for (const r of data.blocked_rules) {
      const flags = [...new Set(((r.flags || 'giu') + 'g').split(''))].join('');
      rules.push({
        id: `${prefix}_${r.id}`,
        kind: 'regex',
        regex: new RegExp(r.pattern, flags),
        message: r.reason,
        source: file,
      });
    }
  }
  return rules;
}

export function loadEvidence() {
  const tokens = new Set();
  const sources = [];
  try {
    const index = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf8').replace(/^﻿/, ''));
    for (const project of Object.values(index.projects || {})) {
      for (const asset of project.assets || []) {
        if (asset.verified_claim) tokens.add(normalize(asset.verified_claim));
      }
    }
    sources.push(INDEX_PATH);
  } catch {
    /* sin indice no hay evidencia del harvester: las afirmaciones tecnicas se marcaran */
  }
  try {
    const verified = JSON.parse(fs.readFileSync(VERIFIED_PATH, 'utf8').replace(/^﻿/, ''));
    for (const c of verified.claims || []) {
      for (const t of c.evidence_tokens || []) tokens.add(normalize(t));
    }
    sources.push(VERIFIED_PATH);
  } catch {
    /* archivo opcional */
  }
  return { blob: [...tokens].join('\n'), sources };
}

/* ----------------------------------------------------------------------------------------
 * Reglas KADI propias
 * ------------------------------------------------------------------------------------- */

function regexRule(id, pattern, flags, message) {
  return { id, kind: 'regex', regex: new RegExp(pattern, [...new Set((flags + 'g').split(''))].join('')), message };
}

export function buildKadiRules(evidence, dns = { status: {} }) {
  const rules = [];

  // 1. Adjetivos absolutos y superlativos (complementan R1 y R2)
  const absolutes = [
    '(?<!\\p{L})inhackeabl\\p{L}*',
    '(?<!\\p{L})(?:im)?penetrabl\\p{L}*',
    'a\\s+prueba\\s+de\\s+(?:hackers?|ataques|balas|fallas)',
    '(?<!\\p{L})infalibl\\p{L}*',
    'primer[ao]s?\\s+(?:\\p{L}+\\s+){0,3}del\\s+mundo',
    '(?<!\\p{L})(?:el|la|lo|los|las)\\s+m[aá]s\\s+(?:r[aá]pid|segur|complet|avanzad|potent|innovador|confiabl|inteligent)\\p{L}*',
    '(?<!\\p{L})(?:incomparabl|inigualabl|insuperabl)\\p{L}*',
    'sin\\s+igual(?!\\p{L})',
    'sin\\s+precedentes',
    '(?<!\\p{L})disruptiv\\p{L}*',
    'game[-\\s]?changer',
    'best[-\\s]in[-\\s]class',
    'world[-\\s]class',
    'clase\\s+mundial',
    'mejor(?:es)?\\s+del\\s+(?:mercado|mundo)',
    'n[uú]mero\\s+1(?!\\d)',
  ];
  rules.push(regexRule('KADI_ABSOLUTE_ADJECTIVE', absolutes.join('|'), 'iu',
    'Adjetivo absoluto o superlativo sin respaldo (veracidad KADI).'));

  // 2. Certificaciones no auditadas
  rules.push(regexRule('KADI_UNVERIFIED_CERTIFICATION',
    'ISO[\\s/-]*\\d{4,5}|SOC\\s?[12](?!\\d)|PCI[\\s-]?DSS|NOM-\\d{3}|GDPR|certificad[oa]s?\\s+(?:por|en|ante)\\s|certificaci[oó]n\\s+(?:ISO|SOC|HIPAA|NOM)',
    'iu', 'Certificacion no auditada: no se puede afirmar en publico.'));

  // 3. Hosts, IPs y clientes en cuarentena (P-0)
  rules.push(regexRule('KADI_FORBIDDEN_HOST',
    '(?<![\\w-])prod-cliente\\.kadi\\.technology(?![\\w-])|(?<![\\w-])academia-privada\\.kadi\\.technology(?![\\w-])',
    'iu', 'Host en cuarentena P-0 (produccion real o IP prohibida); nunca enlazar ni mencionar.'));
  rules.push(regexRule('KADI_FORBIDDEN_IP',
    '(?<![\\d.])203\\.0\\.113\\.50(?!\\d|\\.\\d)|(?<![\\d.])203\\.0\\.113\\.51(?!\\d|\\.\\d)',
    'u', 'IP en cuarentena P-0.'));
  rules.push(regexRule('KADI_RAW_IP',
    '(?<![\\d.])(?:\\d{1,3}\\.){3}\\d{1,3}(?!\\d|\\.\\d)', 'u',
    'Direccion IP en el texto: nunca se publican IPs.'));
  // demo-privada/demo-retirada: el hallazgo depende de la resolucion DNS en tiempo de ejecucion (ver resolveHostSync).
  // Si el host no resuelve, o resuelve a una IP prohibida, cualquier mencion es hallazgo.
  const dnsStatus = (dns && dns.status) || {};
  const nonPublic = ['demo-privada', 'demo-retirada'].filter((h) => !(dnsStatus[`${h}.kadi.technology`] || {}).public);
  if (nonPublic.length > 0) {
    rules.push(regexRule('KADI_NONPUBLIC_HOST',
      `(?<![\\w-])(?:${nonPublic.join('|')})\\.kadi\\.technology(?![\\w-])`, 'iu',
      'Host sin DNS publico todavia (la resolucion DNS en tiempo de ejecucion no lo encuentra): no enlazar ni mencionar en piezas publicas.'));
  }
  rules.push(regexRule('KADI_PROHIBITED_CLIENT',
    'KADI_RELEASES_VAULT|Cliente\\s+Ejemplo|CLI-000', 'iu',
    'Cliente real o bodega en cuarentena P-0: no mencionar.'));

  // 4. PII y datos pendientes de confirmar
  rules.push(regexRule('KADI_PII_REVIEWER_NAME', 'Nombre\\s+R\\.', 'iu',
    'Nombre de resenador del portal: la seccion de resenas queda fuera de toda pieza.'));
  rules.push(regexRule('KADI_PII_EMAIL',
    '[\\w.+-]+@(?:gmail|hotmail|outlook|yahoo|icloud)\\.[a-z.]+|[\\w.+-]+@kadi\\.local', 'iu',
    'Correo personal o de prueba: no publicar.'));
  rules.push(regexRule('KADI_UNCONFIRMED_MAILBOX', 'ventas@example\\.com', 'iu',
    'Buzon no confirmado: el correo publico del sitio es otro.'));
  rules.push(regexRule('KADI_CLINIC_PHONE', '55\\s?8347\\s?4800', 'u',
    'Telefono comercial de la clinica: requiere confirmacion de la clinica antes de publicarlo en copy.'));

  // 5. Datos de Urgencia Express y visor 3D verificados el 2026-10-21
  rules.push(regexRule('KADI_URGENCIA_3_CLICS', '(?:3|tres)\\s+clic(?:k|s|ks)?(?![\\p{L}])', 'iu',
    'La pre-admision express es de 1 clic, no de 3.'));
  // El visor/atlas 3D del portal ofrece cuatro especies (canino, felino, conejo y ave); verificado en anatomia3d.js publico el 2026-10-21.
  // La vinculacion clinica con el expediente dentro de KADI SCV (sugerencia de lesiones) si cubre solo perro y gato; esa afirmacion no se marca.
  const soloPG = '(?:solo|solamente|[uú]nicamente)\\s+(?:de\\s+|para\\s+|con\\s+)?(?:perros?\\s+y\\s+gatos?|canino\\s+y\\s+felino)';
  rules.push(regexRule('KADI_VISOR_SOLO_PERRO_GATO',
    `visor[^\\n.]{0,80}${soloPG}|${soloPG}[^\\n.]{0,60}visor`, 'iu',
    'El visor 3D del portal ofrece cuatro especies (canino, felino, conejo y ave), no solo perro y gato.'));

  // 6. Afirmaciones tecnicas que exigen evidencia (indice del harvester o verified_claims.json)
  const techClaims = [
    { id: 'KADI_UNVERIFIED_WEBCRYPTO', pattern: 'web\\s?crypto', needs: 'webcrypto', label: 'WebCrypto' },
    { id: 'KADI_UNVERIFIED_IV_96', pattern: '96\\s*bits?', needs: '96 bits', label: 'IV de 96 bits' },
    { id: 'KADI_UNVERIFIED_AES', pattern: 'AES[-\\s]?256[-\\s]?GCM', needs: 'aes-256-gcm', label: 'AES-256-GCM' },
    { id: 'KADI_UNVERIFIED_LASER', pattern: 'puntero\\s+l[aá]ser', needs: 'puntero laser', label: 'puntero laser' },
    { id: 'KADI_UNVERIFIED_THREEJS', pattern: 'three\\.?js', needs: 'three.js', label: 'Three.js' },
  ];
  for (const claim of techClaims) {
    if (!evidence.blob.includes(normalize(claim.needs))) {
      rules.push(regexRule(claim.id, claim.pattern, 'iu',
        `La afirmacion sobre ${claim.label} no tiene evidencia verificada (indice del harvester o scripts/verified_claims.json).`));
    }
  }

  // El visor NO usa Three.js: afirmar lo contrario es falso aunque exista evidencia de la negacion.
  rules.push(regexRule('KADI_THREEJS_AFFIRMATIVE',
    '(?:con|usa|usamos|usando|construid[oa]\\s+(?:en|con)|basad[oa]\\s+en)\\s+three\\.?js', 'iu',
    'El visor 3D esta escrito en WebGL puro: no usa Three.js.'));

  // 7. Gladys con gobernanza humana y etapas canonicas
  rules.push(regexRule('KADI_GLADYS_OVERCLAIM',
    'Gladys\\s+(?:diagnostica|decide|prescribe|receta|reemplaza|sustituye\\s+al)', 'iu',
    'Gladys apoya; la decision clinica es del medico veterinario.'));
  rules.push(regexRule('KADI_STAGE_OVERCLAIM',
    '(?:Gladys|Contract\\s+ERP|TVillage|Academia|Vital\\s+Signs\\s+Vet|R[eé]quiem|GK\\s+Docs|ChronoSDK|Swarm|Anatom[ií]a\\s+3D|Biblioteca)[^\\n.]{0,80}(?:ya\\s+disponible|disponible\\s+(?:hoy|ya)|(?<!fecha\\s+de\\s+)lanzamiento|lanzamos|a\\s+la\\s+venta)',
    'iu', 'Solo KADI SCV esta en etapa disponible; el resto esta en desarrollo o validacion.'));
  rules.push(regexRule('KADI_PRIVACY_ABSOLUTE',
    'imposible\\s+de\\s+(?:hackear|vulnerar)|nadie\\s+(?:puede|podr[aá])\\s+(?:leer|acceder)|ni\\s+KADI\\s+puede|cifrad\\p{L}*\\s+(?:militar|bancari)',
    'iu', 'Promesa absoluta de privacidad o seguridad.'));

  // 8. Cohorte Founders: privilegios contractuales y escasez inventada
  rules.push(regexRule('KADI_FOUNDERS_LIFETIME_PROMISE', 'de\\s+por\\s+vida|vitalici\\p{L}*|congelad\\p{L}*', 'iu',
    'Privilegio contractual no aprobado para redes sociales.'));
  rules.push(regexRule('KADI_FOUNDERS_SCARCITY',
    '[uú]ltimas?\\s+plazas|plazas\\s+agotad\\p{L}*|solo\\s+quedan|quedan\\s+\\d+', 'iu',
    'Escasez no respaldada por el estado real de la cohorte.'));

  // 8b. Capacidades que el codigo de KADI SCV todavia no implementa
  rules.push(regexRule('KADI_AES_BACKUPS',
    '(?:respaldos?|backups?|copias?\\s+de\\s+seguridad)[^\\n.]{0,80}(?:AES|cifrad\\p{L}*|encriptad\\p{L}*)|(?:AES[-\\s]?256[-\\s]?GCM|cifrad\\p{L}*|encriptad\\p{L}*)[^\\n.]{0,80}(?:respaldos?|backups?|copias?\\s+de\\s+seguridad)',
    'iu', 'KADI SCV no implementa respaldos cifrados con AES-256-GCM; AES-256-GCM solo es la demo de cifrado del navegador.'));
  rules.push(regexRule('KADI_CFDI',
    'CFDI|timbrad\\p{L}*|timbra(?:r|mos)?(?!\\p{L})',
    'iu', 'KADI SCV no implementa CFDI ni timbrado: no mencionarlo como disponible.'));

  // 9. Placeholders
  rules.push(regexRule('KADI_PLACEHOLDER', 'TODO|TBD|XXX|\\[\\s*(?:pendiente|completar|insertar)[^\\]]*\\]', 'u',
    'Placeholder o texto pendiente.'));
  rules.push(regexRule('KADI_PLACEHOLDER_LOREM', 'lorem\\s+ipsum', 'iu', 'Texto de relleno.'));

  return rules;
}

/* ----------------------------------------------------------------------------------------
 * Reglas con logica (conteos, plazas, UTM, hashtags)
 * ------------------------------------------------------------------------------------- */

function* matchesWithIndex(regex, text) {
  const re = new RegExp(regex.source, regex.flags.includes('g') ? regex.flags : regex.flags + 'g');
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m[0].length === 0) {
      re.lastIndex += 1;
      continue;
    }
    yield m;
  }
}

function checkCounts(text) {
  const out = [];
  const re = /(?<![\p{L}\d])(\d{1,3}|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince)\s+(sistemas|proyectos|productos|m[oó]dulos)(?:\s+(\p{L}+))?/giu;
  let m;
  while ((m = re.exec(text)) !== null) {
    const n = toNumber(m[1]);
    if (n === null) continue;
    const noun = normalize(m[2]);
    const next = normalize(m[3] || '');
    let ok;
    if (noun === 'sistemas') {
      ok = n === 10 || (n === 14 && next.startsWith('anatom'));
    } else if (noun === 'modulos') {
      ok = n === 2 && next.startsWith('clinico');
    } else {
      ok = n === 10;
    }
    if (!ok) {
      out.push({
        index: m.index,
        rule: 'KADI_CANON_COUNT',
        message: 'Conteo distinto al canon: 10 sistemas principales + 2 modulos clinicos vinculados (14 sistemas solo para el visor 3D, con la palabra anatomicos).',
        match: m[0],
      });
    }
  }
  return out;
}

function checkPlazas(text) {
  const out = [];
  const tag = /(?<![\p{L}\d&])#\s?(\d+)(?![\p{L}\d])/gu;
  let m;
  while ((m = tag.exec(text)) !== null) {
    const digits = m[1];
    const n = parseInt(digits, 10);
    let ok = false;
    if (digits.length === 3) ok = n >= 1 && n <= 10;
    else if (digits.length === 2) ok = digits === '01';
    if (!ok) {
      out.push({
        index: m.index,
        rule: 'KADI_FOUNDERS_PLAZA',
        message: 'Plaza fuera del canon: #001 asignada a la clinica fundadora, #002 a #010 abiertas; la cohorte se llama KADI Founders #01.',
        match: m[0],
      });
    }
  }
  const count = /(?<![\p{L}\d])(\d{1,3}|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+plazas/giu;
  while ((m = count.exec(text)) !== null) {
    const n = toNumber(m[1]);
    if (n !== null && n !== 10 && n !== 9) {
      out.push({
        index: m.index,
        rule: 'KADI_FOUNDERS_PLAZA',
        message: 'La cohorte tiene 10 plazas: #001 asignada y 9 abiertas (#002 a #010).',
        match: m[0],
      });
    }
  }
  return out;
}

// Se excluye la barra invertida: en los .json un salto de linea escapado (\n) no es parte de la URL.
const URL_RE = /https?:\/\/[^\s<>"'`)\]}\\]+/giu;
const BARE_RE = /(?<![\w@./:-])(?:[a-z0-9-]+\.)*kadi\.technology(?![\w-])(?:\/[^\s<>"'`)\]}\\]*)?/giu;

function stripTrailingPunctuation(u) {
  return u.replace(/[.,;:!?*_]+$/u, '');
}

const CANON_HOSTS = new Set(['kadi.technology', 'portal-cliente.kadi.technology', 'wa.me', 'calendar.app.google']);

export function checkLinks(text, dns = { status: {} }) {
  const out = [];
  const status = (dns && dns.status) || {};
  // demo-privada/demo-retirada solo cuentan como canonicos si resuelven en DNS; si no, los reporta KADI_NONPUBLIC_HOST.
  const resolvedOk = new Set(Object.entries(status).filter(([, s]) => s.public).map(([h]) => h));
  const forbiddenHost = /^(?:prod-cliente|academia-privada|demo-privada|demo-retirada)\.kadi\.technology$/i;
  let m;
  while ((m = URL_RE.exec(text)) !== null) {
    const raw = stripTrailingPunctuation(m[0]);
    let url;
    try {
      url = new URL(raw.replace(/\\u0026/g, '&'));
    } catch {
      out.push({ index: m.index, rule: 'KADI_LINK_INVALID', message: 'Enlace mal formado.', match: raw });
      continue;
    }
    const host = url.hostname.toLowerCase();
    // Ya lo reporta KADI_FORBIDDEN_HOST / KADI_NONPUBLIC_HOST, salvo demo-privada/demo-retirada que ya resuelven en DNS.
    if (forbiddenHost.test(host) && !resolvedOk.has(host)) continue;
    if (!CANON_HOSTS.has(host) && !resolvedOk.has(host)) {
      out.push({
        index: m.index,
        rule: 'KADI_LINK_NOT_CANONICAL',
        message: 'Enlace fuera del canon (kadi.technology, portal-cliente.kadi.technology, WhatsApp wa.me/5210000000000, agenda calendar.app.google).',
        match: raw,
      });
      continue;
    }
    if (host === 'wa.me') {
      if (!url.pathname.startsWith('/5210000000000')) {
        out.push({ index: m.index, rule: 'KADI_LINK_NOT_CANONICAL', message: 'El numero de WhatsApp canonico es 5210000000000.', match: raw });
      }
      continue;
    }
    if (host === 'calendar.app.google') {
      if (!url.pathname.startsWith('/ID_AGENDA_EJEMPLO')) {
        out.push({ index: m.index, rule: 'KADI_LINK_NOT_CANONICAL', message: 'La agenda canonica es calendar.app.google/ID_AGENDA_EJEMPLO.', match: raw });
      }
      continue;
    }
    const p = url.searchParams;
    const missing = ['utm_source', 'utm_medium', 'utm_campaign'].filter((k) => !p.get(k));
    if (missing.length > 0) {
      out.push({
        index: m.index,
        rule: 'KADI_UTM_MISSING',
        message: `Enlace a ${host} sin ${missing.join(', ')}.`,
        match: raw,
      });
      continue;
    }
    const source = p.get('utm_source');
    const medium = p.get('utm_medium');
    const campaign = p.get('utm_campaign');
    if (!Object.prototype.hasOwnProperty.call(CANON_UTM, source)) {
      out.push({ index: m.index, rule: 'KADI_UTM_SCHEME', message: `utm_source "${source}" fuera del esquema oficial (instagram, linkedin, facebook, youtube, tiktok).`, match: raw });
    } else if (!CANON_UTM[source].includes(medium)) {
      out.push({ index: m.index, rule: 'KADI_UTM_SCHEME', message: `utm_medium "${medium}" no corresponde a ${source}; esperado: ${CANON_UTM[source].join(' | ')}.`, match: raw });
    }
    if (!SNAKE_CASE.test(campaign)) {
      out.push({ index: m.index, rule: 'KADI_UTM_SCHEME', message: `utm_campaign "${campaign}" debe estar en snake_case.`, match: raw });
    }
  }
  while ((m = BARE_RE.exec(text)) !== null) {
    const raw = stripTrailingPunctuation(m[0]);
    const bareHost = raw.split('/')[0].toLowerCase();
    if (/^(?:prod-cliente|academia-privada|demo-privada|demo-retirada)\.kadi\.technology/i.test(raw) && !resolvedOk.has(bareHost)) continue;
    out.push({
      index: m.index,
      rule: 'KADI_UTM_MISSING',
      message: 'Dominio de KADI escrito sin esquema ni UTM: usa el enlace completo con utm_source, utm_medium y utm_campaign.',
      match: raw,
    });
  }
  return out;
}

function checkHashtags(text) {
  const out = [];
  const re = /(?<![\p{L}\d&#])#[\p{L}][\p{L}\d_]*/gu;
  const all = [...text.matchAll(re)];
  if (all.length > MAX_HASHTAGS) {
    out.push({
      index: all[MAX_HASHTAGS].index,
      rule: 'KADI_HASHTAGS_EXCESS',
      message: `Hashtags moderados: maximo ${MAX_HASHTAGS} por archivo (hay ${all.length}).`,
      match: all[MAX_HASHTAGS][0],
    });
  }
  return out;
}

/* ----------------------------------------------------------------------------------------
 * Motor
 * ------------------------------------------------------------------------------------- */

function lineStarts(text) {
  const starts = [0];
  for (let i = 0; i < text.length; i += 1) if (text[i] === '\n') starts.push(i + 1);
  return starts;
}

function locate(starts, index) {
  let lo = 0;
  let hi = starts.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (starts[mid] <= index) lo = mid;
    else hi = mid - 1;
  }
  return { line: lo + 1, col: index - starts[lo] + 1 };
}

const FORBIDDEN_IPS = new Set(['203.0.113.50', '203.0.113.51']);
const DNS_HOSTS = ['demo-privada.kadi.technology', 'demo-retirada.kadi.technology'];

/**
 * Resolucion DNS en tiempo de ejecucion (solo consulta DNS, nunca una conexion al host).
 * Se ejecuta en un proceso hijo de Node para mantener la API de lint sincrona.
 * KADI_DNS_OVERRIDE (JSON {"host":["ip",...]}) permite pruebas deterministas sin red.
 * Devuelve { addresses, public }: public=true solo si resuelve y ninguna IP esta prohibida (P-0).
 */
export function resolveHostSync(host, { timeoutMs = 6000 } = {}) {
  let addresses = [];
  const override = process.env.KADI_DNS_OVERRIDE;
  if (override) {
    try {
      const map = JSON.parse(override);
      addresses = Array.isArray(map[host]) ? map[host] : [];
    } catch {
      addresses = [];
    }
  } else {
    const code = "const dns=require('node:dns');dns.lookup(process.argv[1],{all:true},(e,a)=>{console.log(JSON.stringify(e?[]:a.map(x=>x.address)));});";
    const r = spawnSync(process.execPath, ['-e', code, host], { encoding: 'utf8', timeout: timeoutMs });
    try {
      addresses = r.status === 0 ? JSON.parse(r.stdout.trim() || '[]') : [];
    } catch {
      addresses = [];
    }
  }
  const forbidden = addresses.some((ip) => FORBIDDEN_IPS.has(ip));
  return { host, addresses, public: addresses.length > 0 && !forbidden };
}

export function resolveDnsStatus() {
  const status = {};
  for (const host of DNS_HOSTS) status[host] = resolveHostSync(host);
  return { status, checked_at: new Date().toISOString() };
}

export function buildRuleSet({ webpageDir = DEFAULT_WEBPAGE } = {}) {
  const claimRules = loadClaimRules(webpageDir);
  const evidence = loadEvidence();
  const dns = resolveDnsStatus();
  const kadiRules = buildKadiRules(evidence, dns);
  return { rules: [...claimRules, ...kadiRules], evidence, dns };
}

export function lintText(text, { file = '<texto>', ruleSet } = {}) {
  const set = ruleSet || buildRuleSet();
  const clean = String(text).replace(/^﻿/, '').replace(/\r\n/g, '\n');
  const starts = lineStarts(clean);
  const raw = [];
  for (const rule of set.rules) {
    for (const m of matchesWithIndex(rule.regex, clean)) {
      // "Acta Cero" es el nombre del proyecto Requiem, no una promesa de cero resultados.
      if (rule.id === 'R2_PROMISE_ZERO' && /acta\s$/i.test(clean.slice(Math.max(0, m.index - 6), m.index))) continue;
      raw.push({ index: m.index, rule: rule.id, message: rule.message, match: m[0] });
    }
  }
  raw.push(...checkCounts(clean), ...checkPlazas(clean), ...checkLinks(clean, set.dns));
  // Los .json repiten los hashtags de cada pieza en una sola estructura: el tope se aplica al copy.md de cada pieza.
  if (path.extname(file).toLowerCase() !== '.json') raw.push(...checkHashtags(clean));
  raw.sort((a, b) => a.index - b.index || a.rule.localeCompare(b.rule));
  const seen = new Set();
  const findings = [];
  for (const f of raw) {
    const key = `${f.index}|${f.rule}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const { line, col } = locate(starts, f.index);
    findings.push({ file, line, col, rule: f.rule, message: f.message, match: f.match.replace(/\s+/g, ' ').slice(0, 80) });
  }
  return findings;
}

export function isInternal(text) {
  return text.split(/\r?\n/).slice(0, 10).some((l) => INTERNAL_MARK.test(l));
}

export function collectFiles(targets) {
  const files = [];
  const visit = (p) => {
    const stat = fs.statSync(p);
    if (stat.isDirectory()) {
      if (SKIP_DIRS.has(path.basename(p))) return;
      for (const name of fs.readdirSync(p).sort()) visit(path.join(p, name));
    } else if (stat.isFile()) {
      if (SKIP_FILES.has(path.basename(p))) return;
      files.push(p);
    }
  };
  for (const t of targets) {
    const abs = path.resolve(t);
    if (!fs.existsSync(abs)) throw new Error(`No existe: ${t}`);
    const stat = fs.statSync(abs);
    if (stat.isFile()) {
      files.push(abs);
    } else {
      const before = files.length;
      visit(abs);
      for (let i = files.length - 1; i >= before; i -= 1) {
        if (!SCAN_EXTENSIONS.has(path.extname(files[i]).toLowerCase())) files.splice(i, 1);
      }
    }
  }
  return files;
}

export function lintFiles(targets, options = {}) {
  const ruleSet = options.ruleSet || buildRuleSet({ webpageDir: options.webpageDir });
  const files = collectFiles(targets);
  const findings = [];
  const skipped = [];
  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8');
    if (isInternal(text)) {
      skipped.push(file);
      continue;
    }
    findings.push(...lintText(text, { file, ruleSet }));
  }
  return { findings, skipped, scanned: files.length - skipped.length, ruleCount: ruleSet.rules.length, evidenceSources: ruleSet.evidence.sources, dns: ruleSet.dns };
}

export function formatFinding(f, base = process.cwd()) {
  const rel = path.relative(base, f.file) || f.file;
  return `${rel}:${f.line}:${f.col}  [${f.rule}]  ${f.message}  -> "${f.match}"`;
}

function main(argv) {
  const args = [];
  let webpageDir = DEFAULT_WEBPAGE;
  let quiet = false;
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--webpage') {
      webpageDir = argv[i + 1];
      i += 1;
    } else if (argv[i] === '--quiet') {
      quiet = true;
    } else if (argv[i] === '--help' || argv[i] === '-h') {
      console.log('Uso: node scripts/check_social_copy.mjs <directorio|archivo...> [--webpage <ruta>] [--quiet]');
      return 0;
    } else {
      args.push(argv[i]);
    }
  }
  if (args.length === 0) {
    console.error('Uso: node scripts/check_social_copy.mjs <directorio|archivo...> [--webpage <ruta>] [--quiet]');
    return 2;
  }
  let result;
  try {
    result = lintFiles(args, { webpageDir });
  } catch (err) {
    console.error(`ERROR DE CONFIGURACION: ${err.message}`);
    return 2;
  }
  if (result.scanned === 0 && result.skipped.length === 0) {
    console.error('ERROR: no se encontro ningun archivo de texto para analizar.');
    return 2;
  }
  for (const f of result.findings) console.log(formatFinding(f));
  if (!quiet) {
    for (const s of result.skipped) {
      console.log(`OMITIDO (interno, marca social-lint: internal): ${path.relative(process.cwd(), s) || s}`);
    }
  }
  if (!quiet && result.dns) {
    for (const [host, s] of Object.entries(result.dns.status)) {
      console.log(`DNS en tiempo de ejecucion: ${host} -> ${s.addresses.length ? s.addresses.join(', ') : 'no resuelve'}${s.public ? '' : ' (no publico: cualquier mencion es hallazgo)'}`);
    }
  }
  const files = new Set(result.findings.map((f) => f.file)).size;
  console.log(
    `${result.findings.length} hallazgos en ${files} archivos (${result.scanned} archivos analizados, ${result.skipped.length} omitidos por marca interna, ${result.ruleCount} reglas activas)`,
  );
  return result.findings.length > 0 ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exit(main(process.argv.slice(2)));
}
