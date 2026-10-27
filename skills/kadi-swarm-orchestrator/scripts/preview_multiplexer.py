#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""KADI Swarm v3.0.0 Apex - Multiplexor reactivo de previsualizacion (/teamwork-preview).

  * Pool de prioridades TCP en 127.0.0.1: preferido -> pool KADI -> rango 5200-5299.
  * Sondeo real doble: ``connect_ex != 0`` Y ``bind`` efimero exitoso.
  * Readiness HTTP 200 con latencia en ms (sin proxies).
  * Guardian PID: terminacion limpia del arbol de procesos (``taskkill /F /T /PID``).

100% libreria estandar de Python 3.13.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Iterable

LOOPBACK = "127.0.0.1"
KADI_POOL = [8000, 5173, 5174, 5175, 3000, 3001, 8080, 9222]
FALLBACK_RANGE = range(5200, 5300)  # 5200..5299


def port_is_free(port: int) -> bool:
    """Sondeo real doble: nadie escucha (connect_ex) y el SO permite el bind."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.settimeout(0.25)
        if probe.connect_ex((LOOPBACK, port)) == 0:
            return False  # hay un servicio aceptando conexiones
    finally:
        probe.close()
    binder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        binder.bind((LOOPBACK, port))  # sin SO_REUSEADDR: en Windows permitiria falsos positivos
        return True
    except OSError:
        return False
    finally:
        binder.close()


def candidate_ports(preferred: int | None = None) -> list[tuple[int, str]]:
    """Orden de prioridad sin duplicados: (puerto, origen)."""
    seen: set[int] = set()
    ordered: list[tuple[int, str]] = []
    if preferred is not None:
        ordered.append((preferred, "preferred"))
        seen.add(preferred)
    for p in KADI_POOL:
        if p not in seen:
            ordered.append((p, "kadi_pool"))
            seen.add(p)
    for p in FALLBACK_RANGE:
        if p not in seen:
            ordered.append((p, "fallback_range"))
            seen.add(p)
    return ordered


def choose_port(preferred: int | None, active_ports: Iterable[int]) -> tuple[int, str] | None:
    """Primer puerto libre segun prioridades; ``None`` si el pool se agoto."""
    active = set(active_ports)
    for port, origin in candidate_ports(preferred):
        if not (0 < port < 65536) or port in active:
            continue
        if port_is_free(port):
            return port, origin
    return None


def check_http(url: str, timeout: float = 10.0, interval: float = 0.25) -> dict[str, Any]:
    """Sondea ``url`` hasta obtener HTTP 200 o agotar ``timeout`` (readiness probe)."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + max(timeout, 0.0)
    attempts = 0
    last_status: int | None = None
    last_error: str | None = None
    while True:
        attempts += 1
        started = time.perf_counter()
        try:
            remaining = max(deadline - time.monotonic(), 0.5)
            with opener.open(url, timeout=min(remaining, 3.0)) as resp:
                last_status = resp.status
                latency = round((time.perf_counter() - started) * 1000, 2)
                if resp.status == 200:
                    return {"ok": True, "http_status": 200, "latency_ms": latency, "attempts": attempts, "url": url}
        except urllib.error.HTTPError as exc:
            last_status, last_error = exc.code, f"HTTP {exc.code}"
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_error = str(getattr(exc, "reason", exc))
        if time.monotonic() >= deadline:
            return {"ok": False, "http_status": last_status, "error": last_error, "attempts": attempts, "url": url}
        time.sleep(interval)


def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, check=False,
        ).stdout
        return f'"{pid}"' in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_process_tree(pid: int) -> dict[str, Any]:
    """Termina el arbol de procesos de ``pid`` (Windows: ``taskkill /F /T /PID``)."""
    protected = {0, 4, os.getpid(), os.getppid()}
    if pid in protected or pid < 0:
        return {"pid": pid, "killed": False, "reason": "pid protegido"}
    if not pid_alive(pid):
        return {"pid": pid, "killed": False, "reason": "proceso ya inexistente"}
    if os.name == "nt":
        proc = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                              capture_output=True, text=True, check=False)
        for _ in range(20):  # espera cierre efectivo (max ~2 s)
            if not pid_alive(pid):
                break
            time.sleep(0.1)
        return {"pid": pid, "killed": not pid_alive(pid), "returncode": proc.returncode}
    try:
        os.kill(pid, 9)
        return {"pid": pid, "killed": True}
    except OSError as exc:
        return {"pid": pid, "killed": False, "reason": str(exc)}
