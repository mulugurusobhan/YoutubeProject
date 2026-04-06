"""OpenAI TTS provider implementation."""

from pathlib import Path
from openai import OpenAI
from .base import BaseTTSProvider


class OpenAITTSProvider(BaseTTSProvider):

    def __init__(self, model: str = "tts-1-hd", voice: str = "nova"):
        self.client = OpenAI()
        self.model = model
        self.voice = voice

    def synthesize(self, text: str, output_path: Path) -> Path:
        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
        )
        response.stream_to_file(str(output_path))
        return output_path
