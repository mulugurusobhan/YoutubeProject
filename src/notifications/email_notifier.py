"""Email notifications for pipeline events."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def _describe_error_with_llm(error_traceback: str, failed_step: str, job_type: str = "pipeline") -> str:
    """Use LLM to turn a raw traceback into a user-friendly explanation."""
    try:
        from src.config import load_config
        from src.providers.llm import AzureLLMProvider
        config = load_config()
        model = config.get("script", {}).get("model", "gpt-4o")
        llm = AzureLLMProvider(model=model, temperature=0.3)
        system = (
            "You are an assistant that explains technical errors to non-technical users. "
            "Given a Python traceback from a video generation pipeline, write a short, "
            "clear explanation (2-4 sentences) of what went wrong and a suggestion to fix it. "
            "Do NOT include code, file paths, or class names. Speak in plain English."
        )
        user = (
            f"Job type: {job_type}\n"
            f"Failed at step: {failed_step}\n"
            f"Error:\n{error_traceback[:1500]}"
        )
        return llm.complete(system, user)
    except Exception:
        return ""


class EmailNotifier:

    def __init__(self, cc: str | None = None):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.recipient = os.getenv("NOTIFICATION_EMAIL", "domcobb1409200@gmail.com")
        self.cc = cc

    def _send(self, subject: str, html_body: str) -> None:
        if not self.sender or not self.password:
            print(f"[Email] Skipped — SMTP_USER / SMTP_PASSWORD not configured")
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = self.sender
        msg["To"] = self.recipient
        if self.cc:
            msg["Cc"] = self.cc
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        recipients = [self.recipient]
        if self.cc:
            recipients.append(self.cc)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender, self.password)
            server.sendmail(self.sender, recipients, msg.as_string())

        print(f"[Email] Sent: {subject}" + (f" (CC: {self.cc})" if self.cc else ""))

    def send_start(self, keywords: list[str], description: str, run_id: str) -> None:
        subject = "YouTube Upload Started"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a73e8;">🚀 YouTube Shorts Pipeline Started</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Run ID</td>
                    <td style="padding: 8px;">{run_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Keywords</td>
                    <td style="padding: 8px;">{', '.join(keywords)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Description</td>
                    <td style="padding: 8px;">{description}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Started At</td>
                    <td style="padding: 8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <h3 style="color: #333;">Pipeline Steps:</h3>
            <ol style="color: #555; line-height: 1.8;">
                <li>Script + Image Prompt Generation</li>
                <li>Voiceover Generation</li>
                <li>Background Visual Generation</li>
                <li>Subtitle Estimation</li>
                <li>Video Assembly</li>
                <li>Metadata Generation</li>
                <li>YouTube Upload</li>
            </ol>
            <p style="color: #888; font-size: 12px;">You will receive another email when the pipeline completes or fails.</p>
        </div>
        """
        self._send(subject, html)

    def send_success(self, run_id: str, keywords: list[str], description: str,
                     script_preview: str, word_count: int, scene_count: int,
                     audio_size_kb: int, image_count: int, video_duration: float,
                     video_size_mb: float, title: str, video_id: str | None,
                     elapsed_seconds: float) -> None:
        subject = "✅ YouTube Upload Completed Successfully"
        video_link = f"https://youtube.com/shorts/{video_id}" if video_id else "Upload skipped"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d9488;">✅ Pipeline Completed Successfully</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Run ID</td>
                    <td style="padding: 8px;">{run_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Keywords</td>
                    <td style="padding: 8px;">{', '.join(keywords)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Total Time</td>
                    <td style="padding: 8px;">{elapsed_seconds:.0f} seconds</td>
                </tr>
            </table>

            <h3 style="color: #333;">Step Results:</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 1. Script</td>
                    <td style="padding: 8px;">{word_count} words, {scene_count} scenes</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 2. Voiceover</td>
                    <td style="padding: 8px;">{audio_size_kb} KB audio</td>
                </tr>
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 3. Visuals</td>
                    <td style="padding: 8px;">{image_count} images generated</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 4. Subtitles</td>
                    <td style="padding: 8px;">{word_count} word timestamps</td>
                </tr>
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 5. Video</td>
                    <td style="padding: 8px;">{video_duration:.1f}s, {video_size_mb:.1f} MB</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 6. Metadata</td>
                    <td style="padding: 8px;">{title}</td>
                </tr>
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 7. Upload</td>
                    <td style="padding: 8px;"><a href="{video_link}">{video_link}</a></td>
                </tr>
            </table>

            <h3 style="color: #333;">Script Preview:</h3>
            <p style="color: #555; background: #f8f9fa; padding: 12px; border-radius: 6px; font-style: italic;">
                "{script_preview[:200]}..."
            </p>
        </div>
        """
        self._send(subject, html)

    def send_failure(self, run_id: str, keywords: list[str], description: str,
                     failed_step: str, error_message: str,
                     completed_steps: list[str], elapsed_seconds: float,
                     job_type: str = "pipeline") -> None:
        subject = "❌ YouTube Upload Failed"
        steps_html = ""
        for step in completed_steps:
            steps_html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;">✅ {step}</td></tr>'
        steps_html += f'<tr style="border-bottom: 1px solid #eee; background: #fef2f2;"><td style="padding: 8px; color: #dc2626;">❌ {failed_step}</td></tr>'

        # Get a user-friendly explanation from LLM
        friendly = _describe_error_with_llm(error_message, failed_step, job_type)
        explanation_html = ""
        if friendly:
            explanation_html = f"""
            <h3 style="color: #dc2626;">What went wrong:</h3>
            <p style="background: #fef2f2; padding: 12px; border-radius: 6px; color: #991b1b; line-height: 1.6;">{friendly}</p>
            """

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc2626;">❌ Pipeline Failed</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Run ID</td>
                    <td style="padding: 8px;">{run_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Keywords</td>
                    <td style="padding: 8px;">{', '.join(keywords)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Failed At</td>
                    <td style="padding: 8px; color: #dc2626; font-weight: bold;">{failed_step}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Elapsed</td>
                    <td style="padding: 8px;">{elapsed_seconds:.0f} seconds</td>
                </tr>
            </table>

            <h3 style="color: #333;">Step Progress:</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                {steps_html}
            </table>

            {explanation_html}

            <details style="margin-top: 12px;">
                <summary style="cursor: pointer; color: #888; font-size: 13px;">Show technical details</summary>
                <pre style="background: #f3f4f6; padding: 12px; border-radius: 6px; color: #555; overflow-x: auto; font-size: 12px; margin-top: 8px;">{error_message[:800]}</pre>
            </details>

            <p style="color: #555; margin-top: 16px;">Description: {description}</p>
        </div>
        """
        self._send(subject, html)

    def send_repost_start(self, reel_url: str, run_id: str) -> None:
        subject = "📸 Instagram Repost Started"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a73e8;">📸 Instagram Repost Started</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Run ID</td>
                    <td style="padding: 8px;">{run_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Reel URL</td>
                    <td style="padding: 8px;"><a href="{reel_url}">{reel_url}</a></td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Started At</td>
                    <td style="padding: 8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <h3 style="color: #333;">Steps:</h3>
            <ol style="color: #555; line-height: 1.8;">
                <li>Download Reel</li>
                <li>Generate Metadata</li>
                <li>Upload to YouTube</li>
            </ol>
            <p style="color: #888; font-size: 12px;">You will receive another email when the repost completes or fails.</p>
        </div>
        """
        self._send(subject, html)

    def send_repost_success(self, run_id: str, reel_url: str, title: str,
                            video_id: str | None, duration: float,
                            elapsed_seconds: float) -> None:
        subject = "✅ Instagram Repost Completed"
        video_link = f"https://youtube.com/shorts/{video_id}" if video_id else "Upload skipped"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d9488;">✅ Instagram Repost Completed</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Run ID</td>
                    <td style="padding: 8px;">{run_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Source</td>
                    <td style="padding: 8px;"><a href="{reel_url}">{reel_url}</a></td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Title</td>
                    <td style="padding: 8px;">{title}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Duration</td>
                    <td style="padding: 8px;">{duration:.1f}s</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Total Time</td>
                    <td style="padding: 8px;">{elapsed_seconds:.0f} seconds</td>
                </tr>
            </table>
            <h3 style="color: #333;">Steps:</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 1. Download Reel</td>
                    <td style="padding: 8px;">{duration:.1f}s video</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 2. Metadata</td>
                    <td style="padding: 8px;">{title}</td>
                </tr>
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 3. Upload</td>
                    <td style="padding: 8px;"><a href="{video_link}">{video_link}</a></td>
                </tr>
            </table>
        </div>
        """
        self._send(subject, html)

    # ------------------------------------------------------------------
    # YouTube Video Repost
    # ------------------------------------------------------------------

    def send_yt_repost_start(self, video_url: str, run_id: str) -> None:
        subject = "▶️ YouTube Repost Started"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ff0000;">▶️ YouTube Repost Started</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Run ID</td>
                    <td style="padding: 8px;">{run_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Source URL</td>
                    <td style="padding: 8px;"><a href="{video_url}">{video_url}</a></td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Started At</td>
                    <td style="padding: 8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <h3 style="color: #333;">Steps:</h3>
            <ol style="color: #555; line-height: 1.8;">
                <li>Download Video</li>
                <li>Generate Metadata</li>
                <li>Upload to YouTube</li>
            </ol>
            <p style="color: #888; font-size: 12px;">You will receive another email when the repost completes or fails.</p>
        </div>
        """
        self._send(subject, html)

    def send_yt_repost_success(self, run_id: str, source_url: str, title: str,
                               video_id: str | None, duration: float,
                               elapsed_seconds: float, is_short: bool = False) -> None:
        subject = "✅ YouTube Repost Completed"
        if is_short:
            video_link = f"https://youtube.com/shorts/{video_id}" if video_id else "Upload skipped"
        else:
            video_link = f"https://youtube.com/watch?v={video_id}" if video_id else "Upload skipped"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d9488;">✅ YouTube Repost Completed</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Run ID</td>
                    <td style="padding: 8px;">{run_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Source</td>
                    <td style="padding: 8px;"><a href="{source_url}">{source_url}</a></td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Title</td>
                    <td style="padding: 8px;">{title}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Duration</td>
                    <td style="padding: 8px;">{duration:.1f}s</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Total Time</td>
                    <td style="padding: 8px;">{elapsed_seconds:.0f} seconds</td>
                </tr>
            </table>
            <h3 style="color: #333;">Steps:</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 1. Download Video</td>
                    <td style="padding: 8px;">{duration:.1f}s video</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 2. Metadata</td>
                    <td style="padding: 8px;">{title}</td>
                </tr>
                <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">✅ 3. Upload</td>
                    <td style="padding: 8px;"><a href="{video_link}">{video_link}</a></td>
                </tr>
            </table>
        </div>
        """
        self._send(subject, html)
