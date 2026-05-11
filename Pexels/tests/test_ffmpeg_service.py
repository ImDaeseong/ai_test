from pathlib import Path

import pytest

from app.services.ffmpeg_service import FFmpegService


def test_build_trim_command_contains_safe_args():
    command = FFmpegService().build_trim_command(Path("in.mp4"), Path("out.mp4"), 5, "portrait")
    assert command[0] == "ffmpeg"
    assert "-vf" in command
    assert "scale=1080:1920" in command[command.index("-vf") + 1]
    assert "fps=30" in command[command.index("-vf") + 1]
    assert "+faststart" in command


def test_build_trim_command_supports_landscape():
    command = FFmpegService().build_trim_command(Path("in.mp4"), Path("out.mp4"), 5, "landscape")
    assert "-vf" in command
    assert "scale=1920:1080" in command[command.index("-vf") + 1]


def test_build_trim_command_can_loop_short_sources():
    command = FFmpegService().build_trim_command(Path("in.mp4"), Path("out.mp4"), 30, "portrait", loop=True)
    assert "-stream_loop" in command
    assert "-1" in command


def test_build_youtube_export_command_uses_upload_friendly_codecs():
    command = FFmpegService().build_youtube_export_command(
        Path("silent.mp4"),
        Path("final.mp4"),
        music_file=Path("music.wav"),
        subtitle_file=Path("captions.srt"),
    )
    assert command[0] == "ffmpeg"
    assert "libx264" in command
    assert "high" in command
    assert "yuv420p" in command
    assert "aac" in command
    assert "48000" in command
    assert "mov_text" in command
    assert "+faststart" in command
    assert "-shortest" not in command


def test_trim_audio_command(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr("app.services.ffmpeg_service.FFmpegService.ensure_ffmpeg", lambda self: None)
    monkeypatch.setattr("subprocess.run", lambda command, **kwargs: calls.append(command))

    source = tmp_path / "music.wav"
    source.write_bytes(b"fake")
    target = tmp_path / "clip.m4a"

    FFmpegService().trim_audio(source, target, 45)

    command = calls[0]
    assert "-t" in command
    assert "45" in [str(part) for part in command]
    assert "aac" in command
    assert "48000" in command


def test_match_scene_durations_to_music_total():
    from app.models.scene import SceneWithVideo

    scenes = [
        SceneWithVideo(scene="a", search_keywords="a", mood="m", camera="c", duration=5),
        SceneWithVideo(scene="b", search_keywords="b", mood="m", camera="c", duration=5),
    ]

    FFmpegService().match_scene_durations_to_total(scenes, 30)

    assert sum(scene.duration for scene in scenes) == pytest.approx(30)
    assert scenes[0].duration == pytest.approx(15)


def test_cleanup_processed_for_output(tmp_path: Path, monkeypatch):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    keep = processed_dir / "other_scene_001.mp4"
    remove_scene = processed_dir / "final_data_scene_001.mp4"
    remove_silent = processed_dir / "final_data_silent.mp4"
    remove_concat = processed_dir / "concat_final_data.txt"
    for path in [keep, remove_scene, remove_silent, remove_concat]:
        path.write_text("x", encoding="utf-8")

    FFmpegService().cleanup_processed_for_output(Path("output/final_data.mp4"), processed_dir=processed_dir)

    assert keep.exists()
    assert not remove_scene.exists()
    assert not remove_silent.exists()
    assert not remove_concat.exists()


def test_ensure_ffmpeg_can_fail(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(RuntimeError):
        FFmpegService().ensure_ffmpeg()
