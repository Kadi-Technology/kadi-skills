"""Nucleo compartido del Community Manager de KADI (solo lectura salvo export de borradores).

Lo usan el servidor MCP local (kadi_social_mcp.py) y los scripts de construccion del lote.
No llama APIs externas ni lee tokens, .env o secretos.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
INDEX_PATH = ROOT / "WebPage" / "assets_por_proyecto" / "semantic_visual_index.json"
CAMPAIGNS_DIR = ROOT / "Campanas"
LINTER_PATH = SCRIPTS_DIR / "check_social_copy.mjs"

# Esquema UTM oficial (RESUMEN_EJECUTIVO_DEMO_Y_PORTAFOLIO.md, seccion 6)
UTM_CHANNELS: dict[str, tuple[str, str]] = {
    "instagram": ("instagram", "organic_social"),
    "linkedin": ("linkedin", "organic_social"),
    "facebook": ("facebook", "organic_social"),
    "youtube_short": ("youtube", "video_short"),
    "youtube_horizontal": ("youtube", "video_horizontal"),
    "tiktok": ("tiktok", "video_vertical"),
}
# Hosts a los que se puede construir un enlace con UTM
UTM_ALLOWED_HOSTS = {"kadi.technology", "portal-cliente.kadi.technology"}
FORBIDDEN_HOSTS = {
    "prod-cliente.kadi.technology": "produccion real de la clinica (P-0)",
    "academia-privada.kadi.technology": "resuelve a una IP prohibida (P-0)",
    "demo-privada.kadi.technology": "aun sin DNS publico",
    "demo-retirada.kadi.technology": "retirado, sin DNS",
}
SNAKE_CASE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
LOTE_RE = re.compile(r"^LOTE-\d{2}$")


class SocialError(ValueError):
    """Error de validacion con mensaje en espanol."""


def build_utm_link(url: str, channel: str, campaign: str) -> str:
    """Devuelve la URL con utm_source, utm_medium y utm_campaign del esquema oficial."""
    if channel not in UTM_CHANNELS:
        raise SocialError(f"Canal invalido '{channel}'. Validos: {', '.join(sorted(UTM_CHANNELS))}")
    if not SNAKE_CASE.match(campaign or ""):
        raise SocialError("La campana debe estar en snake_case (minusculas, digitos y guion bajo).")
    parts = urlsplit(url.strip())
    if parts.scheme != "https":
        raise SocialError("El enlace debe usar https.")
    host = (parts.hostname or "").lower()
    if host in FORBIDDEN_HOSTS:
        raise SocialError(f"Host prohibido {host}: {FORBIDDEN_HOSTS[host]}.")
    if host not in UTM_ALLOWED_HOSTS:
        raise SocialError(
            f"Host '{host}' fuera del canon. Permitidos con UTM: {', '.join(sorted(UTM_ALLOWED_HOSTS))}."
        )
    source, medium = UTM_CHANNELS[channel]
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.startswith("utm_")]
    query = urlencode(kept + [("utm_source", source), ("utm_medium", medium), ("utm_campaign", campaign)])
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", query, parts.fragment))


def _load_index() -> dict[str, Any]:
    with INDEX_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _aspect_label(width: int, height: int) -> str:
    ratio = width / height
    candidates = {"16:9": 16 / 9, "9:16": 9 / 16, "4:5": 4 / 5, "1:1": 1.0, "3:4": 3 / 4, "4:3": 4 / 3}
    label, value = min(candidates.items(), key=lambda kv: abs(kv[1] - ratio))
    return label if abs(value - ratio) < 0.02 else f"{width}x{height}"


def list_assets(project: str | None = None, aspect_ratio: str | None = None, include_unreviewed: bool = False) -> dict[str, Any]:
    """Activos del indice semantico. Por defecto solo publishable=true y pii_check limpio."""
    index = _load_index()
    projects = index.get("projects", {})
    if project and project not in projects:
        raise SocialError(f"Proyecto '{project}' no existe. Validos: {', '.join(sorted(projects))}")
    wanted_aspect = aspect_ratio.strip() if aspect_ratio else None
    out: list[dict[str, Any]] = []
    for slug, data in projects.items():
        if project and slug != project:
            continue
        for asset in data.get("assets", []):
            publishable = asset.get("publishable")
            if not include_unreviewed and publishable is not True:
                continue
            if not include_unreviewed and asset.get("pii_check") != "clean":
                continue
            label = asset.get("aspect_ratio") or _aspect_label(asset["width_px"], asset["height_px"])
            if wanted_aspect and label != wanted_aspect:
                continue
            out.append(
                {
                    "project": slug,
                    "stage": data.get("metadata", {}).get("stage"),
                    "filename": asset["filename"],
                    "absolute_path": asset["absolute_path"],
                    "width_px": asset["width_px"],
                    "height_px": asset["height_px"],
                    "aspect_ratio": label,
                    "sha256": asset["sha256"],
                    "publishable": publishable,
                    "pii_check": asset.get("pii_check"),
                    "verified_claim": asset.get("verified_claim"),
                    "notes": asset.get("notes"),
                }
            )
    return {"count": len(out), "include_unreviewed": include_unreviewed, "assets": out}


def lote_dir(lote: str) -> Path:
    if not LOTE_RE.match(lote or ""):
        raise SocialError("El lote debe tener el formato LOTE-NN, por ejemplo LOTE-01.")
    path = CAMPAIGNS_DIR / lote
    if not path.is_dir():
        raise SocialError(f"No existe la carpeta del lote: {path}")
    return path


def read_pieces(lote: str) -> list[dict[str, Any]]:
    """Lee meta.json de cada carpeta de pieza del lote (dia_canal_slug/)."""
    base = lote_dir(lote)
    pieces = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir() and (p / "meta.json").is_file()):
        with (folder / "meta.json").open(encoding="utf-8") as fh:
            meta = json.load(fh)
        meta["folder"] = folder.name
        pieces.append(meta)
    pieces.sort(key=lambda m: (m["fecha"], m["hora_cdmx"], m["canal"]))
    return pieces


def build_draft_queue(lote: str) -> dict[str, Any]:
    pieces = read_pieces(lote)
    if not pieces:
        raise SocialError(f"El lote {lote} no tiene piezas (meta.json).")
    base = lote_dir(lote)
    pilares: dict[str, int] = {}
    canales: dict[str, int] = {}
    for p in pieces:
        pilares[p["pilar"]] = pilares.get(p["pilar"], 0) + 1
        canales[p["canal"]] = canales.get(p["canal"], 0) + 1
    drafts = []
    for p in pieces:
        drafts.append(
            {
                "id": p["id"],
                "estado": "BORRADOR",
                "requiere_aprobacion": "APROBADO-SOCIAL-LOTE-01",
                "fecha": p["fecha"],
                "hora_cdmx": p["hora_cdmx"],
                "canal": p["canal"],
                "formato": p["formato"],
                "pilar": p["pilar"],
                "tema": p["tema"],
                "campaign": p["campaign"],
                "utm_link": p["utm_link"],
                "copy": p["copy"],
                "hashtags": p["hashtags"],
                "alt_text": p["alt_text"],
                "asset_paths": p["asset_paths"],
                "asset_status": p.get("asset_status"),
                "sector": p.get("sector"),
                "titulo": p.get("titulo"),
                "carpeta": str(base / p["folder"]),
            }
        )
    return {
        "lote": lote,
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "estado_global": "BORRADOR_PENDIENTE_DE_FIRMA",
        "firma_requerida": "APROBADO-SOCIAL-LOTE-01",
        "publica_algo": False,
        "piezas_en_lote": len(drafts),
        "piezas_por_pilar": pilares,
        "piezas_por_canal": canales,
        "borradores": drafts,
    }


def get_calendar(lote: str) -> dict[str, Any]:
    queue = build_draft_queue(lote)
    days: dict[str, list[dict[str, Any]]] = {}
    for d in queue["borradores"]:
        days.setdefault(d["fecha"], []).append(
            {k: d[k] for k in ("id", "hora_cdmx", "canal", "formato", "pilar", "tema", "campaign")}
        )
    return {
        "lote": lote,
        "piezas_en_lote": queue["piezas_en_lote"],
        "piezas_por_pilar": queue["piezas_por_pilar"],
        "piezas_por_canal": queue["piezas_por_canal"],
        "dias": [{"fecha": k, "piezas": v} for k, v in sorted(days.items())],
    }


def export_draft_queue(lote: str, output_name: str = "draft_queue.json") -> dict[str, Any]:
    """Escribe el JSON de borradores dentro de la carpeta del lote. No publica nada."""
    if "/" in output_name or "\\" in output_name or not output_name.endswith(".json"):
        raise SocialError("output_name debe ser un nombre de archivo .json sin rutas.")
    queue = build_draft_queue(lote)
    target = lote_dir(lote) / output_name
    target.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"escrito": str(target), "piezas_en_lote": queue["piezas_en_lote"], "publica_algo": False}


FINDING_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+)\s{2}\[(?P<rule>[A-Z0-9_]+)\]\s{2}(?P<message>.*?)\s{2}->\s\"(?P<match>.*)\"$")


def lint_copy(text: str) -> dict[str, Any]:
    """Pasa el texto por scripts/check_social_copy.mjs (solo lectura de las reglas del portal)."""
    node = shutil.which("node")
    if not node:
        raise SocialError("No se encontro node en PATH; el linter es un script de Node.")
    with tempfile.TemporaryDirectory(prefix="kadi-lint-") as tmp:
        sample = Path(tmp) / "texto.md"
        sample.write_text(text, encoding="utf-8")
        proc = subprocess.run(
            [node, str(LINTER_PATH), str(sample), "--quiet"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            cwd=tmp,
            check=False,
        )
    if proc.returncode == 2:
        raise SocialError(f"Error de configuracion del linter: {proc.stderr.strip() or proc.stdout.strip()}")
    findings = []
    for raw in proc.stdout.splitlines():
        m = FINDING_RE.match(raw)
        if m:
            findings.append(
                {
                    "line": int(m["line"]),
                    "col": int(m["col"]),
                    "rule": m["rule"],
                    "message": m["message"],
                    "match": m["match"],
                }
            )
    return {"ok": proc.returncode == 0, "exit_code": proc.returncode, "findings": findings}
