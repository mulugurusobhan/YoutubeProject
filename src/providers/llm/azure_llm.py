"""Azure OpenAI LLM provider implementation."""

import os
from openai import AzureOpenAI
from .base import BaseLLMProvider


class AzureLLMProvider(BaseLLMProvider):

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.9):
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
            api_key=os.getenv("AZURE_LLM_API_KEY"),
            api_version="2025-04-01-preview",
        )
        self.model = model
        self.temperature = temperature

    def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        model = kwargs.get("model", self.model)
        params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        # Reasoning models (e.g. gpt-5.2-chat) don't support temperature
        temp = kwargs.get("temperature", self.temperature)
        if temp is not None:
            params["temperature"] = temp

        try:
            response = self.client.chat.completions.create(**params)
        except Exception as e:
            if "temperature" in str(e).lower() and "unsupported" in str(e).lower():
                # Retry without temperature for reasoning models
                params.pop("temperature", None)
                response = self.client.chat.completions.create(**params)
            else:
                raise

        return response.choices[0].message.content.strip()
