#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""KADI Swarm v3.0.0 Apex - Destilador semantico AST (motor estilo /boost).

Responsabilidades:
  * ``compute_dual_hashes``: Content-SHA256 (bytes normalizados CRLF->LF) y
    Shape-SHA256 (esqueleto estructural independiente de los datos literales).
  * ``extract_skeleton``: esqueleto ultracompacto de .py/.js/.ts/.mjs/.css/.json.
  * ``build_micro_brief``: paquete de micro-contexto Zero-Exploration para un
    subagente (territorio + contratos + reglas de frontera + comandos).

100% libreria estandar de Python 3.13. Sin dependencias externas.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SHAPE_VERSION = "kadi-shape/1"
BRIEF_SCHEMA = "kadi-micro-brief/3.0"

JS_EXTENSIONS = {".js", ".ts", ".mjs"}
SKELETON_EXTENSIONS = {".py", ".js", ".ts", ".mjs", ".css", ".json"}
IGNORED_DIRS = {".swarm_state", ".git", "node_modules", "__pycache__", ".venv", "dist"}

MAX_TERRITORY_FILES = 200
MAX_CONTRACT_DIR_FILES = 25
MAX_LIST_ITEMS = 150


# --------------------------------------------------------------------------- #
# Hashing primitives
# --------------------------------------------------------------------------- #
def normalize_bytes(data: bytes) -> bytes:
    """Normaliza saltos de linea CRLF -> LF para evitar falsos positivos en Windows."""
    return data.replace(b"\r\n", b"\n")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def file_content_sha256(path: Path) -> str:
    return sha256_hex(normalize_bytes(path.read_bytes()))


# --------------------------------------------------------------------------- #
# JSON: arbol de esquemas
# --------------------------------------------------------------------------- #
def json_schema(value: Any) -> Any:
    """Reemplaza valores primitivos por el nombre de su tipo.

    Diccionarios -> claves ordenadas; listas -> conjunto ordenado de esquemas unicos.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):  # bool antes que int (bool es subclase de int)
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, dict):
        return {key: json_schema(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        unique = {_canonical(json_schema(item)): json_schema(item) for item in value}
        return {"__list__": [unique[k] for k in sorted(unique)]}
    return type(value).__name__


# --------------------------------------------------------------------------- #
# Python: firma estructural publica via ast
# --------------------------------------------------------------------------- #
def _arg_names(args: ast.arguments) -> list[str]:
    names = [a.arg for a in args.posonlyargs] + [a.arg for a in args.args]
    if args.vararg:
        names.append("*" + args.vararg.arg)
    names.extend(a.arg for a in args.kwonlyargs)
    if args.kwarg:
        names.append("**" + args.kwarg.arg)
    return names


def _func_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    returns = ast.unparse(node.returns) if node.returns is not None else None
    return {
        "name": node.name,
        "async": isinstance(node, ast.AsyncFunctionDef),
        "args": _arg_names(node.args),
        "returns": returns,
    }


def python_skeleton(source: str) -> dict[str, Any]:
    """Clases, funciones y metodos publicos (sin prefijo ``_``)."""
    tree = ast.parse(source)
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                functions.append(_func_sig(node))
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            methods = [
                _func_sig(m)
                for m in node.body
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not m.name.startswith("_")
            ]
            methods.sort(key=lambda m: m["name"])
            classes.append({"name": node.name, "methods": methods})
    classes.sort(key=lambda c: c["name"])
    functions.sort(key=lambda f: f["name"])
    return {"classes": classes, "functions": functions}


# --------------------------------------------------------------------------- #
# JS / TS / MJS: firmas exportadas via regex deterministas
# --------------------------------------------------------------------------- #
_JS_STRIP = re.compile(
    r"""("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)|//[^\n]*|/\*.*?\*/""",
    re.DOTALL,
)
_JS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("function", re.compile(
        r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)?\s*\(([^)]*)\)")),
    ("class", re.compile(
        r"\bexport\s+(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"
        r"(?:\s+extends\s+([A-Za-z_$][\w$.]*))?")),
    ("const", re.compile(r"\bexport\s+(?:declare\s+)?(const|let|var)\s+([A-Za-z_$][\w$]*)")),
    ("interface", re.compile(r"\bexport\s+(?:declare\s+)?interface\s+([A-Za-z_$][\w$]*)")),
    ("type", re.compile(r"\bexport\s+(?:declare\s+)?type\s+([A-Za-z_$][\w$]*)")),
    ("enum", re.compile(r"\bexport\s+(?:declare\s+)?(?:const\s+)?enum\s+([A-Za-z_$][\w$]*)")),
    ("named", re.compile(r"\bexport\s*\{([^}]*)\}")),
    ("default", re.compile(r"\bexport\s+default\s+(?!(?:async\s+)?function\b|(?:abstract\s+)?class\b)")),
    ("cjs-assign", re.compile(r"\bmodule\.exports\s*=")),
    ("cjs-member", re.compile(r"\b(?:module\.)?exports\.([A-Za-z_$][\w$]*)\s*=")),
]


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def js_skeleton(source: str) -> dict[str, Any]:
    clean = _JS_STRIP.sub(lambda m: m.group(1) if m.group(1) else " ", source)
    exports: set[str] = set()
    for kind, pattern in _JS_PATTERNS:
        for m in pattern.finditer(clean):
            if kind == "function":
                exports.add(f"function {m.group(1) or 'default'}({_collapse(m.group(2))})")
            elif kind == "class":
                ext = f" extends {m.group(2)}" if m.group(2) else ""
                exports.add(f"class {m.group(1)}{ext}")
            elif kind == "const":
                exports.add(f"{m.group(1)} {m.group(2)}")
            elif kind in ("interface", "type", "enum"):
                exports.add(f"{kind} {m.group(1)}")
            elif kind == "named":
                for item in m.group(1).split(","):
                    item = _collapse(item)
                    if item:
                        exports.add(f"named {item}")
            elif kind == "default":
                exports.add("default expression")
            elif kind == "cjs-assign":
                exports.add("module.exports")
            elif kind == "cjs-member":
                exports.add(f"exports.{m.group(1)}")
    return {"exports": sorted(exports)}


