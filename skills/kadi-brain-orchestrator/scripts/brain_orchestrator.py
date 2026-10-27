"""
KADI Brain Orchestrator v3.0.0 (Enterprise Quad-Brain Engine)
Orquestación armónica de modelos de frontera Anthropic + Antigravity (Gemini 3.8).

ARQUITECTURA DE ROLES (EL CUARTETO ESPECIALIZADO):
1. FABLE 5.1: Cerebro Estratégico Omnisciente (Visión de Producto, Agencia, Roadmaps).
2. OPUS 5.5: Arquitecto Técnico Maestro (Descomposición DAG, Contratos de Datos, Auditoría).
3. SONNET 5.5: Sintetizador Quirúrgico de Código (Generación de Código Fuente, Diffs, Controladores).
4. GEMINI 3.8 / ANTIGRAVITY: Caballo de Batalla Operativo Local (Windows NTFS, Terminal, Linters, Pruebas).

POLÍTICA DE TOKENS Y COSTOS:
- Prompt Caching efímero (90% ahorro en tokens de entrada para esquemas y directivas).
- Razonamiento Adaptativo con control de esfuerzo (effort: low, medium, high).
- Detección automática de Streaming si max_tokens > 16,384.
- Telemetría financiera en tiempo real (Costo USD + Ahorro USD por caché).
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime, timezone

try:
    import anthropic
except ImportError:
    print("ERROR: El paquete 'anthropic' no está instalado. Ejecute: pip install anthropic")
    sys.exit(1)

# Ensure safe UTF-8 output on Windows PowerShell
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Resolving Paths
ENV_FILE = Path.home() / ".env"
KB_DIR = Path.home() / "Desktop" / "KADI_NOTEBOOKLM_KNOWLEDGE_BASE"
WORKSPACE_ROOT = Path.home() / "Desktop"
WORKFLOWS_DIR = KB_DIR / "workflows"

# Pricing por 1M tokens (USD)
MODEL_PRICING = {
    "claude-fable-5-1":  {"input": 10.0, "cache_read": 1.0,  "cache_write": 12.5, "output": 50.0},
    "claude-fable-5":    {"input": 10.0, "cache_read": 1.0,  "cache_write": 12.5, "output": 50.0},
    "claude-opus-5-5":   {"input": 4.0,  "cache_read": 0.4,  "cache_write": 5.0,  "output": 20.0},
    "claude-opus-5":     {"input": 4.0,  "cache_read": 0.4,  "cache_write": 5.0,  "output": 20.0},
    "claude-sonnet-5-5": {"input": 3.0,  "cache_read": 0.3,  "cache_write": 3.75, "output": 15.0},
    "claude-sonnet-5":   {"input": 3.0,  "cache_read": 0.3,  "cache_write": 3.75, "output": 15.0},
    "claude-haiku-5-5":  {"input": 0.8,  "cache_read": 0.08, "cache_write": 1.0,  "output": 4.0},
}

# Token Profile Matrices
TOKEN_PROFILES = {
    "fable": {
        "chat": 1024,      # Conversación estándar, resúmenes, formateo rápido
        "code": 4096,      # Programación puntual, refactors, debugging guiado
        "agent": 8192,     # Agentes autónomos, textos extensos, estrategia omnisciente
        "deep": 16384,     # Generación masiva profunda
        "ceiling": 128000  # Máximo absoluto con streaming
    },
    "opus": {
        "consult": 4096,   # Consultas técnicas minuciosas, arquitectura base
        "code": 8192,      # Desarrollo avanzado, módulos enteros, migraciones masivas
        "agent": 16384,    # Agentes autónomos, flujos multietapa, encadenamiento
        "massive": 32768,  # Flujos extendidos de larga duración (Streaming)
        "ceiling": 128000  # Máximo absoluto con streaming
    },
    "sonnet": {
        "func": 4096,      # Funciones individuales, utilidades, consultas breves
        "code": 16384,     # Controladores, componentes Vue/React, comandos Rust (recomendado)
        "module": 16384,   # Módulos enteros, suites de testing completas
        "massive": 32768,  # Reescritura masiva de archivos fuente (Streaming)
        "ceiling": 128000  # Techo con streaming
    }

}

def get_api_key():
    # Priorizar .env sobre variables de entorno de shell para evitar claves obsoletas
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    val = line.strip().split("=", 1)[1]
                    if val.startswith("sk-ant-"):
                        return val
    key = os.getenv("ANTHROPIC_API_KEY")
    if key and key.startswith("sk-ant-"):
        return key
    return None


def build_cached_system_prompt(repo_filter=None):
    """
    Construye el bloque de contexto del sistema con Prompt Caching efímero de Anthropic.
    Ahorra el 90% del costo en tokens de entrada para esquemas técnicos.
    """
    context_blocks = []
    
    system_intro = (
        "Eres el NÚCLEO DE INTELIGENCIA DE FRONTERA DE KADI TECHNOLOGY.\n"
        "Operas bajo la gobernanza del Cuarteto Especializado:\n"
        "- FABLE 5.1: Visión de producto, agencia y estrategia omnisciente.\n"
        "- OPUS 5.5: Arquitectura técnica maestra, esquemas y descomposición DAG.\n"
        "- SONNET 5.5: Síntesis quirúrgica de código de grado de producción.\n"
        "- GEMINI 3.8 (ANTIGRAVITY): Caballo de batalla operativo local en Windows NTFS.\n\n"
        "LEYES INMUTABLES DE KADI:\n"
        "1. AISLAMIENTO SAGRADO: Prohibido tocar la IP de producción <IP_PRODUCCION> ni KADI_RELEASES_VAULT.\n"
        "2. SILENCIO OPERATIVO: Cero ejecuciones de audio o chrono.exe.\n"
        "3. PRECISIÓN QUIRÚRGICA: Rutas exactas, código completo (cero placeholders), linters reales.\n"
        "4. LOCAL-FIRST: Los datos de las clínicas y usuarios residen localmente en su propio hardware."
    )
    context_blocks.append({
        "type": "text",
        "text": system_intro
    })
    
    # Radiografía Técnica Completa en Caché Efímera de Anthropic (Hasta 100k+ tokens con 90% de descuento)
    radiografia_summary = []
    directive_file = KB_DIR / "16_DIRECTIVA_EJECUTIVA_OPUS_5_5_ARGON.md"
    schema_file = KB_DIR / "13_ESQUEMAS_DATOS_Y_RUTAS_API.md"
    manifest_file = KB_DIR / "14_MANIFIESTOS_Y_COMANDOS_BUILD.md"
    git_tree_file = KB_DIR / "12_RADIOGRAFIA_GIT_Y_ARBOLES.md"
    gladys_file = KB_DIR / "15_ESTADO_GLADYS_SWARM_Y_MODULOS_CLINICOS.md"
    
    if directive_file.exists():
        radiografia_summary.append("=== DIRECTIVA DE GOBERNANZA OPUS 5.5 (§16) ===\n" + directive_file.read_text(encoding="utf-8", errors="ignore"))
    if schema_file.exists():
        radiografia_summary.append("=== ESQUEMAS Y RUTAS TÉCNICAS COMPLETAS (§13) ===\n" + schema_file.read_text(encoding="utf-8", errors="ignore"))
    if manifest_file.exists():
        radiografia_summary.append("=== MANIFIESTOS Y COMANDOS DE BUILD (§14) ===\n" + manifest_file.read_text(encoding="utf-8", errors="ignore"))
    if git_tree_file.exists():
        radiografia_summary.append("=== ÁRBOLES GIT Y ESTRUCTURA DE REPOSITORIOS (§12) ===\n" + git_tree_file.read_text(encoding="utf-8", errors="ignore"))
    if gladys_file.exists():
        radiografia_summary.append("=== ESTADO GLADYS, SWARM Y MÓDULOS CLÍNICOS (§15) ===\n" + gladys_file.read_text(encoding="utf-8", errors="ignore")[:60000])
        
    full_cacheable_context = "\n\n".join(radiografia_summary)
    if full_cacheable_context:
        context_blocks.append({
            "type": "text",
            "text": full_cacheable_context,
            "cache_control": {"type": "ephemeral"}  # <-- PROMPT CACHING MASIVO ACTIVO (90% DESCUENTO)
        })
        
    return context_blocks


def print_token_telemetry(resp, model_name):
    """
    Imprime telemetría detallada de tokens, incluyendo thinking_tokens,
    lectura de caché y cálculo financiero en USD reales.
    """
    usage = getattr(resp, 'usage', None)
    if not usage:
        return
    
    input_tokens = getattr(usage, 'input_tokens', 0)
    output_tokens = getattr(usage, 'output_tokens', 0)
    cached_read = getattr(usage, 'cache_read_input_tokens', 0)
    cached_write = getattr(usage, 'cache_creation_input_tokens', 0)
    
    details = getattr(usage, 'output_tokens_details', None)
    thinking_tokens = 0
    if details:
        thinking_tokens = getattr(details, 'thinking_tokens', 0)
        
    pricing = MODEL_PRICING.get(model_name, {"input": 4.0, "cache_read": 0.4, "cache_write": 5.0, "output": 20.0})
    
    # Cálculo financiero en USD
    cost_input = (input_tokens / 1_000_000) * pricing["input"]
    cost_cache_read = (cached_read / 1_000_000) * pricing["cache_read"]
    cost_cache_write = (cached_write / 1_000_000) * pricing["cache_write"]
    cost_output = (output_tokens / 1_000_000) * pricing["output"]
    total_real_cost = cost_input + cost_cache_read + cost_cache_write + cost_output
    
    # Ahorro obtenido por caché (si esos tokens se hubiesen cobrado a precio completo)
    cost_without_cache = ((input_tokens + cached_read) / 1_000_000) * pricing["input"] + cost_output
    savings_usd = max(0.0, cost_without_cache - total_real_cost)
    
    print("\n" + "-" * 68)
    print(f"[TELEMETRIA DE TOKENS Y COSTOS] Modelo: {model_name}")
    print(f"  * Tokens Entrada (Nuevos):    {input_tokens:,}")
    if cached_read > 0:
        print(f"  * Tokens Entrada (En Cache):  {cached_read:,} (90% de descuento aplicado)")
    if cached_write > 0:
        print(f"  * Tokens Escritos en Cache:   {cached_write:,}")
    print(f"  * Tokens de Salida (Total):   {output_tokens:,}")
    if thinking_tokens > 0:
        print(f"  * Tokens de Pensamiento:      {thinking_tokens:,} (Razonamiento adaptativo)")
    print(f"  * Costo Estimado de Llamada:  ${total_real_cost:.5f} USD")
    if savings_usd > 0:
        print(f"  * Ahorro por Prompt Caching:  ${savings_usd:.5f} USD (~90% en lectura base)")
    print("-" * 68)


def call_anthropic_safe(client, model, messages, system, max_tokens, effort="low", thinking_budget=None, stream=False):
    """
    Invoca la API de Anthropic con calibración de razonamiento adaptativo y límites de salida:
    - Si max_tokens > 16384: Conmuta automáticamente a Streaming para evitar error 400.
    - Utiliza thinking adaptativo y effort ('low', 'medium', 'high') para optimizar velocidad y tokens.
    """
    # Si max_tokens > 16384, la API de Anthropic requiere Streaming obligatorio
    auto_stream = stream or (max_tokens > 16384)
    
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages
    }
    
    if thinking_budget:
        if max_tokens <= thinking_budget:
            max_tokens = thinking_budget + 4096
            kwargs["max_tokens"] = max_tokens
        kwargs["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget
        }
    else:
        # Razonamiento adaptativo con control de esfuerzo
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["output_config"] = {"effort": effort}

    if auto_stream:
        print(f"[*] Modo Streaming activado (techo: {max_tokens} tokens | effort: {effort})...")
        full_text = []
        with client.messages.stream(**kwargs) as stream_resp:
            for text in stream_resp.text_stream:
                sys.stdout.write(text)
                sys.stdout.flush()
                full_text.append(text)
            final_msg = stream_resp.get_final_message()
            print_token_telemetry(final_msg, model)
        return "".join(full_text).strip()
    else:
        resp = client.messages.create(**kwargs)
        print_token_telemetry(resp, model)
        text_parts = [b.text for b in resp.content if hasattr(b, 'text')]
        return "\n".join(text_parts).strip()

def handle_plan(args, client):
    """
    Genera un Plan de Desarrollo Quirúrgico con Opus 5.5.
    """
    model = args.model or "claude-opus-5-5"
    profile = args.profile or "agent"
    effort = args.effort or "medium"
    
    if args.max_tokens:
        max_tokens = args.max_tokens
    else:
        max_tokens = TOKEN_PROFILES.get("opus", {}).get(profile, 16384)
        
    print(f"\n[ORQUESTADOR {model}] Generando Plan de Desarrollo Quirúrgico...")
    print(f"Perfil: {profile} | max_tokens: {max_tokens} | Effort: {effort}")
    print(f"Objetivo: {args.goal}")
    if args.repo:
        print(f"Repositorio objetivo: {args.repo}")
        
    user_prompt = f"""MISIÓN TÉCNICA:
