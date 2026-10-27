"""Stage, validate, then replace a related set of public video assets together."""
from pathlib import Path
import os
import shutil
import tempfile


def publish_artifacts(stage: Path, outputs: dict[str, Path], replace=os.replace) -> None:
    """Replace destinations only after every staged file exists; restore on commit failure."""
    staged = {name: stage / name for name in outputs}
    missing = [str(path) for path in staged.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Faltan artefactos validados: " + ", ".join(missing))

    backup_dir = stage / "backups"
    backup_dir.mkdir()
    had_original = {}
    for index, destination in enumerate(outputs.values()):
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / str(index)
        had_original[destination] = destination.is_file()
        if had_original[destination]:
            shutil.copy2(destination, backup)

    replaced = []
    try:
        for name, destination in outputs.items():
            replace(staged[name], destination)
            replaced.append(destination)
    except Exception:
        for index, destination in reversed(list(enumerate(outputs.values()))):
            if destination not in replaced:
                continue
            if had_original[destination]:
                backup_copy = stage / f"restore-{index}"
                shutil.copy2(backup_dir / str(index), backup_copy)
                replace(backup_copy, destination)
            elif destination.exists():
                destination.unlink()
        raise


def stage_validate_publish(stage_parent: Path, outputs: dict[str, Path], build, validate, replace=os.replace) -> None:
    """Keep partial encoder output private and publish only after validation succeeds."""
    stage_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="web-video-", dir=stage_parent) as stage_name:
        stage = Path(stage_name)
        build(stage)
        validate(stage)
        publish_artifacts(stage, outputs, replace=replace)
