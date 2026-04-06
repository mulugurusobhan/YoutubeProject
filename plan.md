# YouTube Shorts Generation Pipeline — Plan

## Overview

A fully automated pipeline that generates YouTube Shorts end-to-end using AI: writes a script with visual directions, generates an expressive voiceover, creates cinematic background images, estimates word-level subtitles, assembles everything into a vertical video, and publishes directly to YouTube — all from a few keywords and a brief description.

---

## Architecture

```
┌──────────────┐
│   CLI Input   │  keywords + description (or interactive prompts)
└──────┬───────┘
       ▼
┌──────────────────────────────────────────────────────────────┐
│                     Pipeline Orchestrator                     │
│                       (src/pipeline.py)                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Step 1: Script Generation ──► ScriptResult (JSON)            │
│          ├─ spoken lines per scene                             │
│          └─ image generation prompts per scene                 │
│                                                               │
│  Step 2: Voiceover ──► VoiceResult (MP3)                      │
│          chat completions with audio modality                  │
│                                                               │
│  Step 3: Visual Generation ──► VisualResult (PNGs)            │
│          uses image prompts from Step 1                        │
│          5 retries per scene with prompt variations            │
│                                                               │
│  Step 4: Subtitle Estimation ──► SubtitleResult (SRT)         │
│          script text + audio duration → word timestamps        │
│                                                               │
│  Step 5: Video Assembly ──► VideoResult (MP4)                 │
│          MoviePy composites scenes + audio + captions          │
│                                                               │
│  Step 6: Metadata Generation ──► Metadata                     │
│          LLM generates title, description, hashtags            │
│                                                               │
│  Step 7: YouTube Upload ──► video_id                          │
│          OAuth 2.0 + resumable upload                          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Pipeline Stages (Detail)

### 1. Script Generation + Visual Art Direction

- **Provider:** Azure OpenAI (gpt-5.2-chat reasoning model)
- **Input:** Keywords + description brief from user
- **Output:** Structured JSON with `scenes` array, each containing:
  - `"line"` — the spoken dialogue for that beat
  - `"image"` — a detailed cinematic image-generation prompt
- **Key Rules:**
  - Script must fit under 58 seconds (~145 words)
  - Starts with a hook (pattern interrupt / bold claim / question)
  - Ends with a conversational CTA
  - Image prompts are visual-only: no text, code, or letters
  - Image prompts CAN reference TV/movie/anime characters & pop culture
  - Each image varies in setting, color palette, and camera angle
  - Falls back to plain text parsing if JSON output fails

### 2. Voiceover Generation

- **Provider:** Azure OpenAI gpt-audio-1.5 (chat completions with audio modality)
- **Input:** Full spoken script text
- **Output:** MP3 audio file
- **Voice:** Configurable (default: "nova")
- **Delivery Style:**
  - Sounds like a real person, not a narrator
  - Natural rhythm with variable pacing and pitch
  - Breath pauses between sentences
  - Energetic hook, conversational CTA

### 3. Visual Asset Generation

- **Provider:** Azure AI Foundry — Black Forest Labs FLUX.2-pro
- **Input:** Image prompts from Step 1 (one per scene)
- **Output:** Vertical PNG images (1024×1792)
- **Retry Logic:** Up to 5 attempts per scene with prompt variations:
  1. Original prompt
  2. + "Shot from a different angle, unique perspective"
  3. + "Focus on dramatic lighting and rich colors"
  4. + "Minimalist composition, clean layout, strong focal point"
  5. + "Warm color palette, cinematic lens flare, atmospheric"
- **Fallback:** Abstract neon shapes on dark gradient if all retries fail

### 4. Subtitle / Caption Generation

- **Method:** Script-based estimation (no transcription model needed)
- **Input:** Audio duration (via MoviePy AudioFileClip) + script text
- **Output:** Word-level timestamps + SRT file
- **Logic:** Words distributed evenly across audio duration, grouped 5 per subtitle line

### 5. Video Assembly

- **Tool:** MoviePy 2.x (uses imageio-ffmpeg's bundled binary)
- **Input:** Audio, scene images, subtitles, optional background music
- **Output:** 1080×1920 MP4, codec: libx264, audio: AAC
- **Features:**
  - Scene images distributed evenly across audio duration
  - Styled captions with configurable font, size, color, stroke
  - Background music mixed at configurable volume (random from assets/music/)
  - Positioned captions at 70% height for Shorts readability

### 6. Metadata Generation

- **Provider:** Same Azure LLM as Step 1
- **Input:** Script text + topic keywords
- **Output:** Metadata object with title, description, tags
- **Format:** Title (< 100 chars, with emojis), description (2-3 sentences + CTA), tags (includes #Shorts, merged with config defaults)

### 7. YouTube Upload

- **API:** YouTube Data API v3 with OAuth 2.0
- **Auth:** InstalledAppFlow on port 8080, token cached at `config/youtube_token.json`
- **Upload:** Resumable upload with 10 MB chunks, progress reporting
- **Visibility:** Configurable (public/unlisted/private)
- **Hashtags:** Appended to description automatically

---

## Tech Stack

| Component            | Technology                                       |
| -------------------- | ------------------------------------------------ |
| Language             | Python 3.11+                                     |
| Script + Metadata    | Azure OpenAI — gpt-5.2-chat (reasoning model)    |
| Voiceover            | Azure OpenAI — gpt-audio-1.5 (chat + audio)      |
| Image Generation     | Azure AI Foundry — FLUX.2-pro (Black Forest Labs) |
| Subtitles            | Script-based estimation via MoviePy audio duration |
| Video Assembly       | MoviePy 2.x + imageio-ffmpeg                      |
| Background Music     | Local royalty-free library (assets/music/)         |
| YouTube Upload       | Google YouTube Data API v3 + OAuth 2.0             |
| CLI                  | argparse + interactive fallback                    |
| Config               | YAML + dotenv                                      |

---

## Modular Provider System

All AI providers implement abstract base classes, making them swappable:

| Interface            | Implementations                                   |
| -------------------- | ------------------------------------------------- |
| `BaseLLMProvider`    | `AzureLLMProvider`, `OpenAILLMProvider`            |
| `BaseTTSProvider`    | `AzureTTSProvider`, `OpenAITTSProvider`, `ElevenLabsTTSProvider` |
| `BaseImageProvider`  | `AzureFluxImageProvider`, `DalleImageProvider`     |

Provider selection is driven by `config/config.yaml` settings.

---

## Project Structure

```
Youtube Project/
├── src/
│   ├── __init__.py
│   ├── config.py              # Config loading, paths, dotenv
│   ├── models.py              # Typed dataclasses for pipeline data
│   ├── pipeline.py            # Orchestrator — wires providers & runs stages
│   ├── main.py                # CLI entry point
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── base.py        # BaseLLMProvider (abstract)
│   │   │   ├── azure_llm.py   # Azure OpenAI (reasoning model support)
│   │   │   └── openai_llm.py  # Direct OpenAI
│   │   ├── tts/
│   │   │   ├── base.py        # BaseTTSProvider (abstract)
│   │   │   ├── azure_tts.py   # gpt-audio-1.5 via chat completions
│   │   │   ├── openai_tts.py  # OpenAI TTS API
│   │   │   └── elevenlabs.py  # ElevenLabs
│   │   └── image/
│   │       ├── base.py        # BaseImageProvider (abstract)
│   │       ├── azure_flux.py  # FLUX.2-pro via Azure AI Foundry
│   │       └── dalle.py       # DALL-E 3
│   ├── generators/
│   │   ├── script.py          # LLM → script JSON + image prompts
│   │   ├── voice.py           # TTS → MP3 voiceover
│   │   ├── visuals.py         # Image gen with 5-retry logic
│   │   ├── subtitles.py       # Duration-based word timestamps → SRT
│   │   └── metadata.py        # LLM → title, description, tags
│   ├── editors/
│   │   └── video.py           # MoviePy video composition
│   └── uploaders/
│       └── youtube.py         # YouTube Data API v3 upload
├── config/
│   ├── config.yaml            # All pipeline settings
│   ├── client_secret.json     # Google OAuth credentials
│   └── youtube_token.json     # Cached OAuth token (auto-generated)
├── assets/
│   ├── fonts/                 # Custom fonts for captions
│   ├── music/                 # Royalty-free background tracks
│   └── branding/              # Intro/outro assets
├── output/                    # Generated runs (timestamped folders)
│   └── <run_id>/
│       ├── voiceover.mp3
│       ├── subtitles.srt
│       ├── visuals/
│       │   ├── scene_000.png
│       │   └── ...
│       └── short.mp4
├── .env                       # API keys and endpoints
├── requirements.txt
├── plan.md
└── README.md
```
| Scheduling         | Cron / Windows Task Scheduler      |

---

## Project Structure

```
youtube-shorts-pipeline/
├── config/
│   ├── config.yaml          # Pipeline settings (niche, voice, style)
│   └── .env                 # API keys (gitignored)
├── src/
│   ├── main.py              # Pipeline orchestrator
│   ├── script_generator.py  # Step 1 — LLM script generation
│   ├── voice_generator.py   # Step 2 — TTS voiceover
│   ├── visual_generator.py  # Step 3 — AI image/video generation
│   ├── subtitle_generator.py# Step 4 — Whisper transcription
│   ├── video_editor.py      # Step 5 — FFmpeg/MoviePy assembly
│   ├── metadata_generator.py# Step 6 — Title/desc/tags
│   └── youtube_uploader.py  # Step 7 — YouTube API upload
├── assets/
│   ├── music/               # Royalty-free background tracks
│   ├── fonts/               # Subtitle fonts
│   └── branding/            # Logo, intro/outro overlays
├── output/                  # Generated videos (gitignored)
├── requirements.txt
├── plan.md
└── README.md
```

---

## Implementation Order

1. **Phase 1 — Core Pipeline (MVP)**
   - [ ] Project setup, config, dependencies
   - [ ] Script generation via OpenAI
   - [ ] Voiceover generation via TTS API
   - [ ] Subtitle generation via Whisper
   - [ ] Basic video assembly with FFmpeg/MoviePy
   - [ ] Manual test of full pipeline end-to-end

2. **Phase 2 — YouTube Integration**
   - [ ] YouTube API OAuth setup
   - [ ] Upload with metadata
   - [ ] Scheduled/automated uploads

3. **Phase 3 — Polish & Automation**
   - [ ] Animated word-by-word subtitles
   - [ ] AI thumbnail generation
   - [ ] Trending topic auto-fetcher
   - [ ] Batch generation (multiple Shorts per run)
   - [ ] Logging, error handling, retries
   - [ ] Cron/scheduler for daily uploads

---

## API Keys Required

- OpenAI API key (script + subtitles)
- ElevenLabs API key (voice) — or use OpenAI TTS
- Google Cloud project with YouTube Data API v3 enabled + OAuth credentials
- (Optional) Stability AI key for Stable Diffusion

---

## Constraints & Notes

- YouTube Shorts must be **≤ 60 seconds** and **vertical (9:16)**
- YouTube API has a daily upload quota — plan around it
- Comply with YouTube ToS regarding AI-generated content disclosure
- Store API keys securely in `.env`, never commit them
- All generated music/assets must be royalty-free or AI-generated
