"""Subtitle generation — word-level timestamps estimated from script + audio duration."""

from pathlib import Path

from moviepy import AudioFileClip

from ..models import WordTimestamp, SubtitleResult
from ..config import get_run_dir


class SubtitleGenerator:

    def __init__(self, config: dict):
        self.config = config

    def generate(self, audio_path: Path, run_id: str, script_text: str = "") -> SubtitleResult:
        """Generate word-level subtitles.

        Uses the known script text + audio duration to evenly distribute
        word timestamps (no transcription API needed).
        """
        print("[Subtitles] Estimating word timestamps from script + audio duration...")

        audio = AudioFileClip(str(audio_path))
        duration = audio.duration
        audio.close()

        # Split script into words
        raw_words = script_text.split()
        if not raw_words:
            return SubtitleResult(words=[], srt_path=None)

        # Distribute words evenly across the audio duration
        time_per_word = duration / len(raw_words)
        words = []
        for i, w in enumerate(raw_words):
            start = i * time_per_word
            end = start + time_per_word
            words.append(WordTimestamp(text=w, start=start, end=end))

        # Write SRT grouped by ~5 words per line
        srt_path = get_run_dir(self.config, run_id) / "subtitles.srt"
        self._write_srt(words, srt_path)

        print(f"[Subtitles] {len(words)} words, {duration:.1f}s audio, SRT → {srt_path.name}")
        return SubtitleResult(words=words, srt_path=srt_path)

    @staticmethod
    def _write_srt(words: list[WordTimestamp], path: Path) -> None:
        group_size = 5
        with open(path, "w", encoding="utf-8") as f:
            idx = 1
            for i in range(0, len(words), group_size):
                group = words[i : i + group_size]
                text = " ".join(w.text for w in group)
                start = SubtitleGenerator._fmt(group[0].start)
                end = SubtitleGenerator._fmt(group[-1].end)
                f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")
                idx += 1

    @staticmethod
    def _fmt(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
