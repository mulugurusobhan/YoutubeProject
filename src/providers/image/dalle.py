"""DALL-E image generation provider."""

from pathlib import Path
import requests
from openai import OpenAI
from .base import BaseImageProvider


class DalleImageProvider(BaseImageProvider):

    def __init__(self, model: str = "dall-e-3", size: str = "1024x1792", quality: str = "standard"):
        self.client = OpenAI()
        self.model = model
        self.size = size
        self.quality = quality

    def generate(self, prompt: str, output_path: Path) -> Path:
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            n=1,
            size=self.size,
            quality=self.quality,
        )

        url = response.data[0].url
        img_resp = requests.get(url, timeout=60)
        img_resp.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_resp.content)

        return output_path
