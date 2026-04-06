"""Abstract base for image generation providers."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseImageProvider(ABC):
    """Interface that all image generation providers must implement."""

    @abstractmethod
    def generate(self, prompt: str, output_path: Path) -> Path:
        """Generate an image from a text prompt and save to output_path.

        Returns the output_path for convenience.
        """
