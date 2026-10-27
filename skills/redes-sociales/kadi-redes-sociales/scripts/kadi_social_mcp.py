#!/usr/bin/env python3
"""Servidor MCP local (stdio) del Community Manager de KADI.

Herramientas de solo lectura y borrador:
  - list_assets(project, aspect_ratio)       activos publicables del indice semantico
  - get_calendar(lote)                       calendario del lote (dias y piezas)
  - build_utm_link(url, channel, campaign)   enlace con el esquema UTM oficial
  - lint_copy(text)                          invoca scripts/check_social_copy.mjs
  - export_draft_queue(lote)                 escribe draft_queue.json del lote (nada se publica)

No llama APIs externas, no lee tokens ni .env. Usa FastMCP (paquete mcp) si esta instalado;
si no, implementa JSON-RPC 2.0 minimo conforme a MCP (initialize, tools/list, tools/call).
Para forzar la implementacion minima: KADI_SOCIAL_MCP_FORCE_MINIMAL=1.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kadi_social_core as core  # noqa: E402

SERVER_NAME = "kadi-social"
SERVER_VERSION = "1.0.0"


def tool_list_assets(project: str = "", aspect_ratio: str = "") -> dict[str, Any]:
    """Lista activos publicables (publishable=true, pii_check=clean) del indice semantico. Filtros opcionales: project (slug, p. ej. kadi-scv) y aspect_ratio (16:9, 9:16, 4:5, 1:1)."""
    return core.list_assets(project or None, aspect_ratio or None)


def tool_get_calendar(lote: str) -> dict[str, Any]:
    """Devuelve el calendario de un lote (formato LOTE-NN): piezas por dia, canal, pilar y horario CDMX."""
    return core.get_calendar(lote)


def tool_build_utm_link(url: str, channel: str, campaign: str) -> dict[str, Any]:
    """Construye un enlace UTM oficial. channel: instagram, linkedin, facebook, youtube_short, youtube_horizontal o tiktok. campaign en snake_case. Solo hosts kadi.technology y portal-cliente.kadi.technology."""
    return {"url": core.build_utm_link(url, channel, campaign)}


def tool_lint_copy(text: str) -> dict[str, Any]:
    """Revisa un copy con el linter de claims de KADI (reglas R1, R2 y KADI). Devuelve hallazgos con linea, columna y regla."""
    return core.lint_copy(text)


def tool_export_draft_queue(lote: str) -> dict[str, Any]:
    """Genera draft_queue.json del lote a partir de las piezas (meta.json). Todo queda como BORRADOR: no publica nada."""
    return core.export_draft_queue(lote)


def _schema(props: dict[str, dict[str, Any]], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_assets",
        "func": tool_list_assets,
        "description": tool_list_assets.__doc__,
        "read_only": True,
        "inputSchema": _schema(
            {
                "project": {"type": "string", "description": "Slug del proyecto, por ejemplo kadi-scv o anatomia-3d. Vacio para todos."},
                "aspect_ratio": {"type": "string", "description": "16:9, 9:16, 4:5 o 1:1. Vacio para todos."},
            },
            [],
        ),
    },
    {
        "name": "get_calendar",
        "func": tool_get_calendar,
        "description": tool_get_calendar.__doc__,
        "read_only": True,
        "inputSchema": _schema({"lote": {"type": "string", "description": "Identificador del lote, por ejemplo LOTE-01."}}, ["lote"]),
    },
    {
        "name": "build_utm_link",
        "func": tool_build_utm_link,
        "description": tool_build_utm_link.__doc__,
        "read_only": True,
        "inputSchema": _schema(
            {
                "url": {"type": "string", "description": "URL https de kadi.technology o portal-cliente.kadi.technology."},
                "channel": {"type": "string", "enum": sorted(core.UTM_CHANNELS), "description": "Canal de destino."},
                "campaign": {"type": "string", "description": "Slug de campana en snake_case."},
            },
            ["url", "channel", "campaign"],
        ),
    },
    {
        "name": "lint_copy",
        "func": tool_lint_copy,
        "description": tool_lint_copy.__doc__,
        "read_only": True,
        "inputSchema": _schema({"text": {"type": "string", "description": "Texto del copy a revisar."}}, ["text"]),
    },
    {
        "name": "export_draft_queue",
        "func": tool_export_draft_queue,
        "description": tool_export_draft_queue.__doc__,
        "read_only": False,
        "inputSchema": _schema({"lote": {"type": "string", "description": "Identificador del lote, por ejemplo LOTE-01."}}, ["lote"]),
    },
]
TOOL_INDEX = {t["name"]: t for t in TOOLS}


# ---------------------------------------------------------------------------------------------
# Implementacion minima JSON-RPC 2.0 (stdio, un mensaje JSON por linea) conforme a MCP
# ---------------------------------------------------------------------------------------------
SUPPORTED_PROTOCOLS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = TOOL_INDEX.get(name)
    if tool is None:
        raise KeyError(name)
    func: Callable[..., Any] = tool["func"]
    try:
        payload = func(**arguments)
        return {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
            "structuredContent": payload,
            "isError": False,
        }
    except (core.SocialError, TypeError) as exc:
        return {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    if method is None:
        return None  # respuesta de un cliente: se ignora
    if msg_id is None:
        return None  # notificacion (notifications/initialized, etc.)
    params = msg.get("params") or {}
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[1]
        return _result(
            msg_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Herramientas de solo lectura y borrador del Community Manager de KADI. Nada se publica.",
            },
        )
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
                "annotations": {"readOnlyHint": t["read_only"], "openWorldHint": False},
            }
            for t in TOOLS
        ]
        return _result(msg_id, {"tools": tools})
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOL_INDEX:
            return _error(msg_id, -32602, f"Herramienta desconocida: {name}")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _error(msg_id, -32602, "arguments debe ser un objeto")
        return _result(msg_id, _call_tool(name, arguments))
    return _error(msg_id, -32601, f"Metodo no soportado: {method}")


def run_minimal() -> None:
    stdin = sys.stdin
    stdout = sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps(_error(None, -32700, "JSON invalido"), ensure_ascii=False) + "\n")
            stdout.flush()
            continue
        if isinstance(msg, list):
            replies = [r for r in (handle_message(m) for m in msg if isinstance(m, dict)) if r is not None]
            if replies:
                stdout.write(json.dumps(replies, ensure_ascii=False) + "\n")
                stdout.flush()
            continue
        reply = handle_message(msg)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()


def run_fastmcp() -> None:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations

    server = FastMCP(SERVER_NAME, instructions="Herramientas de solo lectura y borrador del Community Manager de KADI. Nada se publica.")
    for t in TOOLS:
        server.add_tool(
            t["func"],
            name=t["name"],
            description=t["description"],
            annotations=ToolAnnotations(readOnlyHint=t["read_only"], openWorldHint=False),
        )
    server.run(transport="stdio")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    if os.environ.get("KADI_SOCIAL_MCP_FORCE_MINIMAL") == "1":
        run_minimal()
        return
    try:
        import mcp.server.fastmcp  # noqa: F401
    except ImportError:
        run_minimal()
        return
    run_fastmcp()


if __name__ == "__main__":
    main()