Objetivo: {args.goal}
Repositorio: {args.repo or 'Ecosistema General KADI'}
Contexto adicional: {args.context or 'Ninguno'}

Como Orquestador Maestro (Opus 5.5), emite el PLAN DE DESARROLLO DETERMINISTA para que SONNET 5.5 (sintetizador de código) y ANTIGRAVITY / GEMINI 3.8 (ejecutor en Windows local) lo lleven a cabo.
Estructura obligatoria:
1. Diagnóstico Técnico y Alcance Exacto.
2. Archivos exactos a crear o modificar (rutas relativas absolutas y firmas de clases/funciones).
3. Interfaces de Tipos, Migraciones DDL o Esquemas Prisma.
4. Secuencia de Implementación en Código (especificaciones exactas para Sonnet 5.5).
5. Playbook de Comandos Locales para Antigravity (PowerShell, npm, cargo, php artisan).
6. Checklist de Definition of Done (Criterios de Aceptación).
"""

    system_prompt = build_cached_system_prompt(args.repo)
    full_text = call_anthropic_safe(
        client, model, [{"role": "user", "content": user_prompt}], 
        system_prompt, max_tokens, effort=effort, stream=args.stream
    )
        
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"\n[OK] Plan guardado en: {out_path} ({len(full_text)} caracteres)")
    elif not args.stream:
        print("\n" + "=" * 80)
        print(full_text)
        print("=" * 80)
        
    return full_text

def handle_strategy(args, client):
    """
    Emite una Directiva Estratégica u Omnisciente con Fable 5.1.
    """
    model = args.model or "claude-fable-5-1"
    profile = args.profile or "agent"
    effort = args.effort or "low"
    
    if args.max_tokens:
        max_tokens = args.max_tokens
    else:
        max_tokens = TOKEN_PROFILES.get("fable", {}).get(profile, 8192)
        
    print(f"\n[CEREBRO ESTRATÉGICO {model}] Emitiendo Directiva Omnisciente...")
    print(f"Perfil: {profile} | max_tokens: {max_tokens} | Effort: {effort}")
    print(f"Tema: {args.topic}")
    
    user_prompt = f"""DIRECTIVA ESTRATÉGICA:
