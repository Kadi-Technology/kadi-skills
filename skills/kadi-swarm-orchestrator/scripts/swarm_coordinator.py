#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""KADI Swarm v3.0.0 Apex - Kernel transaccional CLI (Edicion E2E Overpower Apex).

Uso::

    uv run scripts/swarm_coordinator.py <comando> [opciones]

Exit Codes: 0 OK | 1 error general | 2 conflicto de lock NTFS | 3 violacion de contrato
SHA-256 (Content/Shape) | 4 puertos TCP agotados | 5 violacion de frontera |
6 politica de modelos | 7 circuit breaker de auto-remediacion.

100% libreria estandar de Python 3.13. Sin dependencias externas.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ast_distiller  # noqa: E402
import preview_multiplexer as pm  # noqa: E402
from shadow_vault import ShadowVault  # noqa: E402

try:  # bloqueo a nivel de kernel: Windows NTFS (msvcrt); fallback POSIX para portabilidad
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None  # type: ignore[assignment]
    import fcntl  # type: ignore[import-not-found]

VERSION = "3.0.0"
EDITION = "E2E Overpower Apex"

EXIT_OK, EXIT_ERROR, EXIT_LOCK_CONFLICT, EXIT_CONTRACT, EXIT_PORTS = 0, 1, 2, 3, 4
EXIT_BOUNDARY, EXIT_MODEL, EXIT_CIRCUIT_BREAKER = 5, 6, 7

ORCHESTRATOR_MODELS = {"gemini-4-argon-high", "opus-5.5-xhigh"}
SUBAGENT_MODELS = {"gemini-3.8-flash-high", "sonnet-5.5-high"}
ALL_TIER_S_MODELS = ORCHESTRATOR_MODELS | SUBAGENT_MODELS

DEFAULT_TTL = 1800
REMEDIATION_TTL = 300
MAX_REMEDIATION_ATTEMPTS = 2
MUTEX_TIMEOUT_SECONDS = 10.0

STATE_DIRNAME = ".swarm_state"
STATE_JSON_FILES = ("mission.json", "locks.json", "contracts.json", "ports.json",
                    "reports.json", "remediations.json")

CLOSING_LAWS = {
    "ley_1_silencio_operativo_absoluto": (
        "PROHIBIDO ejecutar 'chrono.exe speak', scripts TTS o cualquier notificacion sonora "
        "durante o al finalizar las olas. Orquestador y subagentes operan 100% en silencio."
    ),
    "ley_2_entrega_obligatoria_manual_po": (
        "Todo reporte final del Orquestador General DEBE cerrar con la seccion titulada exactamente "
        "'MANUAL ESTRATÉGICO DE SIGUIENTES PASOS PARA EL PO': (a) Resumen de Blindaje E2E y Guia de "
        "Rollback (contratos Content/Shape, metricas del Flight Recorder, comandos rollback-agent/Git) "
        "y (b) 3-4 Caminos Estrategicos numerados con Objetivo, Beneficio de Negocio, Nivel de Riesgo "
        "(Bajo/Medio/Alto) y Prompt/Comando exacto listo para copiar y pegar."
    ),
}

# comando -> (modelos permitidos, --model obligatorio)
MODEL_POLICY: dict[str, tuple[set[str], bool]] = {
    "register-squad": (ORCHESTRATOR_MODELS, True),
    "publish-contract": (ORCHESTRATOR_MODELS, False),
    "distill-context": (ORCHESTRATOR_MODELS, False),
    "emit-remediation": (ORCHESTRATOR_MODELS, False),
    "rollback-agent": (ORCHESTRATOR_MODELS, False),
    "acquire-lock": (SUBAGENT_MODELS, True),
}
DEFAULT_POLICY: tuple[set[str], bool] = (ALL_TIER_S_MODELS, False)
NO_MUTEX_COMMANDS = {"check-preview"}