# --------------------------------------------------------------------------- #
# CSS: tokens :root y clases principales
# --------------------------------------------------------------------------- #
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_CSS_ROOT = re.compile(r":root\s*\{([^}]*)\}")
_CSS_VAR = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]*)")
_CSS_PRELUDE = re.compile(r"([^{}]+)\{")
_CSS_CLASS = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")


def css_skeleton(source: str, with_values: bool = True) -> dict[str, Any]:
    clean = _CSS_COMMENT.sub(" ", source)
    tokens: dict[str, str] = {}
    for block in _CSS_ROOT.finditer(clean):
        for name, value in _CSS_VAR.findall(block.group(1)):
            tokens[name] = _collapse(value)
    classes: set[str] = set()
    for prelude in _CSS_PRELUDE.findall(clean):
        if prelude.lstrip().startswith("@"):
            continue
        classes.update(_CSS_CLASS.findall(prelude))
    return {
        "tokens": tokens if with_values else sorted(tokens),
        "classes": sorted(classes),
    }


# --------------------------------------------------------------------------- #
# Esqueleto unificado + dual hash
# --------------------------------------------------------------------------- #
def _read_text(path: Path) -> str:
    return normalize_bytes(path.read_bytes()).decode("utf-8", errors="replace")


def _shape_basis(path: Path) -> tuple[str, Any] | None:
    """Devuelve ``(kind, estructura_hasheable)`` o None si no hay forma estructural."""
    ext = path.suffix.lower()
    try:
        if ext == ".json":
            return "json", json_schema(json.loads(_read_text(path).lstrip("\ufeff")))
        if ext == ".py":
            return "python", python_skeleton(_read_text(path))
        if ext in JS_EXTENSIONS:
            return "javascript", js_skeleton(_read_text(path))
        if ext == ".css":
            return "css", css_skeleton(_read_text(path), with_values=False)
    except (ValueError, SyntaxError, RecursionError):
        return None  # sintaxis invalida -> shape == content (cualquier cambio rompe)
    return None


def compute_dual_hashes(file_path: Path) -> dict:
    """Calcula ``content_sha256`` y ``shape_sha256`` de un archivo.

    Lanza ``FileNotFoundError`` si el archivo no existe.
    """
    file_path = Path(file_path)
    content = file_content_sha256(file_path)
    basis = _shape_basis(file_path)
    if basis is None:
        return {"content_sha256": content, "shape_sha256": content, "kind": "opaque"}
    kind, structure = basis
    payload = _canonical({"v": SHAPE_VERSION, "kind": kind, "shape": structure})
    return {
        "content_sha256": content,
        "shape_sha256": sha256_hex(payload.encode("utf-8")),
        "kind": kind,
    }


def extract_skeleton(file_path: Path) -> dict[str, Any]:
    """Esqueleto compacto para inyectar en micro-briefs (no incluye cuerpos ni datos)."""
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    try:
        if ext == ".json":
            return {"kind": "json", "schema": json_schema(json.loads(_read_text(file_path).lstrip("\ufeff")))}
        if ext == ".py":
            return {"kind": "python", **python_skeleton(_read_text(file_path))}
        if ext in JS_EXTENSIONS:
            return {"kind": "javascript", **js_skeleton(_read_text(file_path))}
        if ext == ".css":
            skel = css_skeleton(_read_text(file_path), with_values=True)
            skel["classes"] = skel["classes"][:MAX_LIST_ITEMS]
            return {"kind": "css", **skel}
    except (ValueError, SyntaxError, RecursionError) as exc:
        return {"kind": "unparseable", "error": str(exc)[:120]}
    return {"kind": "opaque", "size": file_path.stat().st_size}


