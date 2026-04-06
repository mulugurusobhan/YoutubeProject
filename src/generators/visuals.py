"""Visual generation — creates background images for each script scene."""

import random
from pathlib import Path

from ..models import ScriptResult, VisualResult
from ..providers.image import BaseImageProvider
from ..config import get_run_dir

MAX_RETRIES = 5

_RETRY_TWEAKS = [
    "Use a slightly different camera angle and warmer color palette.",
    "Try a wider shot with cooler tones and softer lighting.",
    "Use a dramatic close-up perspective with high contrast.",
    "Switch to a minimalist composition with bokeh background.",
    "Use an aerial or birds-eye-view angle with vivid saturated colors.",
]


class VisualGenerator:

    def __init__(self, image_provider: BaseImageProvider, config: dict):
        self.image_provider = image_provider
        self.config = config
        self.style = config["visuals"]["style"]

    @staticmethod
    def _fallback_prompt(style: str) -> str:
        return (
            f"A visually striking vertical background, style: {style}. "
            f"Abstract glowing neon shapes on a dark gradient. "
            f"No text, no words, no letters. Cinematic lighting, shallow depth of field."
        )

    def _generate_with_retries(self, prompt: str, img_path: Path, scene_idx: int) -> None:
        """Try generating an image up to MAX_RETRIES times with prompt variations."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                if attempt == 0:
                    current_prompt = prompt
                else:
                    tweak = _RETRY_TWEAKS[attempt - 1] if attempt - 1 < len(_RETRY_TWEAKS) else random.choice(_RETRY_TWEAKS)
                    current_prompt = f"{prompt} {tweak}"
                    print(f"[Visuals]   Retry {attempt}/{MAX_RETRIES - 1} for scene {scene_idx + 1}...")

                self.image_provider.generate(current_prompt, img_path)
                return  # success
            except Exception as e:
                last_error = e
                print(f"[Visuals]   Attempt {attempt + 1} failed: {e}")

        # All retries exhausted — use a safe fallback
        print(f"[Visuals]   All {MAX_RETRIES} attempts failed for scene {scene_idx + 1}, using fallback")
        self.image_provider.generate(self._fallback_prompt(self.style), img_path)

    def generate(self, script: ScriptResult, run_id: str) -> VisualResult:
        visuals_dir = get_run_dir(self.config, run_id) / "visuals"
        visuals_dir.mkdir(parents=True, exist_ok=True)

        # Use image prompts from the script generator (step 1)
        has_prompts = len(script.image_prompts) == len(script.scenes)
        if not has_prompts:
            print("[Visuals] WARNING: No image prompts from script, using fallback style")

        image_paths: list[Path] = []
        for i, scene in enumerate(script.scenes):
            if has_prompts:
                prompt = script.image_prompts[i]
            else:
                prompt = self._fallback_prompt(self.style)

            print(f"[Visuals] Generating image {i + 1}/{len(script.scenes)}: {scene[:50]}...")
            img_path = visuals_dir / f"scene_{i:03d}.png"
            self._generate_with_retries(prompt, img_path, i)
            image_paths.append(img_path)

        print(f"[Visuals] {len(image_paths)} images saved")
        return VisualResult(image_paths=image_paths)