Iniciativa: {args.topic}
Contexto: {args.context or 'Portafolio KADI Technology'}

Como Cerebro Estratégico Omnisciente (Fable 5.1), genera la directiva de negocio, arquitectura y visión para KADI Technology.
Estructura obligatoria:
1. Visión Estratégica y Posicionamiento de Mercado.
2. Impacto en el Portafolio de 11 Productos KADI.
3. Desafíos de Experiencia de Usuario y Gobernanza de Privacidad (Local-First).
4. Directiva Arquitectónica para Opus 5.5 y el equipo de ingeniería.
5. Roadmap por Fases y Métricas Clave de Éxito.
"""

    system_prompt = build_cached_system_prompt()
    full_text = call_anthropic_safe(
        client, model, [{"role": "user", "content": user_prompt}],
        system_prompt, max_tokens, effort=effort, stream=args.stream
    )
    
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"\n[OK] Directiva guardada en: {out_path} ({len(full_text)} caracteres)")
    elif not args.stream:
        print("\n" + "=" * 80)
        print(full_text)
        print("=" * 80)
        
    return full_text

def handle_synthesize(args, client):
    """
    Utiliza Sonnet 5.5 como Sintetizador Quirúrgico de Código de Élite.
    """
    model = args.model or "claude-sonnet-5-5"
    profile = args.profile or "code"
    effort = args.effort or "low"
    
    if args.max_tokens:
        max_tokens = args.max_tokens
    else:
        max_tokens = TOKEN_PROFILES.get("sonnet", {}).get(profile, 16384)
        
    print(f"\n[SINTETIZADOR DE CÓDIGO {model}] Generando código de grado de producción...")
    print(f"Perfil: {profile} | max_tokens: {max_tokens} | Effort: {effort}")
    print(f"Requerimiento: {args.spec}")
    if args.repo:
        print(f"Repositorio objetivo: {args.repo}")
        
    user_prompt = f"""REQUERIMIENTO DE IMPLEMENTACIÓN DE CÓDIGO:
