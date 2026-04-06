"""Azure OpenAI TTS provider — uses gpt-audio model via chat completions."""

import base64
import os
from pathlib import Path

from openai import AzureOpenAI
from .base import BaseTTSProvider


class AzureTTSProvider(BaseTTSProvider):

    def __init__(self, voice: str = "nova"):
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_TTS_ENDPOINT"),
            api_key=os.getenv("AZURE_TTS_API_KEY"),
            api_version="2025-04-01-preview",
        )
        self.model = os.getenv("AZURE_TTS_MODEL", "gpt-audio-1.5")
        self.voice = voice

    def synthesize(self, text: str, output_path: Path) -> Path:
        # gpt-audio models generate speech via chat completions with audio modality
        response = self.client.chat.completions.create(
            model=self.model,
            modalities=["text", "audio"],
            audio={"voice": self.voice, "format": "mp3"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a charismatic YouTube creator recording a voiceover "
                        "for a viral Short. Read the script below EXACTLY as written — "
                        "do NOT add, remove, or change any words.\n\n"
                        "Delivery style:\n"
                        "- Sound like a real person talking to a friend, NOT a narrator.\n"
                        "- Use natural rhythm: speed up on exciting parts, slow down "
                        "for emphasis.\n"
                        "- Add subtle energy and enthusiasm — like you genuinely find "
                        "this fascinating.\n"
                        "- Use natural pauses between sentences (brief breath pauses).\n"
                        "- Vary your pitch — go higher for excitement, lower for "
                        "dramatic emphasis.\n"
                        "- The hook (first line) should grab attention immediately "
                        "with urgency.\n"
                        "- The call-to-action at the end should feel conversational, "
                        "not like a sales pitch."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )

        # Extract audio from response
        audio_data = response.choices[0].message.audio
        audio_bytes = base64.b64decode(audio_data.data)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        return output_path
