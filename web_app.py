"""Flask web app for YouTube Shorts generation pipeline."""

import time
import traceback
import threading
from flask import Flask, render_template, request, jsonify

from src.config import load_config
from src.pipeline import Pipeline
from src.notifications.email_notifier import EmailNotifier

app = Flask(__name__, template_folder="templates", static_folder="static")

# Track running jobs: {run_id: {status, ...}}
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    keywords_raw = data.get("keywords", "").strip()
    description = data.get("description", "").strip()
    notify_email = data.get("notify_email", "").strip() or None

    if not keywords_raw or not description:
        return jsonify({"error": "Keywords and description are required."}), 400

    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    brief = {"keywords": keywords, "description": description, "notify_email": notify_email}

    # Start pipeline in background thread
    thread = threading.Thread(target=_run_pipeline, args=(brief,), daemon=True)
    thread.start()

    return jsonify({"message": "Pipeline started!", "keywords": keywords})


@app.route("/status")
def status():
    with jobs_lock:
        job_list = sorted(jobs.values(), key=lambda j: j.get("started", 0), reverse=True)
    return jsonify(job_list)


def _run_pipeline(brief: dict):
    notify_email = brief.get("notify_email")
    notifier = EmailNotifier(cc=notify_email)
    config = load_config()
    pipeline = Pipeline(config)
    keywords = brief["keywords"]
    description = brief["description"]

    # Generate a run_id early for tracking
    import uuid
    from datetime import datetime
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]

    job = {
        "run_id": run_id,
        "keywords": keywords,
        "description": description,
        "status": "running",
        "current_step": "Starting...",
        "started": time.time(),
        "completed_steps": [],
        "error": None,
        "video_url": None,
    }
    with jobs_lock:
        jobs[run_id] = job

    # Send start email
    try:
        notifier.send_start(keywords, description, run_id)
    except Exception as e:
        print(f"[Email] Failed to send start notification: {e}")

    start_time = time.time()
    completed_steps = []
    step_names = [
        "1. Script Generation",
        "2. Voiceover Generation",
        "3. Visual Generation",
        "4. Subtitle Estimation",
        "5. Video Assembly",
        "6. Metadata Generation",
        "7. YouTube Upload",
    ]

    try:
        topic_summary = ", ".join(keywords)

        # 1. Script
        _update_job(job, "1. Generating script...")
        script = pipeline.script_gen.generate(brief)
        completed_steps.append(step_names[0])
        _update_job(job, "1. Script done", completed_steps[:])

        # 2. Voice
        _update_job(job, "2. Generating voiceover...")
        voice = pipeline.voice_gen.generate(script.text, run_id)
        completed_steps.append(step_names[1])
        _update_job(job, "2. Voiceover done", completed_steps[:])

        # 3. Visuals
        _update_job(job, "3. Generating visuals...")
        visuals = pipeline.visual_gen.generate(script, run_id)
        completed_steps.append(step_names[2])
        _update_job(job, "3. Visuals done", completed_steps[:])

        # 4. Subtitles
        _update_job(job, "4. Generating subtitles...")
        subtitles = pipeline.subtitle_gen.generate(voice.audio_path, run_id, script.text)
        completed_steps.append(step_names[3])
        _update_job(job, "4. Subtitles done", completed_steps[:])

        # 5. Video
        _update_job(job, "5. Assembling video...")
        video = pipeline.video_editor.assemble(
            voice.audio_path, visuals.image_paths, subtitles, run_id,
        )
        completed_steps.append(step_names[4])
        _update_job(job, "5. Video done", completed_steps[:])

        # 6. Metadata
        _update_job(job, "6. Generating metadata...")
        metadata = pipeline.metadata_gen.generate(script.text, topic_summary)
        completed_steps.append(step_names[5])
        _update_job(job, "6. Metadata done", completed_steps[:])

        # 7. Upload
        _update_job(job, "7. Uploading to YouTube...")
        thumbnail = visuals.image_paths[0] if visuals.image_paths else None
        video_id = pipeline.uploader.upload(video.video_path, metadata, thumbnail)
        completed_steps.append(step_names[6])

        elapsed = time.time() - start_time
        video_url = f"https://youtube.com/shorts/{video_id}" if video_id else None

        with jobs_lock:
            job["status"] = "completed"
            job["current_step"] = "Done!"
            job["completed_steps"] = completed_steps
            job["video_url"] = video_url
            job["title"] = metadata.title
            job["elapsed"] = elapsed

        # Send success email
        audio_size_kb = int(voice.audio_path.stat().st_size / 1024)
        notifier.send_success(
            run_id=run_id,
            keywords=keywords,
            description=description,
            script_preview=script.text,
            word_count=script.word_count,
            scene_count=len(script.scenes),
            audio_size_kb=audio_size_kb,
            image_count=len(visuals.image_paths),
            video_duration=video.duration_seconds,
            video_size_mb=video.size_mb,
            title=metadata.title,
            video_id=video_id,
            elapsed_seconds=elapsed,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = traceback.format_exc()
        failed_step = step_names[len(completed_steps)] if len(completed_steps) < len(step_names) else "Unknown"

        with jobs_lock:
            job["status"] = "failed"
            job["current_step"] = f"Failed at: {failed_step}"
            job["completed_steps"] = completed_steps
            job["error"] = str(e)
            job["elapsed"] = elapsed

        # Send failure email
        try:
            notifier.send_failure(
                run_id=run_id,
                keywords=keywords,
                description=description,
                failed_step=failed_step,
                error_message=error_msg,
                completed_steps=completed_steps,
                elapsed_seconds=elapsed,
            )
        except Exception as email_err:
            print(f"[Email] Failed to send failure notification: {email_err}")


def _update_job(job: dict, current_step: str, completed_steps: list | None = None):
    with jobs_lock:
        job["current_step"] = current_step
        if completed_steps is not None:
            job["completed_steps"] = completed_steps


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