# --------------------------------------------------------------------------- #
# Micro-brief
# --------------------------------------------------------------------------- #
def _walk_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for item in sorted(root.rglob("*")):
        if item.is_file() and not any(part in IGNORED_DIRS for part in item.relative_to(root).parts):
            out.append(item)
    return out


def _rel(workspace: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _file_entry(workspace: Path, path: Path) -> dict[str, Any]:
    return {
        "path": _rel(workspace, path),
        "size": path.stat().st_size,
        "sha256_16": file_content_sha256(path)[:16],
    }


def describe_territory(workspace: Path, items: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in items:
        target = (workspace / raw).resolve()
        if not target.exists():
            result.append({"path": _rel(workspace, target), "kind": "missing", "note": "se creara dentro del territorio"})
        elif target.is_file():
            result.append({"kind": "file", **_file_entry(workspace, target)})
        else:
            files = _walk_files(target)
            result.append({
                "path": _rel(workspace, target),
                "kind": "dir",
                "file_count": len(files),
                "files": [_file_entry(workspace, f) for f in files[:MAX_TERRITORY_FILES]],
                "truncated": len(files) > MAX_TERRITORY_FILES,
            })
    return result


def describe_contracts(workspace: Path, items: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in items:
        target = (workspace / raw).resolve()
        if not target.exists():
            result.append({"path": _rel(workspace, target), "kind": "missing"})
            continue
        files = [target] if target.is_file() else [
            f for f in _walk_files(target) if f.suffix.lower() in SKELETON_EXTENSIONS
        ][:MAX_CONTRACT_DIR_FILES]
        for f in files:
            hashes = compute_dual_hashes(f)
            result.append({
                "path": _rel(workspace, f),
                "mode": "read-only",
                "content_sha256": hashes["content_sha256"],
                "shape_sha256": hashes["shape_sha256"],
                "skeleton": extract_skeleton(f),
            })
    return result


def build_micro_brief(
    workspace: Path,
    agent_id: str,
    territory: list[str],
    contracts: list[str],
    mission_goal: str,
    agent_model: str,
    coordinator_path: Path,
) -> dict[str, Any]:
    """Construye el micro_brief.json (Zero-Exploration) para un subagente."""
    workspace = Path(workspace).resolve()
    coord = f'uv run "{coordinator_path}"'
    ws = f'--workspace "{workspace}"'
    paths = " ".join(f'"{t}"' for t in territory)
    brief: dict[str, Any] = {
        "schema": BRIEF_SCHEMA,
        "agent_id": agent_id,
        "agent_model": agent_model,
        "mission_goal": mission_goal,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspace": str(workspace),
        "territory_writable": describe_territory(workspace, territory),
        "contracts_readonly": describe_contracts(workspace, contracts),
        "boundary_rules": [
            "ZERO-EXPLORATION: no leas ni listes archivos fuera de territory_writable y contracts_readonly.",
            "Solo puedes editar archivos dentro de tu territorio bloqueado.",
            "Los contratos son de solo lectura: su Shape-SHA256 no puede cambiar (modo strict: tampoco el Content-SHA256).",
            "Exit Code 2 o 6 en acquire-lock: aborta de inmediato. Exit Code 5 en submit-report: revierte lo tocado fuera de tu zona.",
            "SILENCIO OPERATIVO: prohibido chrono.exe speak, TTS o cualquier notificacion sonora.",
        ],
        "commands": {
            "on_start": [f'{coord} acquire-lock --agent-id {agent_id} --model {agent_model} --paths {paths} {ws}'],
            "on_finish": [
                f'{coord} submit-report --agent-id {agent_id} --wave 1 --status DONE --summary "<resumen>" '
                f'--artifacts {paths} {ws}',
                f'{coord} release-lock --agent-id {agent_id} {ws}',
            ],
        },
    }
    brief["token_estimate"] = len(_canonical(brief)) // 4
    return brief


def main(argv: list[str]) -> int:  # pragma: no cover - utilidad de diagnostico
    if len(argv) < 2:
        print("uso: ast_distiller.py <archivo>", file=sys.stderr)
        return 1
    target = Path(argv[1])
    if not target.is_file():
        print(f"archivo inexistente: {target}", file=sys.stderr)
        return 1
    print(json.dumps({"hashes": compute_dual_hashes(target), "skeleton": extract_skeleton(target)},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
