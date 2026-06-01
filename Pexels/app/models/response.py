from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.scene import SceneWithVideo


class GenerateVideoResponse(BaseModel):
    status: str
    project_id: str
    scenes: list[SceneWithVideo]
    output_file: Optional[str] = None


class ProjectStatusResponse(BaseModel):
    status: str
    project_id: str
    output_file: Optional[str] = None
    error: Optional[str] = None
    scenes: list[SceneWithVideo] = []
