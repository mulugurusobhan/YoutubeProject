"""Email notifications for pipeline events."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


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
                     completed_steps: list[str], elapsed_seconds: float) -> None:
        subject = "❌ YouTube Upload Failed"
        steps_html = ""
        for step in completed_steps:
            steps_html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;">✅ {step}</td></tr>'
        steps_html += f'<tr style="border-bottom: 1px solid #eee; background: #fef2f2;"><td style="padding: 8px; color: #dc2626;">❌ {failed_step}</td></tr>'

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

            <h3 style="color: #dc2626;">Error:</h3>
            <pre style="background: #fef2f2; padding: 12px; border-radius: 6px; color: #991b1b; overflow-x: auto; font-size: 13px;">{error_message[:500]}</pre>

            <p style="color: #555;">Description: {description}</p>
        </div>
        """
        self._send(subject, html)
