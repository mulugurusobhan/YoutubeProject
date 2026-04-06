"""Video assembly — composites visuals, audio, and subtitles into a Short."""

import random
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
)

from ..models import SubtitleResult, VideoResult, WordTimestamp
from ..config import get_run_dir, PROJECT_ROOT


class VideoEditor:

    def __init__(self, config: dict):
        self.config = config
        self.vid = config["video"]
        self.sub = config["subtitles"]
        self.width = self.vid["width"]
        self.height = self.vid["height"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assemble(
        self,
        audio_path: Path,
        image_paths: list[Path],
        subtitles: SubtitleResult,
        run_id: str,
    ) -> VideoResult:
        output_path = get_run_dir(self.config, run_id) / "short.mp4"

        voiceover = AudioFileClip(str(audio_path))
        duration = voiceover.duration

        # Layers
        base = self._build_scene_track(image_paths, duration)
        captions = self._build_caption_track(subtitles.words)
        final_video = CompositeVideoClip(
            [base] + captions,
            size=(self.width, self.height),
        )

        # Audio mix
        final_audio = self._mix_audio(voiceover, duration)
        final_video = final_video.with_audio(final_audio).with_duration(duration)

        # Render
        print(f"[Video] Rendering {duration:.1f}s video → {output_path.name}")
        final_video.write_videofile(
            str(output_path),
            fps=self.vid["fps"],
            codec="libx264",
            audio_codec="aac",
            logger="bar",
        )

        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"[Video] Done! {size_mb:.1f} MB")
        return VideoResult(
            video_path=output_path,
            duration_seconds=duration,
            size_mb=size_mb,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_scene_track(self, image_paths: list[Path], duration: float):
        n = len(image_paths)
        scene_dur = duration / n
        clips = [
            ImageClip(str(p))
            .resized((self.width, self.height))
            .with_duration(scene_dur)
            for p in image_paths
        ]
        return concatenate_videoclips(clips, method="compose")

    def _build_caption_track(self, words: list[WordTimestamp]) -> list[TextClip]:
        group_size = 5
        clips: list[TextClip] = []

        for i in range(0, len(words), group_size):
            group = words[i : i + group_size]
            text = " ".join(w.text for w in group)
            start = group[0].start
            end = group[-1].end
            dur = max(end - start, 0.3)

            clip = (
                TextClip(
                    text=text,
                    font_size=self.sub["font_size"],
                    color=self.sub["color"],
                    stroke_color=self.sub["stroke_color"],
                    stroke_width=self.sub["stroke_width"],
                    method="caption",
                    size=(self.width - 100, None),
                    text_align="center",
                )
                .with_duration(dur)
                .with_start(start)
                .with_position(("center", self.height * 0.70))
            )
            clips.append(clip)

        return clips

    def _mix_audio(self, voiceover: AudioFileClip, duration: float) -> CompositeAudioClip:
        tracks = [voiceover]
        bg_path = self._pick_bg_music()
        if bg_path:
            bg = AudioFileClip(str(bg_path))
            bg = bg.subclipped(0, min(duration, bg.duration))
            bg = bg.with_volume_scaled(self.vid["background_music_volume"])
            tracks.append(bg)
        return CompositeAudioClip(tracks)

    def _pick_bg_music(self) -> Path | None:
        music_dir = PROJECT_ROOT / self.vid["background_music_dir"]
        if not music_dir.exists():
            return None
        tracks = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
        return random.choice(tracks) if tracks else None
