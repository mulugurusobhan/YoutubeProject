"""Centralized configuration loading and project paths."""

import yaml
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def load_config() -> dict:
    """Load pipeline config from config/config.yaml."""
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_output_dir(config: dict) -> Path:
    """Return the resolved output directory, creating it if needed."""
    out = PROJECT_ROOT / config["output"]["dir"]
    out.mkdir(parents=True, exist_ok=True)
    return out


def get_run_dir(config: dict, run_id: str) -> Path:
    """Return and create the directory for a specific pipeline run."""
    run_dir = get_output_dir(config) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
