"""YouTube uploader — publishes a video via the Data API v3."""

import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..models import Metadata
from ..config import PROJECT_ROOT

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
TOKEN_PATH = PROJECT_ROOT / "config" / "youtube_token.json"


class YouTubeUploader:

    def __init__(self, config: dict):
        self.yt_cfg = config["youtube"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, video_path: Path, metadata: Metadata,
               thumbnail_path: Path | None = None) -> str:
        youtube = self._get_service()

        # Build description with hashtags appended
        hashtags = " ".join(f"#{t}" for t in metadata.tags[:30])
        full_description = f"{metadata.description}\n\n{hashtags}"

        body = {
            "snippet": {
                "title": metadata.title,
                "description": full_description,
                "tags": metadata.tags,
                "categoryId": self.yt_cfg["category_id"],
            },
            "status": {
                "privacyStatus": self.yt_cfg["privacy_status"],
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,
        )

        print(f"[Upload] Uploading '{metadata.title}' to YouTube...")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[Upload] {int(status.progress() * 100)}% uploaded")

        video_id = response["id"]

        # Set thumbnail if provided
        if thumbnail_path and thumbnail_path.exists():
            try:
                print(f"[Upload] Setting thumbnail: {thumbnail_path.name}")
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/png"),
                ).execute()
                print("[Upload] Thumbnail set successfully")
            except Exception as e:
                print(f"[Upload] WARNING: Thumbnail upload failed: {e}")

        print(f"[Upload] Done! https://youtube.com/shorts/{video_id}")
        return video_id

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @staticmethod
    def _get_service():
        creds = None
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                secrets_file = os.getenv(
                    "YOUTUBE_CLIENT_SECRETS_FILE",
                    str(PROJECT_ROOT / "config" / "client_secret.json"),
                )
                flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
                creds = flow.run_local_server(
                    port=8080, open_browser=False, bind_addr="0.0.0.0",
                )

            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)
