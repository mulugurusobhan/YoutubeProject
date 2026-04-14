"""YouTube video downloader — OAuth + YouTube Data API with yt-dlp fallback."""

import re
import uuid
import subprocess
from datetime import datetime
from pathlib import Path

import requests
import yt_dlp
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from ..config import PROJECT_ROOT

COOKIES_PATH = PROJECT_ROOT / "config" / "youtube_cookies.txt"
TOKEN_PATH = PROJECT_ROOT / "config" / "youtube_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
]
WARP_PROXY = "socks5://127.0.0.1:40000"


def has_cookies() -> bool:
    """Check whether a YouTube cookies file exists."""
    return COOKIES_PATH.exists() and COOKIES_PATH.stat().st_size > 0


def _warp_available() -> bool:
    """Check if Cloudflare WARP proxy is available."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", 40000))
        sock.close()
        return result == 0
    except Exception:
        return False


def has_oauth() -> bool:
    """Check if valid OAuth credentials exist."""
    if not TOKEN_PATH.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        return creds is not None and (creds.valid or creds.refresh_token is not None)
    except Exception:
        return False


def _load_credentials() -> Credentials:
    """Load and auto-refresh OAuth credentials."""
    if not TOKEN_PATH.exists():
        raise FileNotFoundError("No OAuth token. Please login with Google first.")
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        else:
            raise ValueError("OAuth token expired. Please re-login with Google.")
    return creds


def _extract_video_id(url: str) -> str:
    """Extract the 11-character video ID from a YouTube URL."""
    for pattern in [
        r"(?:v=|/v/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def _fetch_metadata_api(video_id: str, creds: Credentials) -> dict:
    """Fetch video metadata using the YouTube Data API v3 (OAuth-authenticated)."""
    youtube = build("youtube", "v3", credentials=creds)
    resp = youtube.videos().list(
        part="snippet,contentDetails",
        id=video_id,
    ).execute()

    items = resp.get("items", [])
    if not items:
        raise ValueError(f"Video {video_id} not found via YouTube Data API")

    snippet = items[0]["snippet"]
    thumbs = snippet.get("thumbnails", {})
    # Pick best thumbnail: maxres > high > medium > default
    thumb_url = None
    for quality in ("maxres", "high", "medium", "default"):
        if quality in thumbs:
            thumb_url = thumbs[quality]["url"]
            break

    return {
        "title": snippet.get("title", "YouTube Video")[:100],
        "description": snippet.get("description", ""),
        "thumbnail_url": thumb_url,
        "channel": snippet.get("channelTitle", ""),
    }


def _download_file(url: str, dest: Path, label: str = ""):
    """Download a file from URL with progress."""
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = int(downloaded / total * 100)
                print(f"\r[YouTube DL] {label}{pct}%", end="", flush=True)
    if total:
        print()


def _oauth_download(url: str, output_dir: Path) -> dict:
    """Download video using OAuth for metadata + yt-dlp for the stream."""
    creds = _load_credentials()
    video_id = _extract_video_id(url)

    # 1. Get metadata via YouTube Data API (always works with OAuth)
    print(f"[YouTube OAuth] Fetching metadata for {video_id} via Data API...")
    meta = _fetch_metadata_api(video_id, creds)
    print(f"[YouTube OAuth] Title: {meta['title']}")

    # 2. Download thumbnail
    thumbnail_path = None
    if meta["thumbnail_url"]:
        try:
            thumbnail_path = output_dir / "thumbnail.jpg"
            _download_file(meta["thumbnail_url"], thumbnail_path, "thumb: ")
        except Exception as e:
            print(f"[YouTube OAuth] Thumbnail download failed: {e}")
            thumbnail_path = None

    # 3. Download video via yt-dlp
    output_template = str(output_dir / "video.%(ext)s")
    ydl_opts = {
        "outtmpl": output_template,
        "format": "best",
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "js_runtimes": "node",
    }

    if _warp_available():
        ydl_opts["proxy"] = WARP_PROXY
        print("[YouTube OAuth] Using WARP proxy")

    if COOKIES_PATH.exists():
        ydl_opts["cookiefile"] = str(COOKIES_PATH)

    print("[YouTube OAuth] Downloading video via yt-dlp...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # Find downloaded video file
    video_path = None
    for f in output_dir.iterdir():
        if f.suffix == ".mp4":
            video_path = f
            break

    if not video_path:
        raise FileNotFoundError(f"Downloaded video not found in {output_dir}")

    duration = info.get("duration", 0)
    print(f"[YouTube OAuth] Downloaded: {video_path.name} ({duration}s)")

    return {
        "video_path": video_path,
        "title": meta["title"],
        "description": meta["description"],
        "thumbnail_path": thumbnail_path,
        "duration": duration,
    }


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

    Tries OAuth + Innertube API first, falls back to yt-dlp.

    Returns:
        dict with keys: run_id, video_path, title, description,
                        thumbnail_path, duration, is_short
    """
    url = _sanitize_url(url)
    is_short = "/shorts/" in url

    run_id = "yt_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    output_dir = PROJECT_ROOT / "output" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Try OAuth-based download first ---
    if has_oauth():
        try:
            print("[YouTube DL] Trying OAuth-authenticated download...")
            result = _oauth_download(url, output_dir)
            return {
                "run_id": run_id,
                "video_path": result["video_path"],
                "title": result["title"],
                "description": result["description"],
                "thumbnail_path": result["thumbnail_path"],
                "duration": result["duration"],
                "is_short": is_short,
            }
        except Exception as e:
            print(f"[YouTube DL] OAuth download failed: {e}")
            print("[YouTube DL] Falling back to yt-dlp...")

    # --- Fallback: yt-dlp ---
    output_template = str(output_dir / "video.%(ext)s")
    ydl_opts = {
        "outtmpl": output_template,
        "format": "best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "quiet": False,
        "no_warnings": False,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "js_runtimes": "node",
    }

    if _warp_available():
        ydl_opts["proxy"] = WARP_PROXY
        print("[YouTube DL] Using WARP proxy")

    if COOKIES_PATH.exists():
        ydl_opts["cookiefile"] = str(COOKIES_PATH)
        print("[YouTube DL] Using cookies for authentication")

    print(f"[YouTube DL] Downloading via yt-dlp: {url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_path = None
    thumbnail_path = None
    for f in output_dir.iterdir():
        if f.suffix == ".mp4":
            video_path = f
        elif f.suffix in (".jpg", ".jpeg", ".png", ".webp"):
            thumbnail_path = f

    if not video_path:
        raise FileNotFoundError(f"Downloaded video not found in {output_dir}")

    return {
        "run_id": run_id,
        "video_path": video_path,
        "title": info.get("title", "")[:100] or "YouTube Video",
        "description": info.get("description", ""),
        "thumbnail_path": thumbnail_path,
        "duration": info.get("duration", 0),
        "is_short": is_short,
    }
