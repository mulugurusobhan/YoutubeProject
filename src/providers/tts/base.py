"""Abstract base for TTS providers."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseTTSProvider(ABC):
    """Interface that all text-to-speech providers must implement."""

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> Path:
        """Convert text to speech and write audio to output_path.

        Returns the output_path for convenience.
        """
