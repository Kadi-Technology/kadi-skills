"""Audio checks shared by the Narrador import pipeline and the video renderer."""
from pathlib import Path
import json
import math
import subprocess

import numpy as np


SAMPLE_RATE = 48_000
MIN_PEAK_DBFS = -60.0
MIN_RMS_DBFS = -72.0
MIN_ACTIVE_FRAME_DBFS = -65.0
MIN_ACTIVE_FRAME_FRACTION = 0.01


def probe_duration(path: Path) -> float:
    value = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    ).strip()
    return float(value)


def audio_metrics(path: Path) -> dict:
    stream = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=channels,sample_rate", "-of", "json", str(path)], text=True,
    ))["streams"][0]
    channels = int(stream["channels"])
    if not 1 <= channels <= 8:
        raise ValueError(f"Cantidad de canales no admitida: {channels}.")
    raw = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ar", str(SAMPLE_RATE),
         "-acodec", "pcm_f32le", "-f", "f32le", "-"]
    )
    interleaved = np.frombuffer(raw, dtype="<f4")
    if not interleaved.size:
        return {"duration": 0.0, "peakDbfs": -math.inf, "rmsDbfs": -math.inf,
                "activeFrameFraction": 0.0, "channels": channels, "selectedChannel": 0}
    if interleaved.size % channels:
        raise ValueError("La decodificación produjo una trama de audio incompleta.")
    samples = interleaved.reshape(-1, channels)
    peak_by_channel = np.max(np.abs(samples), axis=0)
    rms_by_channel = np.sqrt(np.mean(samples * samples, axis=0, dtype=np.float64))
    selected = int(np.argmax(rms_by_channel))
    mono = samples[:, selected]
    peak = float(peak_by_channel[selected])
    rms = float(rms_by_channel[selected])
    frame_size = SAMPLE_RATE // 50  # 20 ms
    usable = mono[:len(mono) // frame_size * frame_size].reshape(-1, frame_size)
    frame_rms = np.sqrt(np.mean(usable * usable, axis=1, dtype=np.float64)) if usable.size else np.array([])
    active = float(np.mean(frame_rms >= 10 ** (MIN_ACTIVE_FRAME_DBFS / 20))) if frame_rms.size else 0.0
    db = lambda value: 20 * math.log10(value) if value > 0 else -math.inf
    return {
        "duration": len(mono) / SAMPLE_RATE,
        "peakDbfs": db(peak),
        "rmsDbfs": db(rms),
        "activeFrameFraction": active,
        "channels": channels,
        "selectedChannel": selected,
        "channelPeakDbfs": [db(float(value)) for value in peak_by_channel],
        "channelRmsDbfs": [db(float(value)) for value in rms_by_channel],
    }


def extract_channel(source: Path, target: Path, channel: int) -> None:
    stream = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=channels", "-of", "json", str(source)], text=True,
    ))["streams"][0]
    channels = int(stream["channels"])
    if not 0 <= channel < channels:
        raise ValueError(f"Canal {channel} fuera de rango para {channels} canales.")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source), "-vn", "-af",
        f"pan=mono|c0=c{channel}", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(target),
    ], check=True)


def require_audible_audio(path: Path, metrics: dict | None = None) -> dict:
    metrics = metrics or audio_metrics(path)
    if metrics["peakDbfs"] < MIN_PEAK_DBFS:
        raise ValueError(f"Audio rechazado: pico {metrics['peakDbfs']:.1f} dBFS, debajo de {MIN_PEAK_DBFS:.0f} dBFS.")
    if metrics["rmsDbfs"] < MIN_RMS_DBFS:
        raise ValueError(f"Audio rechazado: RMS {metrics['rmsDbfs']:.1f} dBFS, debajo de {MIN_RMS_DBFS:.0f} dBFS.")
    if metrics["activeFrameFraction"] < MIN_ACTIVE_FRAME_FRACTION:
        raise ValueError("Audio rechazado: no hay suficientes tramas audibles para considerarlo una voz.")
    return metrics


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_voice_import(story_path: Path, timeline_path: Path, voice_dir: Path, expected_speaker: str = "Narrador") -> dict:
    story = load_json(story_path)
    if story.get("voice") != "Narrador (grabación importada)":
        raise ValueError("El storyboard no solicita audio importado de Narrador.")
    manifest_path = voice_dir / "import-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("No hay importación de voz validada.")
    manifest = load_json(manifest_path)
    expected_identity = "test_fixture_salome_not_narrador" if expected_speaker == "TEST-ONLY-Salome" else "declared_by_operator_not_machine_verified"
    if manifest.get("status") != "validated_import" or manifest.get("speaker") != expected_speaker or manifest.get("speakerIdentity") != expected_identity:
        raise ValueError("La etiqueta/procedencia de la voz no coincide con el modo solicitado.")
    if manifest.get("storyboardSha256") != sha256_file(story_path):
        raise ValueError("El storyboard cambió después de la importación de voz.")
    if manifest.get("timelineSha256") != sha256_file(timeline_path):
        raise ValueError("La timeline no coincide con la importación de voz.")
    timeline = load_json(timeline_path)
    story_scenes = story.get("scenes", [])
    timeline_scenes = timeline.get("scenes", [])
    ids = [scene["id"] for scene in story_scenes]
    if len(ids) != 6 or [scene["id"] for scene in timeline_scenes] != ids:
        raise ValueError("La importación debe contener las seis escenas actuales en orden.")
    if any(timeline_scenes[index].get("voice") != story_scenes[index].get("voice") for index in range(6)):
        raise ValueError("La timeline contiene texto distinto al storyboard actual.")
    entries = {entry["id"]: entry for entry in manifest.get("scenes", [])}
    if set(entries) != set(ids):
        raise ValueError("El manifiesto no contiene las seis escenas.")
    for scene_id in ids:
        audio = voice_dir / f"voice-{scene_id}.mp3"
        words = voice_dir / f"words-{scene_id}.json"
        entry = entries[scene_id]
        if not audio.is_file() or sha256_file(audio) != entry.get("audioSha256"):
            raise ValueError(f"El audio de la escena {scene_id} no coincide con el manifiesto.")
        if not words.is_file() or sha256_file(words) != entry.get("wordsSha256"):
            raise ValueError(f"Las marcas de palabra de la escena {scene_id} no coinciden con el manifiesto.")
        require_audible_audio(audio)
    return manifest
