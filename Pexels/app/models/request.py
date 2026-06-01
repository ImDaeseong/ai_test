from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.scene import Orientation


class GenerateVideoRequest(BaseModel):
    text: str = Field(min_length=1)
    orientation: Orientation = "portrait"
    style: str = "cinematic"
    with_subtitles: bool = False
    with_music: bool = False
    music_file: Optional[str] = None
    subtitle_file: Optional[str] = None
    output_path: Optional[str] = None
    target_duration: Optional[float] = None
