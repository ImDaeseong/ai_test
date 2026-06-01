from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


Orientation = Literal["portrait", "landscape", "square"]


class Scene(BaseModel):
    scene: str = Field(min_length=1)
    scene_ko: Optional[str] = None
    search_keywords: str = Field(min_length=1)
    mood: str = Field(min_length=1)
    camera: str = Field(min_length=1)
    orientation: Orientation = "portrait"
    duration: float = Field(gt=0, le=60)

    @field_validator("scene", "search_keywords", "mood", "camera")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class SceneWithVideo(Scene):
    video_id: Optional[int] = None
    video_file: Optional[str] = None
    processed_file: Optional[str] = None
