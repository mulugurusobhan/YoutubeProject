"""Script generation — produces a spoken script from a creative brief."""

import json
import re

from ..models import ScriptResult
from ..providers.llm import BaseLLMProvider

SYSTEM_PROMPT = """\
You are a viral YouTube Shorts scriptwriter AND visual art director.
Write a short-form video script that is {style}.

You must output valid JSON with this exact structure:
{{
  "scenes": [
    {{
      "line": "The spoken line for this scene beat.",
      "image": "A detailed image-generation prompt for this scene's background."
    }}
  ]
}}

Script rules:
- The full spoken script (all "line" values combined) MUST be speakable in \
under {max_seconds} seconds (~{max_words} words total).
- Start with a powerful hook in the first line (pattern interrupt, bold claim, \
or question).
- Keep sentences short and punchy.
- End with a clear call-to-action (like, follow, comment).
- Each scene/beat is one object in the array.

Image prompt rules:
- Each "image" value is a self-contained prompt for an AI image generator.
- Describe ONLY visuals: colors, lighting, objects, environments, mood, \
camera angle, characters.
- NEVER include any text, words, letters, numbers, code, or UI elements in \
the image prompt.
- You CAN reference recognizable characters, scenes, or aesthetics from \
TV shows, movies, anime, and pop culture to make the visuals engaging and \
relatable.
- Use cinematic language: depth of field, dramatic lighting, close-up, \
wide shot, etc.
- Images are vertical (9:16 portrait) for a phone screen.
- Make each image visually distinct from the previous one — vary settings, \
colors, and angles.
- Match the mood and energy of the spoken line.

Output ONLY the JSON. No markdown fences, no explanation."""

USER_PROMPT = """\
Create a YouTube Shorts script + image prompts based on this brief:

Keywords: {keywords}
Description: {description}"""


def _extract_json(text: str) -> str:
    """Strip markdown fences or surrounding text to get raw JSON."""
    # Try to find a JSON block inside ```json ... ``` or ``` ... ```
    m = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        return m.group(1)
    # Otherwise find the first { ... } block
    m = re.search(r'(\{.*\})', text, re.DOTALL)
    if m:
        return m.group(1)
    return text


class ScriptGenerator:

    def __init__(self, llm: BaseLLMProvider, config: dict):
        self.llm = llm
        self.cfg = config["script"]
        self.max_seconds = config["content"]["max_duration_seconds"]

    def generate(self, brief: dict) -> ScriptResult:
        """Generate a script from a brief dict with 'keywords' and 'description'."""
        max_words = int(self.max_seconds * 2.5)

        system = SYSTEM_PROMPT.format(
            style=self.cfg["style"],
            max_seconds=self.max_seconds,
            max_words=max_words,
        )

        user = USER_PROMPT.format(
            keywords=", ".join(brief["keywords"]),
            description=brief["description"],
        )

        raw = self.llm.complete(
            system_prompt=system,
            user_prompt=user,
        )

        # Parse structured JSON output
        try:
            data = json.loads(_extract_json(raw))
            scenes_data = data["scenes"]
            lines = [s["line"] for s in scenes_data]
            image_prompts = [s["image"] for s in scenes_data]
            text = "\n".join(lines)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[Script] WARNING: Failed to parse JSON, falling back to plain text: {e}")
            text = raw
            lines = []
            image_prompts = []

        result = ScriptResult(text=text, scenes=lines, image_prompts=image_prompts)
        print(f"[Script] Generated {result.word_count} words, {len(result.scenes)} scenes")
        if image_prompts:
            print(f"[Script] Image prompts: {len(image_prompts)} scene directions included")
        return result
