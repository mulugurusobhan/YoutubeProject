"""Abstract base for LLM providers."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Interface that all LLM providers must implement."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Send a chat completion request and return the assistant's text."""