class CoordinatorError(Exception):
    """Error controlado con exit code y payload JSON."""

    def __init__(self, code: int, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.payload = {"status": "ERROR", "error": message, **extra}


class KadiArgumentParser(argparse.ArgumentParser):
    """argparse usa exit 2 por defecto, que aqui significa 'conflicto de lock'. Se fuerza 1."""

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        raise SystemExit(EXIT_ERROR)


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def norm_path(path: Path) -> str:
    """Normaliza a minusculas con separadores del SO (NTFS case-insensitive)."""
    return str(path).lower().replace("/", os.sep)


def is_within(child: str, parent: str) -> bool:
    return child == parent or child.startswith(parent + os.sep)


def atomic_write_json(path: Path, data: Any, tmp_dir: Path | None = None) -> None:
    """Reemplazo atomico: temp en .swarm_state + flush + fsync + os.replace."""
    tmp_dir = tmp_dir or path.parent
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", dir=tmp_dir, suffix=".tmp")
    try:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except BaseException:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


class Mutex:
    """Mutex de kernel sobre ``mutex.lock`` (msvcrt.locking LK_NBLCK) con backoff exponencial + jitter."""

    def __init__(self, path: Path, timeout: float = MUTEX_TIMEOUT_SECONDS) -> None:
        self.path, self.timeout, self.fd = path, timeout, -1

    def __enter__(self) -> "Mutex":
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
        deadline = time.monotonic() + self.timeout
        attempt = 0
        while True:
            try:
                os.lseek(self.fd, 0, os.SEEK_SET)
                if msvcrt is not None:
                    msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                else:  # pragma: no cover
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    os.close(self.fd)
                    raise CoordinatorError(EXIT_ERROR, f"timeout de {self.timeout}s esperando mutex.lock") from None
                delay = min(0.25, 0.005 * (2 ** attempt))
                time.sleep(delay + random.uniform(0, delay))  # exponencial + jitter
                attempt += 1

    def __exit__(self, *exc: object) -> None:
        try:
            os.lseek(self.fd, 0, os.SEEK_SET)
            if msvcrt is not None:
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover
                fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)


