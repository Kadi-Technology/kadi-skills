"""Import an authentic Narrador recording, validate it, and align its six scenes locally.

This script deliberately has no TTS fallback. `--speaker Narrador` is an operator
declaration; the script validates audibility and script alignment, not identity.
"""
from pathlib import Path
import argparse
import difflib
import json
import math
import os
import re
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/video-kadi"
VOICE_OUT = OUT / "voice-narrador"
STORY_PATH = ROOT / "scripts/video/storyboard.json"
TIMELINE_PATH = OUT / "timeline.json"
EXPECTED_SPEAKER = "Narrador"
TEST_FIXTURE_SPEAKER = "TEST-ONLY-Salome"
MIN_SCENE_MATCH = 0.72


def tokens(value: str) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", plain)


def flatten_asr_words(segments) -> list[dict]:
    flattened = []
    for segment in segments:
        for item in segment.words or []:
            raw = (item.word or "").strip()
            pieces = tokens(raw)
            if not pieces:
                continue
            start, end = float(item.start), float(item.end)
            step = max(0.01, end - start) / len(pieces)
            for index, piece in enumerate(pieces):
                flattened.append({
                    "token": piece,
                    "text": raw if len(pieces) == 1 else piece,
                    "start": start + step * index,
                    "end": start + step * (index + 1),
                })
    return flattened


def align_scene(expected_text: str, recognized: list[dict], cursor: int) -> tuple[int, int, float]:
    expected = tokens(expected_text)
    if not expected:
        raise ValueError("Una escena del guion no contiene texto para alinear.")
    min_size = max(1, math.floor(len(expected) * 0.62))
    max_size = max(min_size, math.ceil(len(expected) * 1.42))
    best = (cursor, min(cursor + min_size, len(recognized)), 0.0)
    last_start = len(recognized) - min_size
    for start in range(cursor, last_start + 1):
        for size in range(min_size, min(max_size, len(recognized) - start) + 1):
            candidate = [item["token"] for item in recognized[start:start + size]]
            score = difflib.SequenceMatcher(None, expected, candidate, autojunk=False).ratio()
            if score > best[2]:
                best = (start, start + size, score)
    return best


def run_asr(model_path: str, audio_path: Path, device: str, compute_type: str) -> list[dict]:
    # local_files_only prevents an unplanned model download or network call.
    from faster_whisper import WhisperModel

    model = WhisperModel(model_path, device=device, compute_type=compute_type, local_files_only=True)
    segments, _info = model.transcribe(
        str(audio_path), language="es", word_timestamps=True, vad_filter=True,
        condition_on_previous_text=False, beam_size=5,
    )
    return flatten_asr_words(segments)


def encode_clip(source: Path, start: float, end: float, target: Path) -> None:
    duration = max(0.05, end - start)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source), "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}", "-vn", "-ac", "1", "-ar", "48000",
        "-af", "loudnorm=I=-20:TP=-2:LRA=11", "-c:a", "libmp3lame", "-b:a", "192k",
        str(target),
    ], check=True)


