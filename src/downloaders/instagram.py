"""Instagram reel downloader — uses saved cookies.txt for yt-dlp."""

import re
import uuid
from datetime import datetime
from pathlib import Path

import yt_dlp

from ..config import PROJECT_ROOT

COOKIES_PATH = PROJECT_ROOT / "config" / "instagram_cookies.txt"


def is_logged_in() -> bool:
    """Check whether a saved cookie file with a sessionid exists."""
    if not COOKIES_PATH.exists():
        return False
    try:
        text = COOKIES_PATH.read_text(encoding="utf-8")
        return "sessionid" in text
    except Exception:
        return False


def _sanitize_url(url: str) -> str:
    """Validate and clean an Instagram reel URL."""
    url = url.strip()
    pattern = r"https?://(www\.)?instagram\.com/(reel|reels|p)/[\w-]+"
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid Instagram reel URL: {url}")
    return match.group(0)


def download_reel(url: str) -> dict:
    """Download an Instagram reel using saved cookies.

    Returns:
        dict with keys: run_id, video_path, title, description, thumbnail_path, duration
    """
    if not is_logged_in():
        raise RuntimeError(
            "Not connected to Instagram. Place a valid cookies.txt in config/instagram_cookies.txt."
        )

    url = _sanitize_url(url)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    output_dir = PROJECT_ROOT / "output" / f"reel_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "reel.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "quiet": False,
        "no_warnings": False,
        "cookiefile": str(COOKIES_PATH),
    }

    print(f"[Instagram] Downloading reel: {url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # Find the downloaded video file
    video_path = None
    thumbnail_path = None
    for f in output_dir.iterdir():
        if f.suffix == ".mp4":
            video_path = f
        elif f.suffix in (".jpg", ".jpeg", ".png", ".webp"):
            thumbnail_path = f

    if not video_path:
        raise FileNotFoundError(f"Downloaded video not found in {output_dir}")

    title = info.get("title") or info.get("description", "")[:100] or "Instagram Reel"
    description = info.get("description", "")
    duration = info.get("duration", 0)

    print(f"[Instagram] Downloaded: {video_path.name} ({duration}s)")

    return {
        "run_id": run_id,
        "video_path": video_path,
        "title": title,
        "description": description,
        "thumbnail_path": thumbnail_path,
        "duration": duration,
    }