Objetivo: {args.spec}
Repositorio: {args.repo or 'Ecosistema General KADI'}
Contexto / Plan de referencia:
{args.plan[:4000] if args.plan else 'Directo desde especificación.'}

Como Sintetizador de Código de Élite (Sonnet 5.5), escribe el código fuente COMPLETO y LISTO PARA INYECCIÓN.
DIRECTRICES ESTRICTAS:
1. Cero placeholders, cero comentarios como '// implement code here' o '...'.
2. Rutas relativas exactas de cada archivo en el bloque de encabezado.
3. Tipado estricto (TypeScript, Rust, PHP 8.2+, Python 3.13).
4. Manejo robusto de errores y pruebas unitarias correspondientes.
"""

    system_prompt = build_cached_system_prompt(args.repo)
    full_text = call_anthropic_safe(
        client, model, [{"role": "user", "content": user_prompt}],
        system_prompt, max_tokens, effort=effort, stream=args.stream
    )
    
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"\n[OK] Código sintetizado guardado en: {out_path} ({len(full_text)} caracteres)")
    elif not args.stream:
        print("\n" + "=" * 80)
        print(full_text)
        print("=" * 80)
        
    return full_text

def handle_audit(args, client):
    """
    Audita un parche o diff con Opus 5.5.
    """
    model = args.model or "claude-opus-5-5"
    diff_path = Path(args.diff)
    if not diff_path.exists():
        print(f"ERROR: Archivo diff no encontrado: {diff_path}")
        sys.exit(1)
        
    diff_content = diff_path.read_text(encoding="utf-8", errors="ignore")
    print(f"\n[AUDITOR TÉCNICO {model}] Auditando diff ({len(diff_content)} caracteres)...")
    
    user_prompt = f"""AUDITORÍA TÉCNICA PRE-MERGE:
Diff a auditar:
```diff
{diff_content[:15000]}
```

Verifica con máximo rigor de ingeniería:
1. Cumplimiento del AISLAMIENTO SAGRADO (cero referencias a <IP_PRODUCCION> o releases no autorizadas).
2. Seguridad de Credenciales y Secretos (cero API keys, DSNs o contraseñas en duro).
3. Calidad de Código y Tipos (manejo de nulls, race conditions, inyecciones SQL).
4. Conclusión categórica: APROBADO o RECHAZADO con justificación línea por línea.
"""

    system_prompt = build_cached_system_prompt()
    full_text = call_anthropic_safe(
        client, model, [{"role": "user", "content": user_prompt}],
        system_prompt, max_tokens=args.max_tokens, effort="low"
    )
    
    print("\n" + "=" * 80)
    print("VEREDICTO DE AUDITORÍA:")
    print(full_text)
    print("=" * 80)

def handle_workflow(args, client):
    """
    Ejecuta el Flujo de Trabajo Extendido Multietapa en Cascada (The Quad-Brain Pipeline).
    Etapa 1: Arquitectura / Plan (Opus 5.5 o Fable 5.1)
    Etapa 2: Síntesis de Código Quirúrgico (Sonnet 5.5)
    Etapa 3: Playbook Local para Antigravity / Gemini 3.8
    Etapa 4: Criterios de Aceptación (DoD) y Rollback
    """
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = "".join([c if c.isalnum() else "_" for c in args.goal[:35]]).strip("_")
    workflow_folder = WORKFLOWS_DIR / f"{ts}_{slug}"
    workflow_folder.mkdir(parents=True, exist_ok=True)
    
    orchestrator_model = args.orchestrator or ("claude-fable-5-1" if args.strategic else "claude-opus-5-5")
    coder_model = args.coder or "claude-sonnet-5-5"
    effort = args.effort or "medium"
    
    print("=" * 70)
    print(">>> INICIANDO WORKFLOW MULTIETAPA EXTENDIDO (KADI v3.0)")
    print(f"  * Objetivo:     {args.goal}")
    print(f"  * Repositorio:  {args.repo or 'Ecosistema General'}")
    print(f"  * Orquestador:  {orchestrator_model}")
    print(f"  * Sintetizador: {coder_model}")
    print(f"  * Ejecutor:     GEMINI 3.8 / ANTIGRAVITY (Local Windows NTFS)")
    print(f"  * Directorio:   {workflow_folder}")
    print("=" * 70)

    
    system_prompt = build_cached_system_prompt(args.repo)
    stages_log = []
    
    # ETAPA 1: Plan Arquitectónico / Estratégico
    print(f"\n[FASE 1/4] Generación de Plan Maestro con {orchestrator_model}...")
    plan_prompt = f"""MISIÓN INTEGRAL:
