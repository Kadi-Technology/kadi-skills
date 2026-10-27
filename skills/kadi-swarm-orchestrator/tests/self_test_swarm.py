#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""KADI Swarm v3.0.0 Apex - Suite E2E de auto-verificacion.

Simula una mision completa de 4 olas sobre un workspace temporal: registro, contratos
duales, locks jerarquicos, colisiones, destilacion AST, edicion, violacion de frontera,
rollback atomico, remediacion con circuit breaker, puertos TCP reales, readiness HTTP,
guardian PID y cierre. Exit Code 0 solo si TODAS las aserciones pasan.

Uso: uv run tests/self_test_swarm.py
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
COORD = SCRIPTS / "swarm_coordinator.py"
sys.path.insert(0, str(SCRIPTS))

import ast_distiller as ad  # noqa: E402
import preview_multiplexer as pm  # noqa: E402
from shadow_vault import ShadowVault  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8")

ORCH = "gemini-4-argon-high"
ORCH2 = "opus-5.5-xhigh"
SUB = "gemini-3.8-flash-high"
SUB2 = "sonnet-5.5-high"

RESULTS = {"pass": 0, "fail": 0}


def check(name: str, cond: bool, detail: object = "") -> None:
    RESULTS["pass" if cond else "fail"] += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  -> {detail}"))


def section(title: str) -> None:
    print(f"\n== {title}")


