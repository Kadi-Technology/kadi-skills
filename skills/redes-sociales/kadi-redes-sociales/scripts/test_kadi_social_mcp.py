"""Prueba de humo del servidor MCP: initialize + tools/list (+ tools/call de build_utm_link y lint_copy) por stdin.

Uso:  python scripts/test_kadi_social_mcp.py [--minimal] [--show]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SERVER = Path(__file__).resolve().parent / "kadi_social_mcp.py"


def run(minimal: bool) -> list[dict]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if minimal:
        env["KADI_SOCIAL_MCP_FORCE_MINIMAL"] = "1"
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "prueba", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "build_utm_link", "arguments": {"url": "https://kadi.technology/contacto/", "channel": "youtube_short", "campaign": "founders_cohort01"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "build_utm_link", "arguments": {"url": "https://prod-cliente.kadi.technology/", "channel": "instagram", "campaign": "founders_cohort01"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "lint_copy", "arguments": {"text": "Somos el mejor software. Visita https://kadi.technology/ hoy."}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "list_assets", "arguments": {"project": "anatomia-3d", "aspect_ratio": "9:16"}}},
    ]
    proc = subprocess.Popen(
        [sys.executable, "-I", str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    responses: list[dict] = []
    wanted = {m["id"] for m in messages if "id" in m}
    try:
        assert proc.stdin and proc.stdout
        for m in messages:
            proc.stdin.write(json.dumps(m) + "\n")
        proc.stdin.flush()
        deadline = time.time() + 120
        while wanted and time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            if line.strip():
                reply = json.loads(line)
                responses.append(reply)
                wanted.discard(reply.get("id"))
        if wanted:
            raise SystemExit(f"Faltaron respuestas para los ids {sorted(wanted)}")
    finally:
        if proc.stdin:
            proc.stdin.close()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
    return responses


def check(responses: list[dict], label: str) -> None:
    by_id = {r["id"]: r for r in responses if "id" in r}
    init = by_id[1]["result"]
    assert init["serverInfo"]["name"] == "kadi-social", init
    tools = {t["name"] for t in by_id[2]["result"]["tools"]}
    expected = {"list_assets", "get_calendar", "build_utm_link", "lint_copy", "export_draft_queue"}
    assert tools == expected, tools
    ok_link = by_id[3]["result"]
    assert not ok_link.get("isError"), ok_link
    url = json.loads(ok_link["content"][0]["text"])["url"]
    assert url == "https://kadi.technology/contacto/?utm_source=youtube&utm_medium=video_short&utm_campaign=founders_cohort01", url
    assert by_id[4]["result"]["isError"] is True, by_id[4]
    lint = json.loads(by_id[5]["result"]["content"][0]["text"])
    assert lint["ok"] is False and lint["findings"], lint
    assets = json.loads(by_id[6]["result"]["content"][0]["text"])
    assert assets["count"] > 0 and all(a["aspect_ratio"] == "9:16" for a in assets["assets"]), assets["count"]
    print(f"[{label}] OK: initialize, tools/list ({len(tools)} herramientas), build_utm_link, lint_copy ({len(lint['findings'])} hallazgos), list_assets ({assets['count']} activos 9:16)")


if __name__ == "__main__":
    show = "--show" in sys.argv
    modes = [True] if "--minimal" in sys.argv else [False, True]
    for minimal in modes:
        label = "JSON-RPC minimo" if minimal else "FastMCP"
        responses = run(minimal)
        if show:
            for r in responses[:2]:
                print(json.dumps(r, ensure_ascii=False)[:3000])
        check(responses, label)