Objetivo: {args.goal}
Repositorio: {args.repo or 'Ecosistema General KADI'}

Como Arquitecto Maestro, descompón la misión en un DAG determinista:
1. Análisis del problema y especificación de interfaz técnica.
2. Lista de archivos exactos a modificar o crear.
3. Especificación detallada de requerimientos para que SONNET 5.5 genere el código sin ambigüedad.
4. Criterios de compatibilidad con el stack existente.
"""
    plan_res = call_anthropic_safe(
        client, orchestrator_model, [{"role": "user", "content": plan_prompt}],
        system_prompt, max_tokens=16384, effort=effort
    )
    with open(workflow_folder / "01_PLAN_ARQUITECTONICO.md", "w", encoding="utf-8") as f:
        f.write(plan_res)
    stages_log.append(f"# WORKFLOW: {args.goal}\n\n## FASE 1: PLAN ARQUITECTÓNICO ({orchestrator_model})\n{plan_res}\n")
    
    # ETAPA 2: Síntesis de Código con Sonnet 5.5
    print(f"\n[FASE 2/4] Síntesis Quirúrgica de Código de Élite con {coder_model}...")
    code_prompt = f"""A partir del plan arquitectónico aprobado:
{plan_res[:5000]}

Genera la implementación técnica completa:
- Código fuente íntegro de controladores, servicios, modelos y componentes.
- Migraciones de base de datos DDL / Prisma schema completas.
- Pruebas unitarias y de integración.
DIRECTIVA: Cero placeholders. Código 100% de grado de producción.
"""
    code_res = call_anthropic_safe(
        client, coder_model, [{"role": "user", "content": code_prompt}],
        system_prompt, max_tokens=16384, effort="low"
    )
    with open(workflow_folder / "02_CODIGO_SINTETIZADO.md", "w", encoding="utf-8") as f:
        f.write(code_res)
    stages_log.append(f"## FASE 2: CÓDIGO FUENTE SINTETIZADO ({coder_model})\n{code_res}\n")
    
    # ETAPA 3: Playbook Local para Antigravity (Gemini 3.8)
    print("\n[FASE 3/4] Generación del Playbook Operativo para Antigravity (Gemini 3.8)...")
    playbook_prompt = f"""Con base en el código sintetizado para '{args.goal}':
