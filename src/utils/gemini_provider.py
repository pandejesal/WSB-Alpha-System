import json
import logging
from typing import Any

from google import genai
from google.genai import types

from src.utils.base_provider import LLMProvider
from src.utils.config import config


class GeminiProvider(LLMProvider):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        api_key = config.api_keys.gemini_api_key.get_secret_value()
        if not api_key:
            self.logger.warning("GEMINI_API_KEY is missing. Provider will degrade gracefully.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def generate_text(self, prompt: str, **kwargs) -> str:
        if not self.client:
            return ""
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Gemini generation failed: {e}")
            return ""

    def generate_json(self, prompt: str, schema: Any, **kwargs) -> dict:
        """
        Generate structured JSON. 'schema' must be a valid Pydantic model class
        if using the new google-genai library's structured output format.
        """
        if not self.client:
            return {}
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Gemini JSON generation failed: {e}")
            return {}
