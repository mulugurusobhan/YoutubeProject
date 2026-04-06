"""Typed data models passed between pipeline stages."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WordTimestamp:
    """A single word with its start/end time in the audio."""
    text: str
    start: float
    end: float


@dataclass
class ScriptResult:
    """Output of the script generation stage."""
    text: str
    scenes: list[str] = field(default_factory=list)
    image_prompts: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.scenes:
            self.scenes = [
                line.strip()
                for line in self.text.strip().splitlines()
                if line.strip()
            ]

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass
class VoiceResult:
    """Output of the voice generation stage."""
    audio_path: Path
    duration_seconds: float = 0.0


@dataclass
class SubtitleResult:
    """Output of the subtitle generation stage."""
    words: list[WordTimestamp]
    srt_path: Path | None = None


@dataclass
class VisualResult:
    """Output of the visual generation stage."""
    image_paths: list[Path]


@dataclass
class VideoResult:
    """Output of the video assembly stage."""
    video_path: Path
    duration_seconds: float = 0.0
    size_mb: float = 0.0


@dataclass
class Metadata:
    """YouTube video metadata."""
    title: str
    description: str
    tags: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Complete output of a single pipeline run."""
    run_id: str
    topic: str
    script: ScriptResult
    voice: VoiceResult
    subtitles: SubtitleResult
    visuals: VisualResult
    video: VideoResult
    metadata: Metadata
    video_id: str | None = None
