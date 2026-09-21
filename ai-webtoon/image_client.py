"""OpenAI image-generation adapter for one webtoon panel."""

from __future__ import annotations

import base64
import os
from typing import Any

from openai import OpenAI

MODEL = "gpt-image-2"
IMAGE_SIZE = "1536x1024"
IMAGE_TIMEOUT_SECONDS = 120.0


class ImageClient:
    """Generate one panel image without silently retrying a paid request."""

    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self._client = OpenAI(api_key=api_key, timeout=IMAGE_TIMEOUT_SECONDS, max_retries=0)

    def generate(self, prompt: str) -> tuple[bytes, dict[str, Any]]:
        """Return decoded PNG bytes and privacy-safe usage metadata."""
        result = self._client.images.generate(
            model=MODEL, prompt=prompt, size=IMAGE_SIZE, n=1
        )
        image_bytes = base64.b64decode(result.data[0].b64_json)
        usage = result.usage.model_dump() if result.usage else {}
        return image_bytes, usage
