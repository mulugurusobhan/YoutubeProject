"""Azure AI Foundry — Black Forest Labs FLUX image generation provider."""

import os
import time
from pathlib import Path

import requests
from .base import BaseImageProvider

MAX_POLL_SECONDS = 120
POLL_INTERVAL = 1.5


class AzureFluxImageProvider(BaseImageProvider):

    def __init__(self, size: str = "1024x1792", model: str = "flux-2-pro"):
        self.endpoint = os.getenv("AZURE_FLUX_ENDPOINT")
        self.api_key = os.getenv("AZURE_FLUX_API_KEY")
        if not self.endpoint or not self.api_key:
            raise ValueError(
                "AZURE_FLUX_ENDPOINT and AZURE_FLUX_API_KEY must be set in .env"
            )
        self.size = size
        self.model = model

    def generate(self, prompt: str, output_path: Path) -> Path:
        w, h = self.size.split("x")

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "prompt": prompt,
            "width": int(w),
            "height": int(h),
        }

        # Step 1: Submit generation request
        resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            print(f"[FLUX] Error {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
        data = resp.json()

        # The response may be synchronous (image inline) or async (id + polling_url)
        img_bytes = self._resolve_image(data, headers)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_bytes)

        return output_path

    def _resolve_image(self, data: dict, headers: dict) -> bytes:
        """Handle both sync and async response formats."""

        # Synchronous: image data returned directly
        if "data" in data:
            return self._extract_image_bytes(data["data"][0])

        if "result" in data and data.get("status") == "Ready":
            return self._download(data["result"]["sample"])

        # Async: poll for result
        polling_url = data.get("polling_url")
        request_id = data.get("id")

        if not polling_url and not request_id:
            raise RuntimeError(f"Unexpected response format: {list(data.keys())}")

        # If no explicit polling URL, build one from the base endpoint
        if not polling_url:
            base = self.endpoint.split("/providers/")[0]
            polling_url = f"{base}/providers/blackforestlabs/v1/results/{request_id}?api-version=preview"

        return self._poll(polling_url, headers)

    def _poll(self, polling_url: str, headers: dict) -> bytes:
        """Poll until the image is ready."""
        elapsed = 0.0
        while elapsed < MAX_POLL_SECONDS:
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            resp = requests.get(polling_url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status", "")
            if status == "Ready":
                sample = data.get("result", {}).get("sample")
                if sample:
                    return self._download(sample)
                return self._extract_image_bytes(data)
            if status in ("Error", "Failed"):
                raise RuntimeError(f"FLUX generation failed: {data}")

        raise TimeoutError(f"FLUX generation timed out after {MAX_POLL_SECONDS}s")

    @staticmethod
    def _download(url: str) -> bytes:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def _extract_image_bytes(image_data: dict) -> bytes:
        if "url" in image_data:
            resp = requests.get(image_data["url"], timeout=60)
            resp.raise_for_status()
            return resp.content
        if "b64_json" in image_data:
            import base64
            return base64.b64decode(image_data["b64_json"])
        raise RuntimeError(f"Cannot extract image from: {list(image_data.keys())}")
