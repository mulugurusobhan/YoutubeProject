"""Script generation — produces a spoken script from a creative brief."""

import json
import re

from ..models import ScriptResult
from ..providers.llm import BaseLLMProvider

SYSTEM_PROMPT = """\
You are an elite YouTube Shorts scriptwriter AND visual art director who \
creates viral, highly specific, binge-worthy content.

Your approach:
1. THINK deeply about the topic — what specific facts, stories, examples, \
or angles would genuinely surprise or captivate viewers?
2. AVOID generic filler like "Did you know…", "Here's a crazy fact…", \
"You won't believe…" — instead, lead with the actual substance.
3. USE concrete details: real names, real numbers, real examples. \
Specificity is what separates viral from forgettable.
4. WRITE in a {style} tone — but never sacrifice substance for style.

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
- First line MUST be a specific, concrete hook — a surprising fact, bold \
claim with evidence, or a vivid scenario. NO vague questions or clickbait \
openers.
- Every line must add NEW information or advance the story. Never repeat \
or rephrase what was already said.
- Use short, punchy sentences. One idea per scene beat.
- Include at least one unexpected twist, lesser-known detail, or \
counter-intuitive insight that makes viewers want to share.
- End with a clear call-to-action (like, follow, comment) that ties back \
to the content.
- Do NOT use placeholder phrases like "this thing" or "that stuff" — \
be explicit.

Image prompt rules:
- Each "image" MUST directly illustrate what is being said in its paired \
"line". If the line mentions a specific object, person, place, or scenario, \
the image prompt MUST depict that exact thing — not a loosely related concept.
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
- The sequence of images should feel like a visual story that flows \
naturally alongside the spoken audio.

Output ONLY the JSON. No markdown fences, no explanation."""

USER_PROMPT = """\
Create a YouTube Shorts script + image prompts based on this brief:

Keywords: {keywords}
Description: {description}

Before writing, reason step-by-step:
1. What are the most interesting, specific, non-obvious angles on this topic?
2. What real examples, data points, or stories would hook a viewer in the \
first 2 seconds?
3. What's a twist or payoff that makes the ending satisfying?

Now write the script with that depth. Be specific, not generic."""


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