class Ctx:
    """Contexto de ejecucion: workspace + acceso al estado transaccional."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.state = self.workspace / STATE_DIRNAME

    def load(self, name: str, default: Any) -> Any:
        path = self.state / name
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, name: str, data: Any) -> None:
        atomic_write_json(self.state / name, data, self.state)

    def resolve(self, raw: str) -> Path:
        return (self.workspace / raw).resolve()

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.workspace).as_posix()
        except ValueError:
            return path.as_posix()

    def inside_workspace(self, path: Path) -> Path:
        n = norm_path(path)
        if not is_within(n, norm_path(self.workspace)):
            raise CoordinatorError(EXIT_ERROR, f"ruta fuera del workspace: {path}")
        if is_within(n, norm_path(self.state)):
            raise CoordinatorError(EXIT_ERROR, f"ruta reservada del motor (.swarm_state): {path}")
        return path


def check_model(command: str, model: str | None, allow_legacy: bool) -> None:
    allowed, required = MODEL_POLICY.get(command, DEFAULT_POLICY)
    if model is None:
        if required:
            raise CoordinatorError(EXIT_MODEL, f"'{command}' exige --model Tier S: {sorted(allowed)}")
        return
    if model.strip().lower() == "inherit":
        raise CoordinatorError(EXIT_MODEL, "Model 'inherit' esta prohibido (Ley Anti-Herencia)", model=model)
    if model in allowed or allow_legacy:
        return
    raise CoordinatorError(
        EXIT_MODEL, f"modelo no autorizado '{model}' para '{command}'",
        model=model, allowed=sorted(allowed), hint="--allow-legacy solo para migraciones",
    )


# --------------------------------------------------------------------------- #
# Locks
# --------------------------------------------------------------------------- #
def prune_stale_locks(locks: dict[str, Any]) -> list[dict[str, Any]]:
    now = time.time()
    pruned = []
    for agent_id in [a for a, lk in locks.items() if lk["expires_at"] <= now]:
        lk = locks.pop(agent_id)
        pruned.append({"agent_id": agent_id, "expired_seconds_ago": round(now - lk["expires_at"], 2)})
    return pruned


def classify_conflict(requested: str, held: str) -> str | None:
    if requested == held:
        return "exact"
    if requested.startswith(held + os.sep):
        return "descendant"  # hijo dentro de un directorio bloqueado
    if held.startswith(requested + os.sep):
        return "ascendant"  # padre sobre un archivo/subdirectorio bloqueado
    return None


def do_acquire(ctx: Ctx, agent_id: str, model: str, paths: list[str], ttl: int) -> tuple[int, dict[str, Any]]:
    locks = ctx.load("locks.json", {})
    pruned = prune_stale_locks(locks)  # limpieza silenciosa previa
    if pruned:
        ctx.save("locks.json", locks)
    if ttl <= 0:
        raise CoordinatorError(EXIT_ERROR, "--ttl debe ser > 0")

    display: list[Path] = []
    normalized: list[str] = []
    for raw in paths:
        absolute = ctx.inside_workspace(ctx.resolve(raw))
        n = norm_path(absolute)
        if n not in normalized:
            normalized.append(n)
            display.append(absolute)

    now = time.time()
    conflicts: list[dict[str, Any]] = []
    for other_id, lk in locks.items():
        if other_id == agent_id:
            continue
        for req in normalized:
            for held in lk["normalized_paths"]:
                ctype = classify_conflict(req, held)
                if ctype:
                    conflicts.append({
                        "conflict_type": ctype, "blocking_agent": other_id,
                        "blocking_model": lk["model"], "conflicting_path": held,
                        "requested_path": req,
                        "remaining_ttl_seconds": round(max(lk["expires_at"] - now, 0), 2),
                    })
    if conflicts:
        return EXIT_LOCK_CONFLICT, {"status": "CONFLICT", "agent_id": agent_id, **conflicts[0],
                                    "all_conflicts": conflicts}

    existing = locks.get(agent_id)
    if existing:
        new_idx = [i for i, n in enumerate(normalized)
                   if not any(is_within(n, held) for held in existing["normalized_paths"])]
        status = "EXTENDED" if new_idx else "RENEWED"  # idempotencia / heartbeat
    else:
        new_idx = list(range(len(normalized)))
        status = "GRANTED"

    shadow_info: dict[str, Any] = {"newly_captured_files": 0, "newly_captured_territories": []}
    if new_idx:
        try:  # Shadow Snapshot automatico ANTES de conceder el territorio
            manifest = ShadowVault.capture_snapshot(ctx.workspace, agent_id, [str(display[i]) for i in new_idx])
        except (ValueError, OSError) as exc:
            raise CoordinatorError(EXIT_ERROR, f"fallo al capturar shadow snapshot: {exc}") from exc
        shadow_info = {k: manifest[k] for k in ("newly_captured_files", "newly_captured_territories")}

    record = existing or {"agent_id": agent_id, "acquired_at": now, "heartbeat_count": 0,
                          "normalized_paths": [], "display_paths": []}
    for i in new_idx:
        record["normalized_paths"].append(normalized[i])
        record["display_paths"].append(str(display[i]))
    record.update({
        "model": model, "expires_at": now + ttl, "ttl": ttl,
        "shadow_manifest_path": str(ShadowVault.manifest_path(ctx.workspace, agent_id)),
    })
    if existing:
        record["heartbeat_count"] += 1
    locks[agent_id] = record
    ctx.save("locks.json", locks)
    mission = ctx.load("mission.json", {})
    mission.setdefault("agent_models", {})[agent_id] = model
    ctx.save("mission.json", mission)
    return EXIT_OK, {
        "status": status, "agent_id": agent_id, "model": model,
        "paths": record["display_paths"], "ttl": ttl, "expires_at": record["expires_at"],
        "heartbeat_count": record["heartbeat_count"], "shadow": shadow_info,
        "pruned_stale_locks": pruned,
    }


def cmd_acquire_lock(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    return do_acquire(ctx, a.agent_id, a.model, a.paths, a.ttl)


def cmd_heartbeat_lock(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    locks = ctx.load("locks.json", {})
    pruned = prune_stale_locks(locks)
    lk = locks.get(a.agent_id)
    if not lk:
        ctx.save("locks.json", locks)
        return EXIT_ERROR, {"status": "NO_ACTIVE_LOCK", "agent_id": a.agent_id,
                            "hint": "el lease expiro o nunca existio: ejecuta acquire-lock"}
    ttl = a.ttl or lk.get("ttl", DEFAULT_TTL)
    lk["expires_at"] = time.time() + ttl
    lk["ttl"] = ttl
    lk["heartbeat_count"] += 1
    ctx.save("locks.json", locks)
    return EXIT_OK, {"status": "RENEWED", "agent_id": a.agent_id, "expires_at": lk["expires_at"],
                     "heartbeat_count": lk["heartbeat_count"], "pruned_stale_locks": pruned}


def cmd_release_lock(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    locks = ctx.load("locks.json", {})
    lk = locks.pop(a.agent_id, None)
    ctx.save("locks.json", locks)
    return EXIT_OK, {"status": "RELEASED" if lk else "NO_LOCK", "agent_id": a.agent_id,
                     "released_paths": lk["display_paths"] if lk else [],
                     "active_count": len(locks),
                     "note": "la copia sombra se conserva para rollback-agent hasta cerrar la mision"}


def cmd_prune_stale_locks(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    locks = ctx.load("locks.json", {})
    pruned = prune_stale_locks(locks)
    ctx.save("locks.json", locks)
    return EXIT_OK, {"status": "PRUNED", "pruned": pruned, "active_count": len(locks)}


# --------------------------------------------------------------------------- #
# Mision y contratos
# --------------------------------------------------------------------------- #
def cmd_register_squad(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    mission_file = ctx.state / "mission.json"
    if mission_file.exists() and not a.reset:
        raise CoordinatorError(EXIT_ERROR, "ya existe una mision activa; usa --reset para reiniciar",
                               mission=ctx.load("mission.json", {}))
    if a.reset:
        for child in ctx.state.iterdir():
            if child.name == "mutex.lock":
                continue
            shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink(missing_ok=True)
    (ctx.state / "briefs").mkdir(parents=True, exist_ok=True)
    (ctx.state / "shadows").mkdir(parents=True, exist_ok=True)
    mission = {
        "mission_id": a.mission_id or "mission-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
        "orchestrator_model": a.model, "created_at": now_iso(),
        "wave_status": a.wave_status, "workspace_root": str(ctx.workspace), "version": VERSION,
    }
    ctx.save("mission.json", mission)
    ctx.save("locks.json", {})
    ctx.save("contracts.json", {})
    ctx.save("ports.json", [])
    ctx.save("reports.json", [])
    ctx.save("remediations.json", {"max_attempts": MAX_REMEDIATION_ATTEMPTS, "attempts": {},
                                   "tickets": [], "incidents": []})
    (ctx.state / "events.jsonl").touch()
    return EXIT_OK, {"status": "REGISTERED", "reset": a.reset, "mission": mission, "state_dir": str(ctx.state),
                     "closing_laws": CLOSING_LAWS}


def cmd_publish_contract(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    path = ctx.inside_workspace(ctx.resolve(a.file))
    if not path.is_file():
        raise CoordinatorError(EXIT_ERROR, f"archivo inexistente: {path}")
    hashes = ast_distiller.compute_dual_hashes(path)
    name = a.name or path.name
    contracts = ctx.load("contracts.json", {})
    contracts[name] = {
        "name": name, "schema_path": ctx.rel(path), "owner": a.owner,
        "content_sha256": hashes["content_sha256"], "shape_sha256": hashes["shape_sha256"],
        "kind": hashes["kind"], "mode": a.mode, "published_at": now_iso(),
    }
    ctx.save("contracts.json", contracts)
    return EXIT_OK, {"status": "PUBLISHED", "contract": contracts[name]}


def verify_contracts(ctx: Ctx, names: list[str] | None) -> list[dict[str, Any]]:
    contracts = ctx.load("contracts.json", {})
    selected = list(contracts) if names is None else names
    results = []
    for name in selected:
        c = contracts.get(name)
        if c is None:
            results.append({"name": name, "state": "UNKNOWN_CONTRACT"})
            continue
        path = ctx.workspace / c["schema_path"]
        base = {"name": name, "path": c["schema_path"], "mode": c["mode"], "owner": c["owner"]}
        if not path.is_file():
            results.append({**base, "state": "MISSING"})
            continue
        h = ast_distiller.compute_dual_hashes(path)
        shape_ok = h["shape_sha256"] == c["shape_sha256"]
        content_ok = h["content_sha256"] == c["content_sha256"]
        intact = shape_ok and (content_ok or c["mode"] == "structural")
        results.append({**base, "state": "INTACT" if intact else "VIOLATED",
                        "shape_changed": not shape_ok, "content_changed": not content_ok})
    return results


def cmd_verify_contract(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if not a.all and not a.name:
        raise CoordinatorError(EXIT_ERROR, "indica --name <contrato> o --all")
    results = verify_contracts(ctx, None if a.all else [a.name])
    bad = [r for r in results if r["state"] != "INTACT"]
    return (EXIT_CONTRACT if bad else EXIT_OK), {
        "status": "VIOLATION" if bad else "INTACT", "checked": len(results),
        "violations": bad, "results": results}


def cmd_distill_context(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    model = a.agent_model or (ctx.load("locks.json", {}).get(a.agent_id) or {}).get("model") or "gemini-3.8-flash-high"
    brief = ast_distiller.build_micro_brief(
        ctx.workspace, a.agent_id, a.territory, a.contracts, a.mission_goal, model,
        SCRIPT_DIR / "swarm_coordinator.py")
    out = ctx.state / "briefs" / f"{a.agent_id}_brief.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(out, brief, ctx.state)
    # salida especial: JSON comprimido listo para inyectar al subagente (ver main)
    return EXIT_OK, {"__compact__": brief, "brief_path": str(out)}


# --------------------------------------------------------------------------- #
# Puertos / preview
# --------------------------------------------------------------------------- #
def cmd_acquire_port(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    ports = ctx.load("ports.json", [])
    ports = [p for p in ports if not (p.get("pid") and not pm.pid_alive(p["pid"]))]  # purga PIDs muertos
    entry = next((p for p in ports if p["agent_id"] == a.agent_id), None)
    if entry:
        if a.pid:
            entry["pid"] = a.pid
        ctx.save("ports.json", ports)
        return EXIT_OK, {"status": "EXISTING", **entry}
    choice = pm.choose_port(a.preferred, [p["port"] for p in ports])
    if choice is None:
        ctx.save("ports.json", ports)
        return EXIT_PORTS, {"status": "PORTS_EXHAUSTED", "agent_id": a.agent_id,
                            "pool": pm.KADI_POOL, "fallback_range": "5200-5299"}
    port, origin = choice
    entry = {"port": port, "agent_id": a.agent_id, "pid": a.pid, "preferred": a.preferred,
             "acquired_at": time.time(), "health_url": f"http://{pm.LOOPBACK}:{port}{a.health_path}"}
    ports.append(entry)
    ctx.save("ports.json", ports)
    return EXIT_OK, {"status": "GRANTED", "origin": origin, **entry}


def cmd_check_preview(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if a.port:
        url = f"http://{pm.LOOPBACK}:{a.port}{a.path}"
    elif a.agent_id:
        entry = next((p for p in ctx.load("ports.json", []) if p["agent_id"] == a.agent_id), None)
        if not entry:
            raise CoordinatorError(EXIT_ERROR, f"el agente '{a.agent_id}' no tiene puerto asignado")
        url = f"http://{pm.LOOPBACK}:{entry['port']}{a.path}"
    else:
        raise CoordinatorError(EXIT_ERROR, "indica --port o --agent-id")
    result = pm.check_http(url, timeout=a.timeout)
    return (EXIT_OK if result["ok"] else EXIT_ERROR), {"status": "HTTP_200" if result["ok"] else "NOT_READY", **result}


def release_ports_for(ctx: Ctx, agent_id: str, extra_pids: list[int]) -> dict[str, Any]:
    ports = ctx.load("ports.json", [])
    mine = [p for p in ports if p["agent_id"] == agent_id]
    keep = [p for p in ports if p["agent_id"] != agent_id]
    pids = [p["pid"] for p in mine if p.get("pid")] + [x for x in extra_pids if x and x > 0]
    killed = [pm.kill_process_tree(pid) for pid in dict.fromkeys(pids)]
    ctx.save("ports.json", keep)
    return {"released_ports": [p["port"] for p in mine], "killed": killed}


def cmd_release_port(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    extra = [x for x in (a.pid, a.kill_pid) if x]
    info = release_ports_for(ctx, a.agent_id, extra)
    return EXIT_OK, {"status": "RELEASED" if info["released_ports"] else "NO_PORT", "agent_id": a.agent_id, **info}


# --------------------------------------------------------------------------- #
# Reportes, remediacion, rollback
# --------------------------------------------------------------------------- #
def cmd_submit_report(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    locks = ctx.load("locks.json", {})
    pruned = prune_stale_locks(locks)
    if pruned:
        ctx.save("locks.json", locks)
    held = locks.get(a.agent_id, {}).get("normalized_paths", [])
    violations = []
    for raw in a.artifacts:
        n = norm_path(ctx.resolve(raw))
        if not any(is_within(n, h) for h in held):
            violations.append(n)
    report = {"ts": now_iso(), "agent_id": a.agent_id, "model": a.model, "wave": a.wave,
              "status": a.status, "summary": a.summary, "artifacts": a.artifacts}

    def record(accepted: bool, code: int) -> None:
        reports = ctx.load("reports.json", [])
        reports.append({**report, "accepted": accepted, "exit_code": code})
        ctx.save("reports.json", reports)

    if violations:
        record(False, EXIT_BOUNDARY)
        return EXIT_BOUNDARY, {
            "status": "BOUNDARY_VIOLATION", "agent_id": a.agent_id, "violations": violations,
            "action": "revierte cualquier archivo tocado fuera de tu zona antes de release-lock",
            "closing_laws": CLOSING_LAWS}
    broken = [r for r in verify_contracts(ctx, None) if r["state"] != "INTACT"]
    if broken:
        record(False, EXIT_CONTRACT)
        return EXIT_CONTRACT, {"status": "CONTRACT_VIOLATION", "agent_id": a.agent_id,
                               "violations": broken, "closing_laws": CLOSING_LAWS}
    record(True, EXIT_OK)
    return EXIT_OK, {"status": "ACCEPTED", "agent_id": a.agent_id, "wave": a.wave,
                     "artifacts_verified": len(a.artifacts), "closing_laws": CLOSING_LAWS}


def cmd_emit_remediation(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    target = ctx.inside_workspace(ctx.resolve(a.file))
    rel = ctx.rel(target)
    rem = ctx.load("remediations.json", {"attempts": {}, "tickets": [], "incidents": []})
    used = rem["attempts"].get(a.agent_id, 0)
    script = SCRIPT_DIR / "swarm_coordinator.py"
    ws = f'--workspace "{ctx.workspace}"'
    rollback_cmd = f'uv run "{script}" rollback-agent --agent-id {a.agent_id} {ws}'
    if used >= MAX_REMEDIATION_ATTEMPTS:
        rem["incidents"].append({"ts": now_iso(), "agent_id": a.agent_id, "file": rel, "error": a.error,
                                 "event": "CIRCUIT_BREAKER_OPEN"})
        ctx.save("remediations.json", rem)
        return EXIT_CIRCUIT_BREAKER, {
            "status": "CIRCUIT_BREAKER_OPEN", "agent_id": a.agent_id, "attempts_used": used,
            "max_attempts": MAX_REMEDIATION_ATTEMPTS, "next_action": "rollback-agent",
            "rollback_command": rollback_cmd}
    attempt = used + 1
    reopen_cmd_model = "<model-del-agente>"
    ticket = {
        "ticket_id": f"{a.agent_id}-r{attempt}", "attempt": attempt, "max_attempts": MAX_REMEDIATION_ATTEMPTS,
        "agent_id": a.agent_id, "file": rel, "line": a.line, "failed_assertion": a.assertion,
        "error": a.error, "expected_diff": a.expected_diff, "issued_at": now_iso(),
        "reopen_ttl_seconds": a.ttl,
    }
    rem["attempts"][a.agent_id] = attempt
    rem["tickets"].append(ticket)
    ctx.save("remediations.json", rem)
    payload: dict[str, Any] = {"status": "TICKET_ISSUED", "ticket": ticket,
                               "attempts_remaining": MAX_REMEDIATION_ATTEMPTS - attempt}
    model = (a.agent_model or (ctx.load("locks.json", {}).get(a.agent_id) or {}).get("model")
             or ctx.load("mission.json", {}).get("agent_models", {}).get(a.agent_id))
    if not model:
        reports = [r for r in ctx.load("reports.json", []) if r["agent_id"] == a.agent_id and r.get("model")]
        model = reports[-1]["model"] if reports else None
    payload["reopen_command"] = (
        f'uv run "{script}" acquire-lock --agent-id {a.agent_id} --model {model or reopen_cmd_model} '
        f'--paths "{rel}" --ttl {a.ttl} {ws}')
    if a.reopen:
        if model:
            code, result = do_acquire(ctx, a.agent_id, model, [rel], a.ttl)
            payload["reopen"] = {"exit_code": code, **result}
            if code != EXIT_OK:
                return code, payload
        else:
            payload["reopen"] = {"skipped": "modelo del agente desconocido; usa --agent-model"}
    if a.out:
        out = ctx.resolve(a.out)
        atomic_write_json(out, ticket, out.parent)
        payload["ticket_file"] = str(out)
    return EXIT_OK, payload


def cmd_rollback_agent(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    try:
        restore = ShadowVault.restore(ctx.workspace, a.agent_id)
    except FileNotFoundError as exc:
        raise CoordinatorError(EXIT_ERROR, str(exc)) from exc
    locks = ctx.load("locks.json", {})
    lk = locks.pop(a.agent_id, None)
    ctx.save("locks.json", locks)
    ports = release_ports_for(ctx, a.agent_id, [])
    return EXIT_OK, {"status": "ROLLED_BACK", "agent_id": a.agent_id, **restore,
                     "released_lock": bool(lk), **ports}


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def flight_recorder_metrics(ctx: Ctx) -> dict[str, Any]:
    path = ctx.state / "events.jsonl"
    events: list[dict[str, Any]] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    by_cmd: dict[str, int] = {}
    by_exit: dict[str, int] = {}
    for e in events:
        by_cmd[e["command"]] = by_cmd.get(e["command"], 0) + 1
        by_exit[str(e["exit_code"])] = by_exit.get(str(e["exit_code"]), 0) + 1
    durations = [e["duration_ms"] for e in events if "duration_ms" in e]
    return {
        "total_events": len(events), "by_command": by_cmd, "by_exit_code": by_exit,
        "non_zero_exits": sum(v for k, v in by_exit.items() if k != "0"),
        "avg_duration_ms": round(sum(durations) / len(durations), 3) if durations else 0.0,
        "last_events": events[-5:],
    }


def cmd_status_report(ctx: Ctx, a: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    mission = ctx.load("mission.json", {})
    if a.wave_status:
        mission["wave_status"] = a.wave_status
        ctx.save("mission.json", mission)
    locks = ctx.load("locks.json", {})
    pruned = prune_stale_locks(locks)
    if pruned:
        ctx.save("locks.json", locks)
    now = time.time()
    ports = ctx.load("ports.json", [])
    contracts = verify_contracts(ctx, None)
    intact = all(c["state"] == "INTACT" for c in contracts)
    rem = ctx.load("remediations.json", {"attempts": {}, "tickets": [], "incidents": []})
    ready = not locks and not ports and intact
    return EXIT_OK, {
        "status": "READY_FOR_HANDOFF" if ready else "IN_PROGRESS",
        "version": VERSION, "mission": mission,
        "active_locks": len(locks),
        "locks": [{"agent_id": k, "model": v["model"], "paths": v["display_paths"],
                   "remaining_ttl_seconds": round(max(v["expires_at"] - now, 0), 1),
                   "heartbeat_count": v["heartbeat_count"]} for k, v in locks.items()],
        "pruned_stale_locks": pruned,
        "active_ports": len(ports), "ports": ports,
        "contracts_all_intact": intact, "contracts": contracts,
        "remediations": {"attempts": rem["attempts"], "tickets": len(rem["tickets"]),
                         "incidents": len(rem["incidents"])},
        "reports": len(ctx.load("reports.json", [])),
        "flight_recorder": flight_recorder_metrics(ctx),
        "handoff_reminder": ("Ola 3: exige active_locks == 0, active_ports == 0 y contratos INTACT. "
                             "Cierra con 'MANUAL ESTRATÉGICO DE SIGUIENTES PASOS PARA EL PO'."),
        "closing_laws": CLOSING_LAWS,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
HANDLERS: dict[str, Callable[[Ctx, argparse.Namespace], tuple[int, dict[str, Any]]]] = {
    "register-squad": cmd_register_squad, "publish-contract": cmd_publish_contract,
    "verify-contract": cmd_verify_contract, "distill-context": cmd_distill_context,
    "acquire-lock": cmd_acquire_lock, "heartbeat-lock": cmd_heartbeat_lock,
    "release-lock": cmd_release_lock, "prune-stale-locks": cmd_prune_stale_locks,
    "acquire-port": cmd_acquire_port, "check-preview": cmd_check_preview,
    "release-port": cmd_release_port, "submit-report": cmd_submit_report,
    "emit-remediation": cmd_emit_remediation, "rollback-agent": cmd_rollback_agent,
    "status-report": cmd_status_report,
}


def build_parser() -> argparse.ArgumentParser:
    parser = KadiArgumentParser(prog="swarm_coordinator.py",
                                description=f"KADI Swarm v{VERSION} {EDITION} - kernel transaccional")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=KadiArgumentParser)

    def cmd(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--workspace", default=os.getcwd(), help="raiz del workspace (default: cwd)")
        p.add_argument("--model", default=None, help="modelo Tier S del invocador")
        p.add_argument("--allow-legacy", action="store_true", help="permite modelos legacy (solo migraciones)")
        return p

    p = cmd("register-squad", "inicializa .swarm_state/ y registra la mision")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--mission-id", default=None)
    p.add_argument("--wave-status", default="WAVE_0_FREEZE")

    p = cmd("publish-contract", "congela Content-SHA256 y Shape-SHA256 de un archivo")
    p.add_argument("--file", required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--owner", default="orchestrator")
    p.add_argument("--mode", choices=["strict", "structural"], default="strict")

    p = cmd("verify-contract", "verifica contratos contra el disco")
    p.add_argument("--name", default=None)
    p.add_argument("--all", action="store_true")

    p = cmd("distill-context", "genera el micro-brief AST para un subagente")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--territory", nargs="+", required=True)
    p.add_argument("--contracts", nargs="*", default=[])
    p.add_argument("--mission-goal", required=True)
    p.add_argument("--agent-model", default=None, help="modelo del subagente (default: el de su lock)")

    p = cmd("acquire-lock", "adquiere/renueva un lock con shadow snapshot")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--paths", nargs="+", required=True)
    p.add_argument("--ttl", type=int, default=DEFAULT_TTL)

    p = cmd("heartbeat-lock", "renueva el TTL de los locks de un agente")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--ttl", type=int, default=0)

    p = cmd("release-lock", "libera los locks de un agente")
    p.add_argument("--agent-id", required=True)

    cmd("prune-stale-locks", "purga locks expirados")

    p = cmd("acquire-port", "asigna un puerto TCP libre en 127.0.0.1")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--preferred", type=int, default=None)
    p.add_argument("--pid", type=int, default=None, help="PID del servidor efimero (para el guardian)")
    p.add_argument("--health-path", default="/")

    p = cmd("check-preview", "verifica HTTP 200 en vivo del servidor efimero")
    p.add_argument("--agent-id", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--path", default="/")
    p.add_argument("--timeout", type=float, default=10.0)

    p = cmd("release-port", "libera el puerto y mata el arbol PID")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--pid", type=int, default=None)
    p.add_argument("--kill-pid", type=int, default=None, help="PID adicional a terminar (taskkill /F /T)")

    p = cmd("submit-report", "registra el reporte (verifica fronteras y contratos)")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--wave", choices=["0", "1", "2", "2.5", "3"], default="1")
    p.add_argument("--status", default="DONE")
    p.add_argument("--summary", default="")
    p.add_argument("--artifacts", nargs="*", default=[])

    p = cmd("emit-remediation", "emite un ticket de auto-remediacion (max 2 intentos)")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--error", required=True)
    p.add_argument("--line", type=int, default=None)
    p.add_argument("--assertion", default=None)
    p.add_argument("--expected-diff", default=None)
    p.add_argument("--ttl", type=int, default=REMEDIATION_TTL)
    p.add_argument("--reopen", action="store_true", help="reabre el lock sobre el archivo afectado")
    p.add_argument("--agent-model", default=None)
    p.add_argument("--out", default=None, help="escribe el ticket en este archivo (remediation_ticket.json)")

    p = cmd("rollback-agent", "restaura el territorio del agente desde su shadow snapshot")
    p.add_argument("--agent-id", required=True)

    p = cmd("status-report", "dashboard JSON completo de la mision")
    p.add_argument("--wave-status", default=None)
    return parser


def log_event(ctx: Ctx, args: argparse.Namespace, duration_ms: float, code: int) -> None:
    if not ctx.state.is_dir():
        return
    event = {"ts": now_iso(), "command": args.command, "agent_id": getattr(args, "agent_id", None),
             "model": getattr(args, "model", None), "duration_ms": round(duration_ms, 3), "exit_code": code}
    with (ctx.state / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")  # Flight Recorder append-only


def execute(args: argparse.Namespace, ctx: Ctx) -> tuple[int, dict[str, Any]]:
    try:
        check_model(args.command, args.model, args.allow_legacy)
        if args.command == "register-squad":
            ctx.state.mkdir(parents=True, exist_ok=True)
        elif not (ctx.state / "mission.json").is_file():
            raise CoordinatorError(EXIT_ERROR, f"mision no registrada en {ctx.workspace}; ejecuta register-squad")
        handler = HANDLERS[args.command]
        if args.command in NO_MUTEX_COMMANDS:
            return handler(ctx, args)
        with Mutex(ctx.state / "mutex.lock"):
            return handler(ctx, args)
    except CoordinatorError as exc:
        return exc.code, exc.payload
    except (OSError, ValueError, KeyError) as exc:
        return EXIT_ERROR, {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    ctx = Ctx(Path(args.workspace))
    started = time.perf_counter()
    code, payload = execute(args, ctx)
    log_event(ctx, args, (time.perf_counter() - started) * 1000, code)
    if "__compact__" in payload:  # distill-context: JSON comprimido para inyeccion directa
        print(json.dumps(payload["__compact__"], separators=(",", ":"), ensure_ascii=False))
    else:
        payload.setdefault("exit_code", code)
        payload["command"] = args.command
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
