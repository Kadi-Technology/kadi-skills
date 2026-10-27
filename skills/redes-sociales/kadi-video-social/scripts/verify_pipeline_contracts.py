"""Run isolated audio, hash, cache, and publication-failure checks in output/tests."""
from pathlib import Path
import argparse
import json
import os
import shutil
import tempfile
import wave

import numpy as np

from audio_contract import audio_metrics, extract_channel, require_audible_audio, sha256_file, validate_voice_import
from prepare_audio import align_scene, tokens
from publication import publish_artifacts, stage_validate_publish
import render_video


ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "output/tests"
STORY_PATH = ROOT / "scripts/video/storyboard.json"
PUBLIC = ROOT / "src/assets/videos"
VIDEO_OUT = ROOT / "output/video-kadi"


def write_wav(path: Path, samples: np.ndarray, channels: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(48_000)
        audio.writeframes((pcm * 32767).astype("<i2").tobytes())


def check_signal_contract() -> None:
    rate = 48_000
    times = np.arange(rate * 6, dtype=np.float32) / rate
    silence = TESTS / "contract-silence.wav"
    phase = TESTS / "contract-phase-cancel.wav"
    selected = TESTS / "contract-selected-channel.wav"
    write_wav(silence, np.zeros(rate * 6, dtype=np.float32), 1)
    signal = 0.2 * np.sin(2 * np.pi * 440 * times)
    write_wav(phase, np.stack((signal, -signal), axis=1), 2)
    try:
        require_audible_audio(silence)
    except ValueError:
        pass
    else:
        raise AssertionError("El contrato aceptó silencio digital.")
    metrics = require_audible_audio(phase)
    if metrics["channels"] != 2 or metrics["selectedChannel"] not in (0, 1):
        raise AssertionError("El medidor no seleccionó un canal estéreo.")
    extract_channel(phase, selected, metrics["selectedChannel"])
    selected_metrics = require_audible_audio(selected)
    if selected_metrics["peakDbfs"] < -20:
        raise AssertionError("La voz sintética se canceló al extraer el canal elegido.")
    print("AUDIO_CONTRACT_OK", json.dumps({"silence": "rejected", "selectedChannel": metrics["selectedChannel"], "phasePeakDbfs": metrics["peakDbfs"]}))


def check_scene05_alignment() -> None:
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))
    stale = "Configura la identidad de tu clínica y los accesos según la función de cada persona. Revisa con nosotros qué módulos y acompañamiento necesita tu operación."
    records = [{"token": token, "start": i*0.2, "end": i*0.2+0.15} for i, token in enumerate(tokens(stale))]
    _first, _last, score = align_scene(story["scenes"][4]["voice"], records, 0)
    if score >= 0.72:
        raise AssertionError(f"El guion viejo de escena 05 pasó el umbral de alineación: {score:.3f}")
    print("SCENE05_STALE_TEXT_REJECTED", round(score, 3))


