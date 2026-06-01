from pathlib import Path

from scripts.cleanup_storage import clean_directory


def test_clean_directory_keeps_gitkeep(tmp_path: Path):
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / "old.mp4").write_text("old", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "old.txt").write_text("old", encoding="utf-8")

    clean_directory(tmp_path)

    assert (tmp_path / ".gitkeep").exists()
    assert not (tmp_path / "old.mp4").exists()
    assert not nested.exists()