def coord(ws: Path, *args: str, timeout: int = 90) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(COORD), *args, "--workspace", str(ws)],
                          capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
        data = {"raw": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, data


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def dual(path: Path) -> dict:
    return ad.compute_dual_hashes(path)


# --------------------------------------------------------------------------- #
def test_dual_hashes(tmp: Path) -> None:
    section("Contratos duales Content-Hash vs Shape-Hash")
    j = tmp / "h" / "p.json"
    write(j, json.dumps([{"name": "a", "year": 2024, "ok": True, "score": 1.5, "x": None}]))
    h1 = dual(j)
    write(j, json.dumps([{"name": "a", "year": 2024, "ok": True, "score": 1.5, "x": None},
                         {"name": "zzz", "year": 1999, "ok": False, "score": 9.25, "x": None}]))
    h2 = dual(j)
    check("JSON: agregar registro valido cambia content", h1["content_sha256"] != h2["content_sha256"])
    check("JSON: agregar registro valido NO cambia shape", h1["shape_sha256"] == h2["shape_sha256"])
    write(j, json.dumps([{"name": "a", "year": 2024, "ok": True, "score": 1.5, "x": None, "new_key": 1}]))
    check("JSON: clave nueva SI cambia shape", dual(j)["shape_sha256"] != h1["shape_sha256"])
    write(j, '{"b": 1, "a": "s"}')
    s1 = dual(j)["shape_sha256"]
    write(j, '{"a": "t", "b": 7}')
    check("JSON: orden de claves y valores irrelevantes", dual(j)["shape_sha256"] == s1)
    write(j, "{not json")
    bad = dual(j)
    check("JSON invalido: shape == content", bad["shape_sha256"] == bad["content_sha256"])

    f_lf, f_crlf = tmp / "h" / "lf.txt", tmp / "h" / "crlf.txt"
    f_lf.write_bytes(b"a\nb\n")
    f_crlf.write_bytes(b"a\r\nb\r\n")
    check("CRLF normalizado a LF en content_sha256", dual(f_lf)["content_sha256"] == dual(f_crlf)["content_sha256"])
    check("Archivo opaco: shape == content", dual(f_lf)["shape_sha256"] == dual(f_lf)["content_sha256"])

    py = tmp / "h" / "m.py"
    write(py, "def pub(a, b: int) -> str:\n    return 'x'\n\nclass C:\n    def m(self, z): return 1\n    def _p(self): pass\n")
    p1 = dual(py)["shape_sha256"]
    write(py, "def pub(a, b: int) -> str:\n    return 'otro cuerpo'\n\ndef _priv(): pass\n\nclass C:\n    def m(self, z): return 2\n    def _p(self): pass\n")
    check("PY: cambio de cuerpo/privados NO cambia shape", dual(py)["shape_sha256"] == p1)
    write(py, "def pub(a, b: int) -> str:\n    return 'x'\n\ndef nueva(): pass\n\nclass C:\n    def m(self, z): return 1\n")
    check("PY: nueva funcion publica SI cambia shape", dual(py)["shape_sha256"] != p1)
    write(py, "def pub(a, b: int) -> int:\n    return 1\n\nclass C:\n    def m(self, z): return 1\n")
    check("PY: anotacion de retorno SI cambia shape", dual(py)["shape_sha256"] != p1)

    js = tmp / "h" / "l.mjs"
    write(js, "// export function fake() {}\nexport function render(a, b) { return 1 }\nexport const VERSION = 'x';\n")
    j1 = dual(js)["shape_sha256"]
    write(js, "// export function fake() {}\nexport function render(a,   b) { return 'otro' }\nexport const VERSION = 'y';\n")
    check("JS: cuerpo/valores y comentarios NO cambian shape", dual(js)["shape_sha256"] == j1)
    write(js, "export function render(a, b) { return 1 }\nexport const VERSION = 'x';\nexport function extra() {}\n")
    check("JS: nuevo export SI cambia shape", dual(js)["shape_sha256"] != j1)
    cjs = tmp / "h" / "c.js"
    write(cjs, "module.exports = { a: 1 };\n")
    check("JS: module.exports detectado", "module.exports" in ad.extract_skeleton(cjs)["exports"])
    ts = tmp / "h" / "t.ts"
    write(ts, "export interface A { x: number }\nexport type B = string;\nexport class K extends Base {}\n")
    exp = ad.extract_skeleton(ts)["exports"]
    check("TS: interface/type/class detectados", {"interface A", "type B", "class K extends Base"} <= set(exp), exp)

    css = tmp / "h" / "s.css"
    write(css, ":root { --bg: #000; --glass: rgba(0,0,0,.5); }\n.card { color: var(--bg); }\n.btn.primary { margin: 1.5px }\n")
    c1 = dual(css)["shape_sha256"]
    write(css, ":root { --bg: #fff; --glass: rgba(1,1,1,.9); }\n.card { color: red; }\n.btn.primary { margin: 3px }\n")
    check("CSS: valores de tokens NO cambian shape", dual(css)["shape_sha256"] == c1)
    write(css, ":root { --bg: #000; --glass: rgba(0,0,0,.5); --nuevo: 1; }\n.card {}\n.btn.primary {}\n")
    check("CSS: token nuevo SI cambia shape", dual(css)["shape_sha256"] != c1)
    skel = ad.extract_skeleton(css)
    check("CSS: tokens y clases extraidos", "--bg" in skel["tokens"] and {"card", "btn", "primary"} <= set(skel["classes"]), skel)


def test_vault_unit(tmp: Path) -> None:
    section("Shadow Vault (unitario)")
    ws = tmp / "vault"
    (ws / ".swarm_state").mkdir(parents=True)
    write(ws / "t" / "a.txt", "original")
    ShadowVault.capture_snapshot(ws, "ag", ["t"])
    write(ws / "t" / "a.txt", "editado")
    m = ShadowVault.capture_snapshot(ws, "ag", ["t"])  # heartbeat: NO debe re-capturar
    check("Snapshot idempotente (no recaptura territorios)", m["newly_captured_files"] == 0)
    write(ws / "t" / "n.txt", "nuevo")
    res = ShadowVault.restore(ws, "ag")
    check("Restore devuelve original y borra nuevos",
          (ws / "t" / "a.txt").read_text() == "original" and not (ws / "t" / "n.txt").exists(), res)
    check("Restore < 500 ms", res["elapsed_ms"] < 500, res["elapsed_ms"])
    try:
        ShadowVault.capture_snapshot(ws, "ag2", [str(tmp / "afuera")])
        check("Ruta fuera del workspace rechazada", False)
    except ValueError:
        check("Ruta fuera del workspace rechazada", True)


def test_model_policy(tmp: Path) -> None:
    section("Politica de modelos Tier S (Exit Code 6)")
    ws = tmp / "ws_models"
    ws.mkdir()
    check("register-squad con 'inherit' -> 6", coord(ws, "register-squad", "--model", "inherit")[0] == 6)
    check("register-squad con modelo de subagente -> 6", coord(ws, "register-squad", "--model", SUB)[0] == 6)
    check("register-squad sin --model -> 6", coord(ws, "register-squad")[0] == 6)
    check("register-squad con modelo legacy -> 6", coord(ws, "register-squad", "--model", "gpt-4")[0] == 6)
    check("--allow-legacy NO permite 'inherit'",
          coord(ws, "register-squad", "--model", "inherit", "--allow-legacy")[0] == 6)
    check("register-squad con Opus 5.5 xHigh -> 0", coord(ws, "register-squad", "--model", ORCH2)[0] == 0)
    check("acquire-lock con modelo de orquestador -> 6",
          coord(ws, "acquire-lock", "--agent-id", "x", "--paths", "a", "--model", ORCH)[0] == 6)
    check("acquire-lock con modelo legacy -> 6",
          coord(ws, "acquire-lock", "--agent-id", "x", "--paths", "a", "--model", "claude-3")[0] == 6)
    check("acquire-lock sin --model -> 6", coord(ws, "acquire-lock", "--agent-id", "x", "--paths", "a")[0] == 6)
    check("acquire-lock con Sonnet 5.5 High -> 0",
          coord(ws, "acquire-lock", "--agent-id", "x", "--paths", "a", "--model", SUB2)[0] == 0)
    check("acquire-lock legacy + --allow-legacy -> 0",
          coord(ws, "acquire-lock", "--agent-id", "y", "--paths", "b", "--model", "claude-3", "--allow-legacy")[0] == 0)
    check("publish-contract con modelo de subagente -> 6",
          coord(ws, "publish-contract", "--file", "a", "--model", SUB)[0] == 6)
    check("Argumentos invalidos -> Exit 1 (no 2)", coord(ws, "acquire-lock")[0] == 1)
    check("Comando sin mision registrada -> 1", coord(tmp / "ws_models_none", "status-report")[0] == 1)


# --------------------------------------------------------------------------- #
def test_mission(tmp: Path) -> None:
    section("Mision completa de 4 olas")
    ws = tmp / "mission"
    write(ws / "_data" / "projects.json", json.dumps([{"name": "p1", "year": 2024, "tags": ["a"]}]))
    write(ws / "assets" / "tokens.css", ":root { --bg: #000; --glass: rgba(0,0,0,.4); }\n.card { color: var(--bg); }\n")
    write(ws / "src" / "ui" / "ui.css", ".glass { backdrop-filter: blur(8px); }\n")
    write(ws / "src" / "ui" / "a.njk", "<div class=\"glass\">A</div>\n")
    write(ws / "src" / "core" / "logic.py", "def route(x: str) -> str:\n    return x\n")
    write(ws / "src" / "core" / "extra.py", "VALUE = 1\n")
    write(ws / "media" / "clip.txt", "m")
    original = {p: (ws / p).read_bytes() for p in
                ["src/ui/ui.css", "src/ui/a.njk", "src/core/logic.py", "src/core/extra.py"]}

    # ---- OLA 0
    code, d = coord(ws, "register-squad", "--model", ORCH, "--mission-id", "m-test")
    check("OLA 0 register-squad -> 0", code == 0, d)
    state = ws / ".swarm_state"
    check("Estructura .swarm_state completa",
          all((state / n).exists() for n in ["mutex.lock", "mission.json", "locks.json", "contracts.json", "ports.json",
                                             "reports.json", "remediations.json", "briefs", "shadows", "events.jsonl"]))
    check("mission.json con orquestador", json.loads((state / "mission.json").read_text())["orchestrator_model"] == ORCH)
    check("register-squad repetido sin --reset -> 1", coord(ws, "register-squad", "--model", ORCH)[0] == 1)

    code, d = coord(ws, "publish-contract", "--file", "assets/tokens.css", "--name", "tokens", "--mode", "strict", "--model", ORCH)
    check("publish-contract strict -> 0", code == 0 and d["contract"]["mode"] == "strict", d)
    code, d = coord(ws, "publish-contract", "--file", "_data/projects.json", "--name", "projects",
                    "--owner", "data-architect-001", "--mode", "structural", "--model", ORCH)
    check("publish-contract structural -> 0", code == 0 and d["contract"]["shape_sha256"] != d["contract"]["content_sha256"], d)
    check("publish-contract archivo inexistente -> 1", coord(ws, "publish-contract", "--file", "nada.json")[0] == 1)
    check("verify-contract --all -> 0", coord(ws, "verify-contract", "--all")[0] == 0)

    for aid, model, paths in [("data-architect-001", SUB, ["_data"]), ("ui-glass-001", SUB2, ["src/ui"]),
                              ("core-logic-001", SUB, ["src/core"])]:
        code, d = coord(ws, "acquire-lock", "--agent-id", aid, "--model", model, "--paths", *paths)
        check(f"OLA 0 pre-asigna lock {aid} -> GRANTED", code == 0 and d["status"] == "GRANTED", d)
    check("Shadow snapshot automatico creado",
          (state / "shadows" / "ui-glass-001" / "manifest.json").is_file()
          and (state / "shadows" / "ui-glass-001" / "files" / "src" / "ui" / "ui.css").is_file())
    manifest = json.loads((state / "shadows" / "core-logic-001" / "manifest.json").read_text())
    check("Manifiesto con hashes SHA-256 originales", len(manifest["files"]["src/core/logic.py"]["sha256"]) == 64)

    code, brief_out = coord(ws, "distill-context", "--agent-id", "ui-glass-001", "--territory", "src/ui",
                            "--contracts", "assets/tokens.css", "_data/projects.json",
                            "--mission-goal", "Pulir glassmorphism")
    check("distill-context -> 0 y JSON compacto", code == 0 and brief_out.get("schema") == "kadi-micro-brief/3.0", brief_out)
    check("Brief guardado en briefs/", (state / "briefs" / "ui-glass-001_brief.json").is_file())
    check("Brief contiene skeleton CSS :root y esquema JSON",
          any(c.get("skeleton", {}).get("tokens", {}).get("--bg") == "#000" for c in brief_out["contracts_readonly"])
          and any("schema" in c.get("skeleton", {}) for c in brief_out["contracts_readonly"]))
    check("Brief < 1200 tokens (estimado)", brief_out["token_estimate"] < 1200, brief_out["token_estimate"])
    check("Brief incluye reglas y comandos", brief_out["boundary_rules"] and brief_out["commands"]["on_start"])

    # ---- Colisiones jerarquicas
    section("Locks jerarquicos NTFS")
    code, d = coord(ws, "acquire-lock", "--agent-id", "intruder", "--model", SUB, "--paths", "src/ui")
    check("Conflicto EXACTO -> 2", code == 2 and d["conflict_type"] == "exact" and d["blocking_agent"] == "ui-glass-001", d)
    check("Conflicto expone modelo bloqueante y TTL restante",
          d.get("blocking_model") == SUB2 and d.get("remaining_ttl_seconds", 0) > 0 and "conflicting_path" in d, d)
    code, d = coord(ws, "acquire-lock", "--agent-id", "intruder", "--model", SUB, "--paths", "SRC/UI")
    check("Conflicto case-insensitive (NTFS) -> 2", code == 2 and d["conflict_type"] == "exact", d)
    code, d = coord(ws, "acquire-lock", "--agent-id", "intruder", "--model", SUB, "--paths", "src/ui/a.njk")
    check("Conflicto DESCENDENTE (hijo en padre bloqueado) -> 2", code == 2 and d["conflict_type"] == "descendant", d)
    code, d = coord(ws, "acquire-lock", "--agent-id", "intruder", "--model", SUB, "--paths", "src")
    check("Conflicto ASCENDENTE (padre sobre hijo bloqueado) -> 2", code == 2 and d["conflict_type"] == "ascendant", d)
    code, d = coord(ws, "acquire-lock", "--agent-id", "intruder", "--model", SUB, "--paths", "src/ui-other")
    check("Prefijo de nombre similar NO colisiona", code == 0, d)
    coord(ws, "release-lock", "--agent-id", "intruder")
    code, d = coord(ws, "acquire-lock", "--agent-id", "intruder", "--model", SUB, "--paths", "../fuera")
    check("Ruta fuera del workspace -> 1", code == 1, d)

    section("Idempotencia y heartbeat")
    code, d = coord(ws, "acquire-lock", "--agent-id", "ui-glass-001", "--model", SUB2, "--paths", "src/ui")
    check("Re-acquire del mismo dueno -> RENEWED (no conflicto)", code == 0 and d["status"] == "RENEWED" and d["heartbeat_count"] == 1, d)
    check("Renovacion no recaptura la sombra", d["shadow"]["newly_captured_files"] == 0, d)
    code, d = coord(ws, "heartbeat-lock", "--agent-id", "ui-glass-001")
    check("heartbeat-lock -> RENEWED", code == 0 and d["status"] == "RENEWED" and d["heartbeat_count"] == 2, d)
    check("heartbeat sin lock -> 1", coord(ws, "heartbeat-lock", "--agent-id", "nadie")[0] == 1)
    code, d = coord(ws, "acquire-lock", "--agent-id", "ui-glass-001", "--model", SUB2, "--paths", "src/ui", "src/ui-extra")
    check("Extension de territorio -> EXTENDED", code == 0 and d["status"] == "EXTENDED", d)
    coord(ws, "release-lock", "--agent-id", "ui-glass-001")
    coord(ws, "acquire-lock", "--agent-id", "ui-glass-001", "--model", SUB2, "--paths", "src/ui")  # re-toma (sin ui-extra)

    section("Purga de leases vencidos")
    coord(ws, "acquire-lock", "--agent-id", "ephemeral", "--model", SUB, "--paths", "media", "--ttl", "1")
    time.sleep(1.4)
    code, d = coord(ws, "acquire-lock", "--agent-id", "media-001", "--model", SUB, "--paths", "media")
    check("Lease vencido purgado silenciosamente en acquire-lock",
          code == 0 and d["status"] == "GRANTED" and any(p["agent_id"] == "ephemeral" for p in d["pruned_stale_locks"]), d)
    coord(ws, "acquire-lock", "--agent-id", "ephemeral2", "--model", SUB, "--paths", "src/ui-other", "--ttl", "1")
    time.sleep(1.4)
    code, d = coord(ws, "prune-stale-locks")
    check("prune-stale-locks purga vencidos", code == 0 and len(d["pruned"]) >= 1, d)
    coord(ws, "release-lock", "--agent-id", "media-001")

    # ---- OLA 1
    section("OLA 1: ediciones, fronteras y rollback atomico")
    # data-architect agrega un proyecto (shape intacto)
    write(ws / "_data" / "projects.json", json.dumps([{"name": "p1", "year": 2024, "tags": ["a"]},
                                                      {"name": "p2", "year": 2025, "tags": ["b", "c"]}]))
    code, d = coord(ws, "submit-report", "--agent-id", "data-architect-001", "--wave", "1", "--summary", "p2 agregado",
                    "--artifacts", "_data/projects.json")
    check("submit-report con contrato structural vivo -> 0", code == 0 and d["status"] == "ACCEPTED", d)
    check("submit-report incluye Leyes de Cierre",
          "ley_1_silencio_operativo_absoluto" in d["closing_laws"] and "ley_2_entrega_obligatoria_manual_po" in d["closing_laws"])
    check("verify-contract --all sigue INTACT tras cambio structural", coord(ws, "verify-contract", "--all")[0] == 0)

    # ui edita: modifica, borra y crea
    write(ws / "src" / "ui" / "ui.css", ".glass { backdrop-filter: blur(20px); }\n.nuevo{}\n")
    (ws / "src" / "ui" / "a.njk").unlink()
    write(ws / "src" / "ui" / "nuevo" / "b.njk", "<p>nuevo</p>")
    # core edita en paralelo (NO debe verse afectado por el rollback de ui)
    write(ws / "src" / "core" / "logic.py", "def route(x: str) -> str:\n    return x.upper()\n")
    core_edit = (ws / "src" / "core" / "logic.py").read_bytes()

    code, d = coord(ws, "submit-report", "--agent-id", "ui-glass-001", "--wave", "1", "--summary", "ok",
                    "--artifacts", "src/ui/ui.css", "src/ui/nuevo/b.njk")
    check("submit-report dentro de frontera -> 0", code == 0, d)
    code, d = coord(ws, "submit-report", "--agent-id", "ui-glass-001", "--wave", "1", "--summary", "invade",
                    "--artifacts", "src/core/logic.py")
    check("Violacion de frontera -> Exit 5", code == 5 and d["status"] == "BOUNDARY_VIOLATION", d)
    code, d = coord(ws, "submit-report", "--agent-id", "sin-lock", "--artifacts", "src/ui/ui.css")
    check("Reporte sin lock activo con artifacts -> 5", code == 5, d)

    # violacion de contrato strict
    tokens = ws / "assets" / "tokens.css"
    tok_orig = tokens.read_bytes()
    write(tokens, ":root { --bg: #111; --glass: rgba(0,0,0,.4); }\n.card { color: var(--bg); }\n")
    code, d = coord(ws, "verify-contract", "--name", "tokens")
    check("Contrato strict: valor cambiado -> Exit 3 (content)", code == 3 and d["violations"][0]["content_changed"], d)
    code, d = coord(ws, "submit-report", "--agent-id", "ui-glass-001", "--artifacts", "src/ui/ui.css")
    check("submit-report con contrato roto -> Exit 3", code == 3, d)
    write(tokens, ":root { --bg: #000; --glass: rgba(0,0,0,.4); --x: 1; }\n.card { color: var(--bg); }\n")
    code, d = coord(ws, "verify-contract", "--all")
    check("Contrato strict: token nuevo -> Exit 3 (shape)", code == 3 and d["violations"][0]["shape_changed"], d)
    tokens.write_bytes(tok_orig)
    check("Contrato restaurado -> INTACT", coord(ws, "verify-contract", "--all")[0] == 0)
    projects = ws / "_data" / "projects.json"
    good = projects.read_bytes()
    write(projects, json.dumps([{"name": "p1", "year": "2024", "tags": ["a"]}]))
    code, d = coord(ws, "verify-contract", "--name", "projects")
    check("Contrato structural: cambio de esquema -> Exit 3", code == 3 and d["violations"][0]["shape_changed"], d)
    projects.write_bytes(good)
    check("verify-contract contrato inexistente -> 3", coord(ws, "verify-contract", "--name", "nope")[0] == 3)

    # rollback quirurgico de ui
    code, d = coord(ws, "rollback-agent", "--agent-id", "ui-glass-001", "--model", ORCH)
    check("rollback-agent ui -> 0", code == 0 and d["status"] == "ROLLED_BACK", d)
    check("Archivo modificado restaurado", (ws / "src/ui/ui.css").read_bytes() == original["src/ui/ui.css"])
    check("Archivo borrado restaurado", (ws / "src/ui/a.njk").read_bytes() == original["src/ui/a.njk"])
    check("Archivos/directorios nuevos eliminados",
          not (ws / "src/ui/nuevo/b.njk").exists() and not (ws / "src/ui/nuevo").exists(), d)
    check("Rollback libera locks del agente", "ui-glass-001" not in json.loads((state / "locks.json").read_text()))
    check("Trabajo paralelo de core 100% intacto", (ws / "src/core/logic.py").read_bytes() == core_edit)
    check("Rollback sin snapshot -> 1", coord(ws, "rollback-agent", "--agent-id", "fantasma", "--model", ORCH)[0] == 1)

    for aid in ("data-architect-001",):
        coord(ws, "release-lock", "--agent-id", aid)

    # ---- OLA 2: puertos, preview, guardian PID
    section("OLA 2: multiplexor de puertos, readiness HTTP y guardian PID")
    squat = socket.socket()
    squat.bind(("127.0.0.1", 0))
    squat.listen(1)
    busy = squat.getsockname()[1]
    code, d = coord(ws, "acquire-port", "--agent-id", "qa-redteam-001", "--preferred", str(busy))
    port = d.get("port")
    check("Puerto preferido ocupado por socket real se omite", code == 0 and port != busy, d)
    check("Puerto asignado pertenece al pool KADI/fallback", port in pm.KADI_POOL or 5200 <= port <= 5299, d)
    squat.close()
    code, d2 = coord(ws, "acquire-port", "--agent-id", "qa-redteam-001")
    check("acquire-port idempotente -> EXISTING", code == 0 and d2["status"] == "EXISTING" and d2["port"] == port, d2)
    code, d3 = coord(ws, "acquire-port", "--agent-id", "otro-agente")
    check("Segundo agente recibe puerto distinto", code == 0 and d3["port"] != port, d3)
    coord(ws, "release-port", "--agent-id", "otro-agente")

    code, d = coord(ws, "check-preview", "--agent-id", "qa-redteam-001", "--timeout", "1")
    check("check-preview sin servidor -> 1 NOT_READY", code == 1 and d["status"] == "NOT_READY" and d["http_status"] is None, d)
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                               "--directory", str(ws)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        coord(ws, "acquire-port", "--agent-id", "qa-redteam-001", "--pid", str(server.pid))
        ports = json.loads((state / "ports.json").read_text())
        check("ports.json registra PID del servidor", any(p["pid"] == server.pid for p in ports), ports)
        code, d = coord(ws, "check-preview", "--agent-id", "qa-redteam-001", "--timeout", "15")
        check("check-preview -> HTTP 200 con latencia", code == 0 and d["status"] == "HTTP_200" and d["http_status"] == 200 and d["latency_ms"] >= 0, d)
        code, d = coord(ws, "check-preview", "--port", str(port), "--path", "/no-existe-404", "--timeout", "1")
        check("check-preview 404 -> NOT_READY", code == 1 and d["status"] == "NOT_READY" and d["http_status"] == 404, d)
        code, d = coord(ws, "release-port", "--agent-id", "qa-redteam-001")
        time.sleep(0.3)
        check("release-port libera el puerto", code == 0 and port in d["released_ports"], d)
        check("Guardian PID: taskkill /F /T mato el servidor", server.poll() is not None and d["killed"][0]["killed"], d)
        check("Puerto TCP liberado realmente", pm.port_is_free(port))
    finally:
        if server.poll() is None:
            server.kill()
    check("release-port sin puerto -> NO_PORT", coord(ws, "release-port", "--agent-id", "qa-redteam-001")[1]["status"] == "NO_PORT")

    section("Agotamiento de puertos (Exit 4)")
    atomic_ports = [{"port": p, "agent_id": f"sq{p}", "pid": None, "preferred": None, "acquired_at": 0, "health_url": ""}
                    for p, _ in pm.candidate_ports(None)]
    (state / "ports.json").write_text(json.dumps(atomic_ports), encoding="utf-8")
    code, d = coord(ws, "acquire-port", "--agent-id", "ultimo")
    check("Pool agotado -> Exit 4", code == 4 and d["status"] == "PORTS_EXHAUSTED", d)
    (state / "ports.json").write_text("[]", encoding="utf-8")
    real = pm.port_is_free
    pm.port_is_free = lambda p: False  # type: ignore[assignment]
    check("choose_port sin puertos libres -> None", pm.choose_port(9999, []) is None)
    pm.port_is_free = real  # type: ignore[assignment]

    # ---- OLA 2.5
    section("OLA 2.5: remediacion quirurgica y circuit breaker")
    coord(ws, "release-lock", "--agent-id", "core-logic-001")
    ticket_file = "remediation_ticket.json"
    code, d = coord(ws, "emit-remediation", "--agent-id", "core-logic-001", "--file", "src/core/logic.py",
                    "--line", "2", "--assertion", "route('a') == 'a'", "--error", "AssertionError", "--out", ticket_file)
    check("Remediacion intento 1 -> 0", code == 0 and d["ticket"]["attempt"] == 1 and d["attempts_remaining"] == 1, d)
    check("Ticket con archivo, linea y aserciones",
          d["ticket"]["file"] == "src/core/logic.py" and d["ticket"]["line"] == 2 and (ws / ticket_file).is_file(), d)
    code, d = coord(ws, "emit-remediation", "--agent-id", "core-logic-001", "--file", "src/core/logic.py",
                    "--error", "AssertionError", "--reopen", "--model", ORCH)
    check("Remediacion intento 2 -> 0 y reabre lock 300 s",
          code == 0 and d["ticket"]["attempt"] == 2 and d["reopen"]["exit_code"] == 0, d)
    locks = json.loads((state / "locks.json").read_text())
    lk = locks.get("core-logic-001", {})
    check("Lock reabierto solo sobre el archivo afectado, TTL <= 300",
          len(lk.get("normalized_paths", [])) == 1 and lk["normalized_paths"][0].endswith("logic.py")
          and lk["expires_at"] - time.time() <= 300, lk)
    check("Reapertura no sobrescribe la copia sombra limpia", d["reopen"]["shadow"]["newly_captured_files"] == 0, d)
    code, d = coord(ws, "emit-remediation", "--agent-id", "core-logic-001", "--file", "src/core/logic.py", "--error", "otra vez")
    check("Intento 3 -> Exit 7 (Circuit Breaker)", code == 7 and d["status"] == "CIRCUIT_BREAKER_OPEN", d)
    check("Circuit breaker sugiere rollback-agent", "rollback-agent" in d["rollback_command"])
    code, d = coord(ws, "emit-remediation", "--agent-id", "otro-agente", "--file", "src/core/extra.py", "--error", "e")
    check("Contador de intentos es por agente", code == 0 and d["ticket"]["attempt"] == 1, d)
    code, d = coord(ws, "rollback-agent", "--agent-id", "core-logic-001", "--model", ORCH)
    check("Rollback tras breaker restaura logic.py", code == 0 and (ws / "src/core/logic.py").read_bytes() == original["src/core/logic.py"], d)
    check("remediations.json registra incidente",
          len(json.loads((state / "remediations.json").read_text())["incidents"]) == 1)

    # ---- OLA 3
    section("OLA 3: cierre y status-report")
    coord(ws, "acquire-lock", "--agent-id", "pendiente", "--model", SUB, "--paths", "media")
    code, d = coord(ws, "status-report")
    check("status-report con locks activos -> IN_PROGRESS", code == 0 and d["status"] == "IN_PROGRESS" and d["active_locks"] == 1, d)
    coord(ws, "release-lock", "--agent-id", "pendiente")
    code, d = coord(ws, "status-report", "--model", ORCH, "--wave-status", "WAVE_3_CLOSING")
    check("status-report limpio -> READY_FOR_HANDOFF",
          d["status"] == "READY_FOR_HANDOFF" and d["active_locks"] == 0 and d["active_ports"] == 0 and d["contracts_all_intact"], d)
    check("status-report incluye Leyes de Cierre y recordatorio de Handoff",
          "MANUAL ESTRATÉGICO DE SIGUIENTES PASOS PARA EL PO" in d["handoff_reminder"]
          and "Silencio" in d["closing_laws"]["ley_1_silencio_operativo_absoluto"] or "silencio" in d["closing_laws"]["ley_1_silencio_operativo_absoluto"], d)
    check("wave_status persistido", d["mission"]["wave_status"] == "WAVE_3_CLOSING")
    fr = d["flight_recorder"]
    check("Flight Recorder con metricas", fr["total_events"] > 30 and fr["non_zero_exits"] > 0 and fr["avg_duration_ms"] > 0, fr)
    events = [json.loads(line) for line in (state / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    check("events.jsonl: ISO-8601 microsegundos + campos obligatorios",
          all({"ts", "command", "agent_id", "model", "duration_ms", "exit_code"} <= set(e) and len(e["ts"].split(".")[1].split("+")[0].split("-")[0]) == 6
              for e in events), events[:2])
    check("Sin archivos temporales huerfanos en .swarm_state", not list(state.glob("*.tmp")))


def test_concurrency(tmp: Path) -> None:
    section("Concurrencia: mutex NTFS + escritura atomica")
    ws = tmp / "conc"
    for i in range(8):
        write(ws / "par" / f"f{i}.txt", str(i))
    coord(ws, "register-squad", "--model", ORCH)
    procs = [subprocess.Popen([sys.executable, str(COORD), "acquire-lock", "--agent-id", f"agent-{i}", "--model", SUB,
                               "--paths", f"par/f{i}.txt", "--workspace", str(ws)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(8)]
    codes = [p.wait(timeout=60) for p in procs]
    locks = json.loads((ws / ".swarm_state" / "locks.json").read_text())
    check("8 acquire-lock paralelos -> todos 0", codes == [0] * 8, codes)
    check("locks.json integro con 8 leases (sin perdidas)", len(locks) == 8, len(locks))
    # contienda real por el mismo recurso: exactamente uno gana
    procs = [subprocess.Popen([sys.executable, str(COORD), "acquire-lock", "--agent-id", f"rival-{i}", "--model", SUB2,
                               "--paths", "par", "--workspace", str(ws)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True) for i in range(1)]
    check("Padre sobre 8 hijos bloqueados -> 2", [p.wait(timeout=60) for p in procs] == [2])


def main() -> int:
    started = time.perf_counter()
    print(f"KADI Swarm v3.0.0 Apex - self test ({sys.version.split()[0]})")
    with tempfile.TemporaryDirectory(prefix="kadi_swarm_test_") as raw:
        tmp = Path(raw)
        for fn in (test_dual_hashes, test_vault_unit, test_model_policy, test_mission, test_concurrency):
            try:
                fn(tmp)
            except Exception as exc:  # noqa: BLE001 - una excepcion inesperada cuenta como fallo
                import traceback
                traceback.print_exc()
                check(f"{fn.__name__} sin excepciones", False, repr(exc))
    total = RESULTS["pass"] + RESULTS["fail"]
    print(f"\n{'=' * 60}\nRESULTADO: {RESULTS['pass']}/{total} aserciones OK, {RESULTS['fail']} fallos "
          f"({time.perf_counter() - started:.1f}s)")
    print("SELF TEST OK - Exit Code 0" if not RESULTS["fail"] else "SELF TEST FALLIDO - Exit Code 1")
    return 0 if not RESULTS["fail"] else 1


if __name__ == "__main__":
    sys.exit(main())
