from pathlib import Path

from app.services.data_input_service import DataInputService


def test_extract_lrc_lines(tmp_path: Path):
    path = tmp_path / "song.lrc"
    path.write_text(
        "[00:01.00][Intro]\n[00:02.00]첫 번째 줄\n[00:03.00]Second line\n",
        encoding="utf-8",
    )

    text = DataInputService().extract_text(path)

    assert "첫 번째 줄" in text
    assert "Second line" in text
    assert "Intro" not in text


def test_extract_srt_lines(tmp_path: Path):
    path = tmp_path / "song.srt"
    path.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,000 --> 00:00:03,000\nWorld\n",
        encoding="utf-8",
    )

    text = DataInputService().extract_text(path)

    assert text.splitlines() == ["Hello", "World"]


def test_discover_prefers_lrc_and_finds_assets(tmp_path: Path):
    (tmp_path / "a.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nSRT\n", encoding="utf-8")
    (tmp_path / "b.lrc").write_text("[00:01.00]LRC\n", encoding="utf-8")
    (tmp_path / "music.mp3").write_bytes(b"fake")
    (tmp_path / "cover.png").write_bytes(b"fake")

    assets = DataInputService().discover(tmp_path)

    assert assets.lyric_file.name == "b.lrc"
    assert assets.audio_file and assets.audio_file.name == "music.mp3"
    assert assets.subtitle_file and assets.subtitle_file.name == "a.srt"
    assert assets.image_file and assets.image_file.name == "cover.png"
    assert assets.text == "LRC"
