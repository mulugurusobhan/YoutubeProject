"""YouTube video downloader — downloads full videos or Shorts via yt-dlp."""

import re
import uuid
from datetime import datetime
from pathlib import Path

import yt_dlp

from ..config import PROJECT_ROOT


def _sanitize_url(url: str) -> str:
    """Validate and clean a YouTube video URL."""
    url = url.strip()
    pattern = (
        r"https?://(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w-]+"
    )
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid YouTube URL: {url}")
    return match.group(0)


def download_youtube(url: str) -> dict:
    """Download a YouTube video or Short.

    Returns:
        dict with keys: run_id, video_path, title, description,
                        thumbnail_path, duration, is_short
    """
    url = _sanitize_url(url)
    is_short = "/shorts/" in url

    run_id = "yt_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    output_dir = PROJECT_ROOT / "output" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "video.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "quiet": False,
        "no_warnings": False,
    }

    print(f"[YouTube DL] Downloading: {url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # Find downloaded files
    video_path = None
    thumbnail_path = None
    for f in output_dir.iterdir():
        if f.suffix == ".mp4":
            video_path = f
        elif f.suffix in (".jpg", ".jpeg", ".png", ".webp"):
            thumbnail_path = f

    if not video_path:
        raise FileNotFoundError(f"Downloaded video not found in {output_dir}")

    title = info.get("title", "")[:100] or "YouTube Video"
    description = info.get("description", "")
    duration = info.get("duration", 0)

    print(f"[YouTube DL] Downloaded: {video_path.name} ({duration}s)")

    return {
        "run_id": run_id,
        "video_path": video_path,
        "title": title,
        "description": description,
        "thumbnail_path": thumbnail_path,
        "duration": duration,
        "is_short": is_short,
    }
