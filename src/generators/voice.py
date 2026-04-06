"""Voice generation — converts script text to voiceover audio."""

from pathlib import Path

from ..models import VoiceResult
from ..providers.tts import BaseTTSProvider
from ..config import get_run_dir


class VoiceGenerator:

    def __init__(self, tts: BaseTTSProvider, config: dict):
        self.tts = tts
        self.config = config

    def generate(self, script_text: str, run_id: str) -> VoiceResult:
        run_dir = get_run_dir(self.config, run_id)
        output_path = run_dir / "voiceover.mp3"

        self.tts.synthesize(script_text, output_path)

        size_kb = output_path.stat().st_size / 1024
        print(f"[Voice] Generated {size_kb:.0f} KB audio → {output_path.name}")
        return VoiceResult(audio_path=output_path)
