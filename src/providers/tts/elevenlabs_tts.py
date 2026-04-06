"""ElevenLabs TTS provider implementation."""

import os
from pathlib import Path
from .base import BaseTTSProvider


class ElevenLabsTTSProvider(BaseTTSProvider):

    def __init__(self, voice_id: str, model_id: str = "eleven_multilingual_v2"):
        from elevenlabs import ElevenLabs

        self.client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        self.voice_id = voice_id
        self.model_id = model_id

    def synthesize(self, text: str, output_path: Path) -> Path:
        audio_generator = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id=self.model_id,
        )

        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        return output_path
