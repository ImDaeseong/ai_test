from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.download_service import DownloadService


def test_download_temp_file_is_cleaned_on_failure(tmp_path: Path, monkeypatch):
    target = tmp_path / "video.mp4"
    temp = target.with_suffix(target.suffix + ".part")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield b"x" * 10

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.download_service.httpx.Client", FakeClient)
    monkeypatch.setattr(
        "app.services.download_service.settings",
        SimpleNamespace(max_download_mb=0, request_timeout=30),
    )

    with pytest.raises(RuntimeError):
        DownloadService()._download("http://example.com/video.mp4", target)

    assert not temp.exists()
    assert not target.exists()
