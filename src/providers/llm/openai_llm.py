"""OpenAI LLM provider implementation."""

from openai import OpenAI
from .base import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.9):
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature

    def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            temperature=kwargs.get("temperature", self.temperature),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
