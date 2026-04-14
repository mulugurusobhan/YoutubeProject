"""Metadata generation — SEO-optimized title, description, and tags."""

from ..models import Metadata
from ..providers.llm import BaseLLMProvider

METADATA_PROMPT = """\
You are a YouTube SEO expert. Given a video script, generate optimized metadata \
for a YouTube Short.

Return EXACTLY this format (no extra text):
TITLE: <catchy title under 100 characters, include a hook or emoji>
DESCRIPTION: <2-3 sentence description with keywords, include a CTA>
TAGS: <comma-separated tags, include #Shorts>

Script:
{script}

Topic: {topic}"""

REPOST_METADATA_PROMPT = """\
You are a YouTube SEO expert. A video is being reposted to YouTube.
You are given the original video title and description. Generate optimized YouTube metadata \
that stays true to the original content.

Rules:
- The TITLE must be based on the original title — keep it recognizable but make it catchy (under 100 chars). Add an emoji or hook if appropriate.
- The DESCRIPTION should summarize the content in 2-3 sentences, include relevant keywords and a CTA.
- TAGS must include highly relevant hashtags for the content. Always include #Shorts if it is a short-form video. Include at least 8-12 tags.

Return EXACTLY this format (no extra text):
TITLE: <title>
DESCRIPTION: <description>
TAGS: <comma-separated tags>

Original Title: {original_title}
Original Description: {original_description}
Source: {source}"""


class MetadataGenerator:

    def __init__(self, llm: BaseLLMProvider, config: dict):
        self.llm = llm
        self.default_tags = config.get("youtube", {}).get("default_tags", [])

    def generate(self, script_text: str, topic: str) -> Metadata:
        raw = self.llm.complete(
            system_prompt="",
            user_prompt=METADATA_PROMPT.format(script=script_text, topic=topic),
            temperature=0.7,
        )

        metadata = self._parse(raw)
        print(f"[Metadata] Title: {metadata.title}")
        return metadata

    def generate_repost(self, original_title: str, original_description: str,
                        source: str = "video repost") -> Metadata:
        """Generate metadata for a reposted video using its original title/description."""
        raw = self.llm.complete(
            system_prompt="",
            user_prompt=REPOST_METADATA_PROMPT.format(
                original_title=original_title,
                original_description=original_description[:1000],
                source=source,
            ),
            temperature=0.7,
        )

        metadata = self._parse(raw)
        print(f"[Metadata] Repost title: {metadata.title}")
        return metadata

    def _parse(self, raw: str) -> Metadata:
        title = ""
        description = ""
        tags: list[str] = []

        for line in raw.splitlines():
            line = line.strip()
            if line.upper().startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
            elif line.upper().startswith("DESCRIPTION:"):
                description = line.split(":", 1)[1].strip()
            elif line.upper().startswith("TAGS:"):
                raw_tags = line.split(":", 1)[1].strip()
                tags = [t.strip().strip("#") for t in raw_tags.split(",") if t.strip()]

        all_tags = list(dict.fromkeys(tags + self.default_tags))
        return Metadata(title=title[:100], description=description, tags=all_tags)
