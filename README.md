# YouTube Shorts Generation Pipeline

Fully automated AI pipeline that generates YouTube Shorts from a few keywords — scripts, voiceover, cinematic visuals, subtitles, video assembly, and upload — all in one command.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys — copy .env and fill in your keys
cp .env.example .env

# 3. Configure pipeline settings
#    Edit config/config.yaml (niche, voice, style, etc.)

# 4. Set up YouTube OAuth (for uploads)
#    Place your Google Cloud OAuth client_secret.json in config/
#    See "YouTube Setup" section below

# 5. Run the pipeline
python -m src.main -k "python,tricks" -d "3 mind-blowing Python tricks with dark code visuals"

# Generate without uploading
python -m src.main -k "space,facts" -d "Crazy facts about black holes" --no-upload

# Interactive mode (prompts for input)
python -m src.main
```

## How It Works

The pipeline runs 7 stages sequentially:

| Step | Stage | What It Does |
|------|-------|-------------|
| 1 | **Script + Art Direction** | LLM outputs JSON with spoken lines AND image prompts per scene |
| 2 | **Voiceover** | Chat completions with audio modality generates expressive MP3 |
| 3 | **Visuals** | FLUX.2-pro generates cinematic vertical images (5 retries per scene) |
| 4 | **Subtitles** | Word timestamps estimated from script + audio duration → SRT |
| 5 | **Video Assembly** | MoviePy composites images, audio, and styled captions into MP4 |
| 6 | **Metadata** | LLM generates SEO title, description, and hashtags |
| 7 | **Upload** | YouTube Data API v3 publishes with OAuth 2.0 |

The script generator produces both the narration and visual directions in a single LLM call, so images are coherent with the voiceover. Image prompts can reference TV/movie characters and pop culture.

## CLI Usage

```bash
python -m src.main [OPTIONS]

Options:
  -k, --keywords     Comma-separated topic keywords (e.g., "python,AI,tips")
  -d, --description  Brief describing the video's content and style
  --no-upload        Generate video locally without uploading to YouTube
```

If `-k` or `-d` are omitted, the CLI enters interactive mode and prompts for input.

## API Keys & Services

| Service | Env Variable | Purpose |
|---------|-------------|---------|
| Azure OpenAI | `AZURE_LLM_ENDPOINT`, `AZURE_LLM_API_KEY` | Script, metadata (gpt-5.2-chat) |
| Azure OpenAI | `AZURE_TTS_ENDPOINT`, `AZURE_TTS_API_KEY` | Voiceover (gpt-audio-1.5) |
| Azure AI Foundry | `AZURE_FLUX_ENDPOINT`, `AZURE_FLUX_API_KEY` | Images (FLUX.2-pro) |
| Google Cloud | `config/client_secret.json` | YouTube upload (OAuth 2.0) |
| YouTube | `YOUTUBE_API_KEY` | YouTube Data API v3 |

All keys go in `.env` at the project root.

## YouTube Upload Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable **YouTube Data API v3**
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
4. Download the JSON → save as `config/client_secret.json`
5. Go to **OAuth consent screen → Test users** → add your Google account email
6. Add `http://localhost:8080/` to **Authorized redirect URIs**
7. On first upload, a browser opens for OAuth consent. Token is cached afterward.

## Configuration

All settings in `config/config.yaml`:

```yaml
content:
  niche: "tech tips"
  max_duration_seconds: 58       # stays under 60s Shorts limit

script:
  provider: "azure"              # "azure" or "openai"
  model: "gpt-5.2-chat"
  style: "energetic, casual, Gen-Z friendly"

voice:
  provider: "azure-tts"          # "azure-tts", "openai", or "elevenlabs"
  openai_voice: "nova"           # alloy, echo, fable, onyx, nova, shimmer

visuals:
  provider: "azure-flux"         # "azure-flux" or "dall-e"
  image_model: "FLUX.2-pro"
  style: "digital illustration, vibrant colors"
  size: "1024x1792"              # vertical for Shorts

subtitles:
  font_size: 60
  color: "white"
  stroke_color: "black"

youtube:
  privacy_status: "public"       # public, unlisted, or private
  category_id: "22"              # People & Blogs
```

## Swappable Providers

All AI services are modular with abstract base classes:

| Interface | Available Providers |
|-----------|-------------------|
| `BaseLLMProvider` | `AzureLLMProvider`, `OpenAILLMProvider` |
| `BaseTTSProvider` | `AzureTTSProvider`, `OpenAITTSProvider`, `ElevenLabsTTSProvider` |
| `BaseImageProvider` | `AzureFluxImageProvider`, `DalleImageProvider` |

Switch providers by changing the `provider` field in `config.yaml`.

## Output

Each run creates a timestamped folder in `output/`:

```
output/20260406_143022_a1b2c3/
├── voiceover.mp3          # AI-generated voiceover
├── subtitles.srt          # Word-level subtitle file
├── visuals/               # Background images per scene
│   ├── scene_000.png
│   ├── scene_001.png
│   └── ...
└── short.mp4              # Final assembled YouTube Short
```

## Project Structure

```
src/
├── config.py              # Config loading, paths, dotenv
├── models.py              # Typed dataclasses for pipeline data
├── pipeline.py            # Orchestrator — wires providers & runs stages
├── main.py                # CLI entry point
├── providers/
│   ├── llm/               # LLM providers (Azure, OpenAI)
│   ├── tts/               # TTS providers (Azure, OpenAI, ElevenLabs)
│   └── image/             # Image providers (FLUX, DALL-E)
├── generators/
│   ├── script.py          # Script + image prompt generation (JSON)
│   ├── voice.py           # Voiceover generation
│   ├── visuals.py         # Image generation with retry logic
│   ├── subtitles.py       # Word-level timestamp estimation
│   └── metadata.py        # Title, description, tags generation
├── editors/
│   └── video.py           # MoviePy video composition
└── uploaders/
    └── youtube.py         # YouTube Data API v3 upload
```