def check_import_hashes(import_dir: Path) -> None:
    voice_dir = import_dir / "voice-narrador"
    if not (voice_dir / "import-manifest.json").is_file():
        voice_dir = import_dir / "test-fixture-salome"
    timeline = import_dir / "timeline.json"
    manifest = validate_voice_import(STORY_PATH, timeline, voice_dir, "TEST-ONLY-Salome")
    old_cached = VIDEO_OUT / "voice-05.mp3"
    imported05 = voice_dir / "voice-05.mp3"
    if old_cached.is_file() and sha256_file(old_cached) == sha256_file(imported05):
        raise AssertionError("La escena 05 parece reutilizar el caché histórico.")

    stale_story = json.loads(STORY_PATH.read_text(encoding="utf-8"))
    stale_story["scenes"][4]["voice"] = "Configura la identidad de tu clínica y los accesos según la función de cada persona. Revisa con nosotros qué módulos y acompañamiento necesita tu operación."
    stale_path = TESTS / "storyboard-stale-scene05.json"
    stale_path.write_text(json.dumps(stale_story, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        validate_voice_import(stale_path, timeline, voice_dir, "TEST-ONLY-Salome")
    except ValueError as error:
        if "storyboard" not in str(error):
            raise
    else:
        raise AssertionError("La línea de tiempo aceptó el storyboard viejo de escena 05.")

    with tempfile.TemporaryDirectory(prefix="tampered-import-", dir=TESTS) as temporary:
        tampered = Path(temporary) / "voice-narrador"
        shutil.copytree(voice_dir, tampered)
        with (tampered / "voice-05.mp3").open("ab") as stream:
            stream.write(b"stale-cache-probe")
        try:
            validate_voice_import(STORY_PATH, timeline, tampered, "TEST-ONLY-Salome")
        except ValueError as error:
            if "escena 05" not in str(error):
                raise
        else:
            raise AssertionError("La validación aceptó audio scene05 con hash cambiado.")

    try:
        validate_voice_import(STORY_PATH, VIDEO_OUT / "timeline.json", VIDEO_OUT / "voice-narrador", "Narrador")
    except ValueError:
        pass
    else:
        raise AssertionError("Los archivos raíz voice-01..06 bastaron sin un manifiesto Narrador validado.")
    if manifest.get("speakerIdentity") != "test_fixture_salome_not_narrador":
        raise AssertionError("El manifiesto de fixture no quedó marcado como Salomé de prueba.")
    print("IMPORT_HASHES_OK", "test fixture is Salome; no Narrador identity claim")


def check_encoder_failure_keeps_public_hashes() -> None:
    names = ("kadi-en-accion.mp4", "kadi-en-accion.es.vtt", "kadi-en-accion-transcripcion.txt", "kadi-en-accion-poster.webp")
    destinations = {name: PUBLIC / name for name in names}
    before = {name: sha256_file(path) for name, path in destinations.items()}

    def builder(stage: Path):
        (stage / "kadi-en-accion.es.vtt").write_text("candidate captions", encoding="utf-8")
        def injected_encoder(_silent):
            raise RuntimeError("injected MoviePy/FFmpeg encoder failure")
        render_video.encode_video_stage(stage,picture_encoder=injected_encoder)

    try:
        stage_validate_publish(TESTS, destinations, builder, lambda _stage: None)
    except RuntimeError as error:
        if "encoder failure" not in str(error):
            raise
    else:
        raise AssertionError("El encoder de prueba debía fallar antes del publish.")
    after = {name: sha256_file(path) for name, path in destinations.items()}
    if before != after:
        raise AssertionError("El fallo de encoder modificó archivos públicos.")
    print("ENCODER_FAILURE_PUBLIC_HASHES_UNCHANGED")


def check_replace_rollback() -> None:
    with tempfile.TemporaryDirectory(prefix="publish-rollback-", dir=TESTS) as temporary:
        root = Path(temporary)
        stage = root / "stage"
        public = root / "public"
        stage.mkdir(); public.mkdir()
        outputs = {"one.txt": public / "one.txt", "two.txt": public / "two.txt"}
        outputs["one.txt"].write_text("old-one", encoding="utf-8")
        outputs["two.txt"].write_text("old-two", encoding="utf-8")
        (stage / "one.txt").write_text("new-one", encoding="utf-8")
        (stage / "two.txt").write_text("new-two", encoding="utf-8")
        calls = 0
        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected second replace failure")
            os.replace(source, destination)
        try:
            publish_artifacts(stage, outputs, replace=fail_second)
        except OSError:
            pass
        else:
            raise AssertionError("La segunda sustitución de prueba debía fallar.")
        if outputs["one.txt"].read_text(encoding="utf-8") != "old-one" or outputs["two.txt"].read_text(encoding="utf-8") != "old-two":
            raise AssertionError("El rollback no restauró el conjunto público de prueba.")
    print("MULTIFILE_ROLLBACK_OK")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-dir",type=Path,default=TESTS/"salome-import",help="Aislamiento generado por prepare_audio.py en modo TEST-ONLY-Salome")
    args=parser.parse_args()
    TESTS.mkdir(parents=True, exist_ok=True)
    check_signal_contract()
    check_scene05_alignment()
    check_encoder_failure_keeps_public_hashes()
    check_replace_rollback()
    import_dir = args.import_dir.expanduser().resolve()
    if import_dir.is_dir():
        check_import_hashes(import_dir)
    else:
        print("IMPORT_HASHES_SKIPPED", "create Salome fixture and run prepare_audio first")


if __name__ == "__main__":
    main()
