from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.models.response import ProjectStatusResponse


class ProjectStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.cache_dir / "projects"

    def save(self, project: ProjectStatusResponse) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{project.project_id}.json"
        path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    def get(self, project_id: str) -> ProjectStatusResponse | None:
        path = self.root / f"{project_id}.json"
        if not path.exists():
            return None
        return ProjectStatusResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))
