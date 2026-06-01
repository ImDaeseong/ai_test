from __future__ import annotations

import json
import re

import httpx

from app.config import settings
from app.models.scene import Scene
from app.utils.retry import retry


SCENE_PROMPT = """You are an expert music video director and visual scene planner.

Analyze the following text and split it into cinematic video scenes.

Return ONLY valid JSON array.
Do not include markdown.
Do not include explanation.

Create 6 to 8 scenes unless the input is extremely short.
Keep each initial duration between 4 and 8 seconds.
The application will retime scenes later to match the music duration, so focus on clear visual variety.

Each scene must include:
- scene: detailed visual scene description in English
- scene_ko: natural Korean explanation of the visual scene
- search_keywords: short Pexels search keywords in English
- mood: emotional mood
- camera: camera direction
- orientation: portrait, landscape, or square
- duration: duration in seconds

Preferred orientation: {orientation}
Visual style: {style}

Input text:
{text}

Output format:
[
  {{
    "scene": "...",
    "scene_ko": "...",
    "search_keywords": "...",
    "mood": "...",
    "camera": "...",
    "orientation": "portrait",
    "duration": 5
  }}
]
"""


class GeminiService:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

    def analyze_text(self, text: str, orientation: str, style: str) -> list[Scene]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is missing.")

        prompt = SCENE_PROMPT.format(text=text, orientation=orientation, style=style)
        raw_text = self._generate_content(prompt)
        return parse_scenes_json(raw_text)

    @retry()
    def _generate_content(self, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        params = {"key": self.api_key}
        with httpx.Client(timeout=settings.request_timeout) as client:
            try:
                response = client.post(url, params=params, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                body = exc.response.text[:300]
                raise RuntimeError(f"Gemini API request failed with status {status}: {body}") from None
            data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected Gemini response shape.") from exc


def parse_scenes_json(raw_text: str) -> list[Scene]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini response is not valid JSON.") from exc
    if not isinstance(data, list) or not data:
        raise ValueError("Gemini response must be a non-empty JSON array.")
    return [Scene.model_validate(item) for item in data]