def make_timeline(story: dict, clip_info: list[dict]) -> dict:
    cursor = 0.65
    scenes = []
    for index, (scene, imported) in enumerate(zip(story["scenes"], clip_info)):
        voice_start = cursor
        scene_start = 0.0 if index == 0 else voice_start - 0.35
        length = imported["duration"]
        scenes.append({
            **scene,
            "start": scene_start,
            "voiceStart": voice_start,
            "voiceDuration": length,
            "end": voice_start + length + 0.35,
            "words": imported["words"],
        })
        cursor += length + 0.75
    scenes[-1]["end"] += 2.1
    for index in range(len(scenes) - 1):
        scenes[index]["end"] = scenes[index + 1]["start"]
    return {**story, "duration": scenes[-1]["end"], "scenes": scenes}


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="MP3, WAV, M4A o captura con la voz auténtica de Narrador")
    parser.add_argument("--speaker", required=True, choices=[EXPECTED_SPEAKER, TEST_FIXTURE_SPEAKER], help="Etiqueta declarada; TEST-ONLY-Salome sólo sirve para fixtures aisladas")
    parser.add_argument("--model", required=True, help="Ruta local a un modelo faster-whisper ya instalado; no se descargan modelos")
    parser.add_argument("--storyboard", type=Path, default=STORY_PATH, help="Storyboard que debe alinearse (por defecto, el del proyecto)")
    parser.add_argument("--output-dir", type=Path, default=VOICE_OUT, help="Directorio de clips/manifest; debe estar dentro del workspace")
    parser.add_argument("--timeline-output", type=Path, default=TIMELINE_PATH, help="Archivo de timeline; debe estar dentro del workspace")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()

    from audio_contract import extract_channel, probe_duration, require_audible_audio, sha256_file

    source = args.input.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"No existe el audio indicado: {source}")
    duration = probe_duration(source)
    if not 5 <= duration <= 600:
        raise SystemExit(f"Duración no admitida ({duration:.2f} s); se espera una toma de 5 s a 10 min.")
    try:
        source_metrics = require_audible_audio(source)
    except ValueError as error:
        raise SystemExit(f"{error} No se modificó ni copió el archivo de entrada.") from None

    story_path = args.storyboard.expanduser().resolve()
    voice_out = args.output_dir.expanduser().resolve()
    timeline_output = args.timeline_output.expanduser().resolve()
    for output_path in (voice_out, timeline_output):
        try:
            output_path.relative_to(ROOT)
        except ValueError:
            raise SystemExit("Las rutas de salida deben permanecer dentro de este workspace.") from None
    if args.speaker == TEST_FIXTURE_SPEAKER:
        test_root=(ROOT/"output"/"tests").resolve()
        for output_path in (voice_out,timeline_output):
            try:
                output_path.relative_to(test_root)
            except ValueError:
                raise SystemExit("La etiqueta TEST-ONLY-Salome sólo puede escribir dentro de output/tests.") from None

    story = json.loads(story_path.read_text(encoding="utf-8"))
    if story.get("voice") != "Narrador (grabación importada)":
        raise SystemExit("El storyboard no declara una grabación importada de Narrador; no se procesará con otra voz.")
    if len(story.get("scenes", [])) != 6:
        raise SystemExit("El importador requiere exactamente seis escenas en el storyboard.")

    # Create output folders only after the input and its selected channel pass signal checks.
    stage_parent = voice_out.parent
    stage_parent.mkdir(parents=True, exist_ok=True)
    voice_out.mkdir(parents=True, exist_ok=True)
    stage_prefix = "test-only-salome-import-" if args.speaker == TEST_FIXTURE_SPEAKER else "narrador-import-"
    with tempfile.TemporaryDirectory(prefix=stage_prefix, dir=stage_parent, ignore_cleanup_errors=True) as temp_name:
        stage = Path(temp_name)
        channel_audio = stage / "selected-channel.wav"
        extract_channel(source, channel_audio, source_metrics["selectedChannel"])
        try:
            transcript_words = run_asr(args.model, channel_audio, args.device, args.compute_type)
        except Exception as error:
            raise SystemExit(f"No se pudo transcribir localmente. Verifica que --model apunte a un modelo faster-whisper ya instalado: {error}") from None
        if not transcript_words:
            raise SystemExit("La transcripción local no encontró palabras; no se generó ningún archivo de salida.")

        clips = []
        cursor = 0
        for scene in story["scenes"]:
            first, last, score = align_scene(scene["voice"], transcript_words, cursor)
            if score < MIN_SCENE_MATCH:
                raise SystemExit(
                    f"Escena {scene['id']} no alineada con suficiente confianza ({score:.2f} < {MIN_SCENE_MATCH:.2f}); "
                    "no se generó ningún archivo de salida. Revisa la toma y el guion."
                )
            selected = transcript_words[first:last]
            clip_start = max(0.0, selected[0]["start"] - 0.16)
            clip_end = min(duration, selected[-1]["end"] + 0.28)
            if clip_end <= clip_start:
                raise SystemExit(f"La escena {scene['id']} tiene límites de audio inválidos.")

            clip_path = stage / f"voice-{scene['id']}.mp3"
            encode_clip(channel_audio, clip_start, clip_end, clip_path)
            metrics = require_audible_audio(clip_path)
            clip_duration = probe_duration(clip_path)
            word_items = [
                {
                    "offset": max(0.0, item["start"] - clip_start),
                    "duration": max(0.02, item["end"] - item["start"]),
                    "text": item["text"],
                }
                for item in selected
            ]
            words_path = stage / f"words-{scene['id']}.json"
            words_path.write_text(json.dumps(word_items, ensure_ascii=False, indent=2), encoding="utf-8")
            clips.append({
                "id": scene["id"], "audioPath": clip_path, "wordsPath": words_path,
                "audioSha256": sha256_file(clip_path), "wordsSha256": sha256_file(words_path),
                "duration": clip_duration, "sourceStart": clip_start, "sourceEnd": clip_end,
                "alignmentScore": score, "metrics": metrics, "words": word_items,
            })
            cursor = last

        timeline = make_timeline(story, clips)
        timeline_bytes = (json.dumps(timeline, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        timeline_stage = stage / "timeline.json"
        timeline_stage.write_bytes(timeline_bytes)
        story_hash = sha256_file(story_path)
        manifest = {
            "status": "validated_import",
            "speaker": args.speaker,
            "speakerIdentity": "test_fixture_salome_not_narrador" if args.speaker==TEST_FIXTURE_SPEAKER else "declared_by_operator_not_machine_verified",
            "sourceSha256": sha256_file(source),
            "sourceDuration": duration,
            "sourceMetrics": source_metrics,
            "model": Path(args.model).name,
            "language": "es",
            "storyboardSha256": story_hash,
            "timelineSha256": sha256_file(timeline_stage),
            "scenes": [
                {key: clip[key] for key in ("id", "audioSha256", "wordsSha256", "duration", "sourceStart", "sourceEnd", "alignmentScore", "metrics")}
                for clip in clips
            ],
            "validatedAtUtc": datetime.now(timezone.utc).isoformat(),
        }

        # Commit generated clips only after all six scenes passed audibility and alignment.
        for clip in clips:
            for staged_key, final_name in (("audioPath", f"voice-{clip['id']}.mp3"), ("wordsPath", f"words-{clip['id']}.json")):
                atomic_write(voice_out / final_name, clip[staged_key].read_bytes())
        atomic_write(timeline_output, timeline_bytes)
        atomic_write(voice_out / "import-manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    if Path(temp_name).exists():
        marker = "TEST ONLY: synthesized Salome fixture; never use as Narrador product voice.\n" if args.speaker == TEST_FIXTURE_SPEAKER else "Temporary audio remains after Windows denied cleanup; remove after checking open handles.\n"
        try:
            (Path(temp_name) / "TEMPORARY_AUDIO_NOTICE.txt").write_text(marker, encoding="utf-8")
        except OSError:
            pass
        print("TEMPORARY_AUDIO_CLEANUP_PENDING", temp_name, flush=True)

    print(json.dumps({"status": "validated_import", "speaker": args.speaker, "duration": round(timeline["duration"], 2), "scenes": [round(item["alignmentScore"], 3) for item in clips]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
