#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""KADI Swarm v3.0.0 Apex - Shadow Vault (copias sombra y rollback atomico por agente).

Layout dentro de ``.swarm_state/shadows/[agent_id]/``::

    manifest.json   -> territorios, archivos preexistentes (+SHA-256 original) y directorios
    files/<rel>     -> copia exacta del estado previo de cada archivo preexistente

El snapshot es *aditivo e idempotente*: un territorio ya capturado NO se vuelve a
capturar (si no, un heartbeat sobrescribiria la copia limpia con archivos ya editados).

100% libreria estandar de Python 3.13.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

STATE_DIRNAME = ".swarm_state"
IGNORED_DIRS = {STATE_DIRNAME}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()  # hash binario exacto: la copia sombra es byte-a-byte


def _key(rel: str) -> str:
    return rel.lower()  # NTFS case-insensitive


def _atomic_copy(src: Path, dst: Path) -> None:
    """Copia ``src`` -> ``dst`` con reemplazo atomico (temp en el mismo directorio)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=dst.parent, prefix=".kadi_tmp_")
    try:
        with tmp, src.open("rb") as fh:
            shutil.copyfileobj(fh, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.copystat(src, tmp.name)
        os.replace(tmp.name, dst)
    except BaseException:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def _atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", dir=path.parent, suffix=".tmp")
    try:
        with tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp.name, path)
    except BaseException:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


class ShadowVault:
    """Bóveda de sombras por agente."""

    @staticmethod
    def shadow_dir(workspace: Path, agent_id: str) -> Path:
        return Path(workspace).resolve() / STATE_DIRNAME / "shadows" / agent_id

    @staticmethod
    def manifest_path(workspace: Path, agent_id: str) -> Path:
        return ShadowVault.shadow_dir(workspace, agent_id) / "manifest.json"

    @staticmethod
    def load_manifest(workspace: Path, agent_id: str) -> dict[str, Any] | None:
        mp = ShadowVault.manifest_path(workspace, agent_id)
        if not mp.is_file():
            return None
        return json.loads(mp.read_text(encoding="utf-8"))

    @staticmethod
    def _to_rel(workspace: Path, raw: str | Path) -> tuple[Path, str]:
        absolute = (workspace / raw).resolve()
        try:
            rel = absolute.relative_to(workspace).as_posix()
        except ValueError as exc:
            raise ValueError(f"ruta fuera del workspace: {absolute}") from exc
        return absolute, ("" if rel == "." else rel)

    @staticmethod
    def _under(rel: str, parent: str) -> bool:
        r, p = _key(rel), _key(parent)
        return p == "" or r == p or r.startswith(p + "/")

    @staticmethod
    def _walk(root: Path) -> Iterable[Path]:
        if root.is_file():
            yield root
            return
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for name in filenames:
                yield Path(dirpath) / name

    @classmethod
    def capture_snapshot(cls, workspace: Path, agent_id: str, paths: list[str | Path]) -> dict[str, Any]:
        """Respalda el estado previo de ``paths`` (archivos o carpetas) para ``agent_id``.

        Territorios ya capturados se omiten. Devuelve el manifiesto resultante con
        ``newly_captured_files`` / ``newly_captured_territories`` informativos.
        """
        workspace = Path(workspace).resolve()
        sdir = cls.shadow_dir(workspace, agent_id)
        manifest = cls.load_manifest(workspace, agent_id) or {
            "agent_id": agent_id,
            "workspace_root": str(workspace),
            "captured_at": datetime.now().astimezone().isoformat(timespec="microseconds"),
            "territories": [],
            "territory_existed": {},
            "files": {},
            "dirs": [],
        }
        known_files = {_key(k) for k in manifest["files"]}
        captured_before = list(manifest["territories"])
        new_files = 0
        new_territories: list[str] = []

        for raw in paths:
            absolute, rel = cls._to_rel(workspace, raw)
            if any(cls._under(rel, t) for t in captured_before):
                continue  # ya cubierto por un snapshot previo (idempotencia)
            if _key(rel) in {_key(t) for t in manifest["territories"]}:
                continue
            manifest["territories"].append(rel)
            manifest["territory_existed"][rel] = absolute.exists()
            new_territories.append(rel)
            if not absolute.exists():
                continue
            if absolute.is_dir():
                dirs = [absolute] + [Path(d) for d, _, _ in os.walk(absolute)
                                     if not any(p in IGNORED_DIRS for p in Path(d).relative_to(workspace).parts)]
                for d in dirs:
                    drel = d.relative_to(workspace).as_posix()
                    if drel not in manifest["dirs"]:
                        manifest["dirs"].append(drel)
            for f in cls._walk(absolute):
                frel = f.relative_to(workspace).as_posix()
                if _key(frel) in known_files:
                    continue
                if any(cls._under(frel, t) for t in captured_before):
                    continue  # pertenece a un territorio previo (posible archivo ya editado)
                _atomic_copy(f, sdir / "files" / frel)
                manifest["files"][frel] = {"sha256": _sha256(f), "size": f.stat().st_size}
                known_files.add(_key(frel))
                new_files += 1

        manifest["updated_at"] = datetime.now().astimezone().isoformat(timespec="microseconds")
        _atomic_json(cls.manifest_path(workspace, agent_id), manifest)
        manifest = dict(manifest)
        manifest["newly_captured_files"] = new_files
        manifest["newly_captured_territories"] = new_territories
        return manifest

    @classmethod
    def restore(cls, workspace: Path, agent_id: str) -> dict[str, Any]:
        """Rollback quirurgico: restaura archivos modificados/borrados y elimina los nuevos."""
        started = time.perf_counter()
        workspace = Path(workspace).resolve()
        manifest = cls.load_manifest(workspace, agent_id)
        if manifest is None:
            raise FileNotFoundError(f"sin shadow snapshot para el agente '{agent_id}'")
        sdir = cls.shadow_dir(workspace, agent_id)
        original = {_key(k): k for k in manifest["files"]}
        restored: list[str] = []
        deleted: list[str] = []
        unchanged = 0

        for rel, meta in manifest["files"].items():
            dst = workspace / rel
            if dst.is_file() and _sha256(dst) == meta["sha256"]:
                unchanged += 1
                continue
            _atomic_copy(sdir / "files" / rel, dst)
            restored.append(rel)

        known_dirs = {_key(d) for d in manifest["dirs"]}
        for territory in manifest["territories"]:
            root = (workspace / territory).resolve() if territory else workspace
            if not root.exists():
                continue
            for f in list(cls._walk(root)):
                frel = f.relative_to(workspace).as_posix()
                if _key(frel) not in original:
                    f.unlink()
                    deleted.append(frel)
            if root.is_dir():
                for dirpath, _, _ in os.walk(root, topdown=False):
                    d = Path(dirpath)
                    drel = d.relative_to(workspace).as_posix()
                    if d == workspace or drel.split("/")[0] in IGNORED_DIRS:
                        continue
                    if _key(drel) not in known_dirs and not any(d.iterdir()):
                        d.rmdir()

        return {
            "agent_id": agent_id,
            "restored": sorted(restored),
            "deleted": sorted(deleted),
            "unchanged": unchanged,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    @classmethod
    def discard(cls, workspace: Path, agent_id: str) -> bool:
        sdir = cls.shadow_dir(workspace, agent_id)
        if sdir.exists():
            shutil.rmtree(sdir, ignore_errors=True)
            return True
        return False
