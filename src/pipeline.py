"""Pipeline orchestrator — wires together providers, generators, editors, and uploaders."""

import uuid
from datetime import datetime

from .config import load_config
from .models import PipelineResult

# Providers
from .providers.llm import OpenAILLMProvider, AzureLLMProvider
from .providers.tts import OpenAITTSProvider, ElevenLabsTTSProvider, AzureTTSProvider
from .providers.image import DalleImageProvider, AzureFluxImageProvider

# Generators
from .generators.script import ScriptGenerator
from .generators.voice import VoiceGenerator
from .generators.visuals import VisualGenerator
from .generators.subtitles import SubtitleGenerator
from .generators.metadata import MetadataGenerator

# Editors & uploaders
from .editors.video import VideoEditor
from .uploaders.youtube import YouTubeUploader


class Pipeline:
    """Configurable YouTube Shorts generation pipeline.

    Reads config to select the correct providers, then exposes a
    single ``run()`` method that executes every stage in order.
    """

    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self._init_providers()
        self._init_stages()

    # ------------------------------------------------------------------
    # Provider factory
    # ------------------------------------------------------------------

    def _init_providers(self):
        cfg = self.config

        # LLM
        if cfg["script"].get("provider") == "azure":
            self.llm = AzureLLMProvider(
                model=cfg["script"]["model"],
                temperature=cfg["script"]["temperature"],
            )
        else:
            self.llm = OpenAILLMProvider(
                model=cfg["script"]["model"],
                temperature=cfg["script"]["temperature"],
            )

        # TTS
        voice_cfg = cfg["voice"]
        if voice_cfg["provider"] == "azure-tts":
            self.tts = AzureTTSProvider(voice=voice_cfg["openai_voice"])
        elif voice_cfg["provider"] == "elevenlabs":
            self.tts = ElevenLabsTTSProvider(voice_id=voice_cfg["elevenlabs_voice_id"])
        else:
            self.tts = OpenAITTSProvider(
                model=voice_cfg["openai_model"],
                voice=voice_cfg["openai_voice"],
            )

        # Image generation
        vis_cfg = cfg["visuals"]
        if vis_cfg["provider"] == "azure-flux":
            self.image_provider = AzureFluxImageProvider(
                size=vis_cfg["size"],
                model=vis_cfg["image_model"],
            )
        elif vis_cfg["provider"] == "dall-e":
            self.image_provider = DalleImageProvider(
                model=vis_cfg["image_model"],
                size=vis_cfg["size"],
            )
        else:
            raise ValueError(f"Unknown image provider: {vis_cfg['provider']}")

    def _init_stages(self):
        cfg = self.config
        self.script_gen = ScriptGenerator(self.llm, cfg)
        self.voice_gen = VoiceGenerator(self.tts, cfg)
        self.visual_gen = VisualGenerator(self.image_provider, cfg)
        self.subtitle_gen = SubtitleGenerator(cfg)
        self.metadata_gen = MetadataGenerator(self.llm, cfg)
        self.video_editor = VideoEditor(cfg)
        self.uploader = YouTubeUploader(cfg)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self, brief: dict, upload: bool = True) -> PipelineResult:
        """Run the full pipeline.

        Args:
            brief: Dict with 'keywords' (list[str]) and 'description' (str).
            upload: Whether to upload to YouTube.
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        topic_summary = ", ".join(brief["keywords"])

        print(f"\n{'=' * 60}")
        print(f"  YouTube Shorts Pipeline — Run {run_id}")
        print(f"  Keywords: {topic_summary}")
        print(f"  Brief:    {brief['description'][:80]}...")
        print(f"{'=' * 60}\n")

        # 1. Script
        print("[1/7] Generating script...")
        script = self.script_gen.generate(brief)
        print(f"       Preview: {script.text[:100]}...\n")

        # 2. Voice
        print("[2/7] Generating voiceover...")
        voice = self.voice_gen.generate(script.text, run_id)
        print()

        # 3. Visuals
        print("[3/7] Generating background visuals...")
        visuals = self.visual_gen.generate(script, run_id)
        print()

        # 4. Subtitles
        print("[4/7] Generating subtitles...")
        subtitles = self.subtitle_gen.generate(voice.audio_path, run_id, script.text)
        print()

        # 5. Video assembly
        print("[5/7] Assembling video...")
        video = self.video_editor.assemble(
            voice.audio_path, visuals.image_paths, subtitles, run_id,
        )
        print()

        # 6. Metadata
        print("[6/7] Generating metadata...")
        metadata = self.metadata_gen.generate(script.text, topic_summary)
        print()

        # 7. Upload
        video_id = None
        if upload:
            print("[7/7] Uploading to YouTube...")
            thumbnail = visuals.image_paths[0] if visuals.image_paths else None
            video_id = self.uploader.upload(video.video_path, metadata, thumbnail)
        else:
            print("[7/7] Skipping upload (--no-upload)")

        print(f"\n{'=' * 60}")
        print(f"  Pipeline complete!")
        print(f"  Video: {video.video_path}")
        if video_id:
            print(f"  YouTube: https://youtube.com/shorts/{video_id}")
        print(f"{'=' * 60}\n")

        return PipelineResult(
            run_id=run_id,
            topic=topic_summary,
            script=script,
            voice=voice,
            subtitles=subtitles,
            visuals=visuals,
            video=video,
            metadata=metadata,
            video_id=video_id,
        )
