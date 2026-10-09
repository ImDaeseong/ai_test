"""OpenAI image-generation adapter for one webtoon panel."""

from __future__ import annotations

import base64
import os
from typing import Any

from openai import OpenAI

MODEL = "gpt-image-2"
IMAGE_SIZE = "1536x1024"
IMAGE_QUALITY = "medium"
IMAGE_TIMEOUT_SECONDS = 120.0
SUPPORTED_QUALITIES = ("low", "medium", "high")


class ImageClient:
    """Generate one panel image without silently retrying a paid request."""

    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.model = os.getenv("OPENAI_IMAGE_MODEL", MODEL).strip() or MODEL
        self.quality = os.getenv("OPENAI_IMAGE_QUALITY", IMAGE_QUALITY).strip().lower()
        if self.quality not in SUPPORTED_QUALITIES:
            allowed = ", ".join(SUPPORTED_QUALITIES)
            raise ValueError(f"OPENAI_IMAGE_QUALITY must be one of: {allowed}")
        self._client = OpenAI(api_key=api_key, timeout=IMAGE_TIMEOUT_SECONDS, max_retries=0)

    def generate(self, prompt: str) -> tuple[bytes, dict[str, Any]]:
        """Return decoded PNG bytes and privacy-safe usage metadata."""
        result = self._client.images.generate(
            model=self.model,
            prompt=prompt,
            size=IMAGE_SIZE,
            quality=self.quality,
            n=1,
        )
        image_bytes = base64.b64decode(result.data[0].b64_json)
        usage = result.usage.model_dump() if result.usage else {}
        return image_bytes, usage
