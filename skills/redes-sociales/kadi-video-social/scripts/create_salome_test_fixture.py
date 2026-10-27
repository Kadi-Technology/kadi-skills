"""Create a TEST-ONLY Salome speech fixture; never use it as KADI product narration."""
from pathlib import Path
import asyncio
import hashlib
import json

import edge_tts


ROOT = Path(__file__).resolve().parents[2]
STORY_PATH = ROOT / "scripts/video/storyboard.json"
TESTS = ROOT / "output/tests"
TARGET = TESTS / "salome-fixture.mp3"


async def main():
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))
    text = "\n\n".join(scene["voice"] for scene in story["scenes"])
    TESTS.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(text, "es-CO-SalomeNeural", rate="-4%", pitch="+2Hz").save(str(TARGET))
    fixture = {
        "purpose": "TEST ONLY: import-pipeline QA; this is synthesized Salome speech, not Narrador",
        "voice": "es-CO-SalomeNeural",
        "storyboardSha256": hashlib.sha256(STORY_PATH.read_bytes()).hexdigest(),
        "fixtureSha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
    }
    (TESTS / "salome-fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    print("TEST_FIXTURE_READY", TARGET, TARGET.stat().st_size)


if __name__ == "__main__":
    asyncio.run(main())