Genera el Playbook Operativo de Ejecución Local para ANTIGRAVITY (Gemini 3.8 en Windows NTFS):
1. Rutas exactas en disco donde se deben escribir los archivos.
2. Comandos de terminal exactos de PowerShell (ej. 'npm run lint', 'cargo check', 'php artisan test').
3. Verificaciones de integridad pre y post-ejecución.
"""
    playbook_res = call_anthropic_safe(
        client, "claude-opus-5-5", [{"role": "user", "content": playbook_prompt}],
        system_prompt, max_tokens=8192, effort="low"
    )
    with open(workflow_folder / "03_PLAYBOOK_ANTIGRAVITY.md", "w", encoding="utf-8") as f:
        f.write(playbook_res)
    stages_log.append(f"## FASE 3: PLAYBOOK LOCAL ANTIGRAVITY (GEMINI 3.8)\n{playbook_res}\n")
    
    # ETAPA 4: Matriz de Aceptación (DoD) y Rollback
    print("\n[FASE 4/4] Definición de Criterios de Aceptación y Plan de Rollback...")
    audit_prompt = f"""Define los criterios de salida de la misión '{args.goal}':
1. Checklist estricto de Definition of Done (DoD).
2. Pruebas de no-regresión.
3. Plan de Contingencia y Rollback en caso de fallo.
"""
    audit_res = call_anthropic_safe(
        client, "claude-opus-5-5", [{"role": "user", "content": audit_prompt}],
        system_prompt, max_tokens=8192, effort="low"
    )
    with open(workflow_folder / "04_CRITERIOS_ACEPTACION_Y_ROLLBACK.md", "w", encoding="utf-8") as f:
        f.write(audit_res)
    stages_log.append(f"## FASE 4: CRITERIOS DE ACEPTACIÓN Y ROLLBACK\n{audit_res}\n")
    
    consolidated_path = workflow_folder / "REPORTE_CONSOLIDADO_WORKFLOW.md"
    with open(consolidated_path, "w", encoding="utf-8") as f:
        f.write("\n---\n\n".join(stages_log))
        
    print("\n" + "=" * 70)
    print("[OK] WORKFLOW EXTENDIDO COMPLETADO EXITOSAMENTE")
    print(f"Directorio de artefactos: {workflow_folder}")
    print(f"Reporte consolidado:      {consolidated_path}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="KADI Brain Orchestrator v3.0 (Enterprise Quad-Brain Engine)")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    
    # Subcommand: plan
    p_plan = subparsers.add_parser("plan", help="Generar plan de desarrollo con Opus 5.5")
    p_plan.add_argument("--goal", required=True, help="Objetivo de la misión")
    p_plan.add_argument("--repo", default=None, help="Repositorio objetivo")
    p_plan.add_argument("--context", default=None, help="Contexto o notas adicionales")
    p_plan.add_argument("--model", default="claude-opus-5-5", help="Modelo Anthropic")
    p_plan.add_argument("--profile", choices=["consult", "code", "agent", "massive"], default="agent", help="Perfil de tokens")
    p_plan.add_argument("--effort", choices=["low", "medium", "high"], default="medium", help="Nivel de esfuerzo en pensamiento")
    p_plan.add_argument("--max-tokens", type=int, default=None, help="Sobrescribir tokens máximos")
    p_plan.add_argument("--stream", action="store_true", help="Activar streaming en consola")
    p_plan.add_argument("--output", default=None, help="Ruta de guardado .md")
    
    # Subcommand: strategy
    p_strat = subparsers.add_parser("strategy", help="Emitir directiva estratégica con Fable 5.1")
    p_strat.add_argument("--topic", required=True, help="Tema o iniciativa de negocio")
    p_strat.add_argument("--context", default=None, help="Contexto adicional")
    p_strat.add_argument("--model", default="claude-fable-5-1", help="Modelo Anthropic")
    p_strat.add_argument("--profile", choices=["chat", "code", "agent", "deep"], default="agent", help="Perfil de tokens")
    p_strat.add_argument("--effort", choices=["low", "medium", "high"], default="low", help="Nivel de esfuerzo en pensamiento")
    p_strat.add_argument("--max-tokens", type=int, default=None, help="Sobrescribir tokens máximos")
    p_strat.add_argument("--stream", action="store_true", help="Activar streaming en consola")
    p_strat.add_argument("--output", default=None, help="Ruta de guardado .md")
    
    # Subcommand: synthesize
    p_synth = subparsers.add_parser("synthesize", help="Sintetizar código fuente con Sonnet 5.5")
    p_synth.add_argument("--spec", required=True, help="Especificación del código a generar")
    p_synth.add_argument("--plan", default=None, help="Texto o resumen del plan arquitectónico")
    p_synth.add_argument("--repo", default=None, help="Repositorio objetivo")
    p_synth.add_argument("--model", default="claude-sonnet-5-5", help="Modelo Anthropic")
    p_synth.add_argument("--profile", choices=["func", "code", "module", "massive"], default="code", help="Perfil de tokens")
    p_synth.add_argument("--effort", choices=["low", "medium", "high"], default="low", help="Nivel de esfuerzo en pensamiento")
    p_synth.add_argument("--max-tokens", type=int, default=None, help="Sobrescribir tokens máximos")
    p_synth.add_argument("--stream", action="store_true", help="Activar streaming en consola")
    p_synth.add_argument("--output", default=None, help="Ruta de guardado .md o .ts/.rs/.php")
    
    # Subcommand: audit
    p_audit = subparsers.add_parser("audit", help="Auditar diff de código con Opus 5.5")
    p_audit.add_argument("--diff", required=True, help="Ruta al archivo patch/diff")
    p_audit.add_argument("--model", default="claude-opus-5-5", help="Modelo Anthropic")
    p_audit.add_argument("--max-tokens", type=int, default=8192, help="Tokens máximos")
    
    # Subcommand: workflow
    p_wf = subparsers.add_parser("workflow", help="Workflow extendido multietapa en cascada")
    p_wf.add_argument("--goal", required=True, help="Objetivo complejo a resolver")
    p_wf.add_argument("--repo", default=None, help="Repositorio principal")
    p_wf.add_argument("--strategic", action="store_true", help="Usa Fable 5.1 como orquestador en vez de Opus 5.5")
    p_wf.add_argument("--orchestrator", default=None, help="Modelo orquestador (claude-opus-5-5 o claude-fable-5-1)")
    p_wf.add_argument("--coder", default="claude-sonnet-5-5", help="Modelo sintetizador de código (claude-sonnet-5-5)")
    p_wf.add_argument("--effort", choices=["low", "medium", "high"], default="medium", help="Esfuerzo de pensamiento")

    args = parser.parse_args()
    key = get_api_key()
    if not key:
        print("ERROR: Clave ANTHROPIC_API_KEY no encontrada.")
        sys.exit(1)
        
    client = anthropic.Anthropic(api_key=key)
    
    if args.subcommand == "plan":
        handle_plan(args, client)
    elif args.subcommand == "strategy":
        handle_strategy(args, client)
    elif args.subcommand == "synthesize":
        handle_synthesize(args, client)
    elif args.subcommand == "audit":
        handle_audit(args, client)
    elif args.subcommand == "workflow":
        handle_workflow(args, client)

if __name__ == "__main__":
    main()
