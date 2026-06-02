from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from app.config import settings
from app.models.scene import SceneWithVideo

logger = logging.getLogger(__name__)


class FFmpegService:
    def ensure_ffmpeg(self) -> None:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg is not installed or not in PATH.")

    def probe_duration(self, source: Path) -> float:
        self.ensure_ffmpeg()
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return float(result.stdout.strip())
        except ValueError as exc:
            raise RuntimeError(f"Could not read media duration: {source}") from exc

    def build_trim_command(self, source: Path, target: Path, duration: float, orientation: str, loop: bool = False) -> list[str]:
        vf = f"{self._scale_crop_filter(orientation)},fps=30"
        command = [
            "ffmpeg",
            "-y",
        ]
        if loop:
            command.extend(["-stream_loop", "-1"])
        command.extend([
            "-i",
            str(source),
            "-t",
            str(duration),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-g",
            "60",
            "-keyint_min",
            "60",
            "-flags",
            "+cgop",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        ])
        return command

    def trim_scene(self, source: Path, target: Path, duration: float, orientation: str) -> Path:
        self.ensure_ffmpeg()
        target.parent.mkdir(parents=True, exist_ok=True)
        source_duration = self.probe_duration(source)
        command = self.build_trim_command(source, target, duration, orientation, loop=source_duration + 0.1 < duration)
        subprocess.run(command, check=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
        return target

    def concat(self, clips: list[Path], output: Path) -> Path:
        self.ensure_ffmpeg()
        if not clips:
            raise RuntimeError("No clips to concatenate.")
        output.parent.mkdir(parents=True, exist_ok=True)
        list_file = settings.processed_dir / f"concat_{output.stem}.txt"
        list_file.write_text(
            "\n".join(f"file '{clip.resolve().as_posix()}'" for clip in clips),
            encoding="utf-8",
        )
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        except subprocess.CalledProcessError as first_err:
            logger.warning(
                "concat stream-copy failed (%s), retrying with re-encode: %s",
                first_err.returncode,
                (first_err.stderr or "").strip()[-300:] or "(no stderr)",
            )
            command = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return output

    def render(
        self,
        scenes: list[SceneWithVideo],
        output: Path,
        music_file: Path | None = None,
        subtitle_file: Path | None = None,
        target_duration: float | None = None,
    ) -> Path:
        settings.ensure_storage()
        self.cleanup_processed_for_output(output)
        effective_music_file = music_file
        temp_music_file: Path | None = None
        if music_file:
            music_duration = self.probe_duration(music_file)
            render_duration = min(music_duration, target_duration) if target_duration else music_duration
            if target_duration and target_duration < music_duration:
                temp_music_file = settings.processed_dir / f"{output.stem}_music_clip.m4a"
                effective_music_file = self.trim_audio(music_file, temp_music_file, render_duration)
            self.match_scene_durations_to_total(scenes, render_duration)
        elif target_duration:
            self.match_scene_durations_to_total(scenes, target_duration)
        clips: list[Path] = []
        for index, scene in enumerate(scenes, start=1):
            if not scene.video_file:
                raise RuntimeError(f"Scene {index} is missing video_file.")
            clip_path = settings.processed_dir / f"{output.stem}_scene_{index:03d}.mp4"
            processed = self.trim_scene(Path(scene.video_file), clip_path, scene.duration, scene.orientation)
            scene.processed_file = str(processed)
            clips.append(processed)
        silent_video = settings.processed_dir / f"{output.stem}_silent.mp4"
        self.concat(clips, silent_video)
        return self.export_youtube_mp4(silent_video, output, music_file=effective_music_file, subtitle_file=subtitle_file)

    def trim_audio(self, source: Path, target: Path, duration: float) -> Path:
        self.ensure_ffmpeg()
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-t",
            str(duration),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(target),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return target

    def cleanup_processed_for_output(self, output: Path, processed_dir: Path | None = None) -> None:
        root = processed_dir or settings.processed_dir
        root.mkdir(parents=True, exist_ok=True)
        patterns = [
            f"{output.stem}_scene_*.mp4",
            f"{output.stem}_silent.mp4",
            f"{output.stem}_music_clip.m4a",
            f"concat_{output.stem}*.txt",
        ]
        for pattern in patterns:
            for path in root.glob(pattern):
                if path.is_file():
                    path.unlink()

    def match_scene_durations_to_total(self, scenes: list[SceneWithVideo], total_duration: float) -> None:
        if not scenes:
            raise RuntimeError("No scenes to retime.")
        if total_duration <= 0:
            raise RuntimeError("Music duration must be greater than zero.")
        current_total = sum(scene.duration for scene in scenes)
        if current_total <= 0:
            even_duration = total_duration / len(scenes)
            for scene in scenes:
                scene.duration = even_duration
            return
        scale = total_duration / current_total
        for scene in scenes:
            scene.duration = max(0.5, scene.duration * scale)
        drift = total_duration - sum(scene.duration for scene in scenes)
        scenes[-1].duration = max(0.5, scenes[-1].duration + drift)

    def build_youtube_export_command(
        self,
        video_file: Path,
        output: Path,
        music_file: Path | None = None,
        subtitle_file: Path | None = None,
    ) -> list[str]:
        command = ["ffmpeg", "-y", "-i", str(video_file)]
        input_index = 1
        audio_index: int | None = None
        subtitle_index: int | None = None

        if music_file:
            command.extend(["-i", str(music_file)])
            audio_index = input_index
            input_index += 1

        if subtitle_file:
            command.extend(["-i", str(subtitle_file)])
            subtitle_index = input_index

        command.extend(["-map", "0:v:0"])
        if audio_index is not None:
            command.extend(["-map", f"{audio_index}:a:0"])
        if subtitle_index is not None:
            command.extend(["-map", f"{subtitle_index}:0"])

        # Video is already encoded by trim_scene; copy to avoid quality loss
        command.extend(["-c:v", "copy"])
        if audio_index is not None:
            command.extend(["-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2"])
        if subtitle_index is not None:
            command.extend(["-c:s", "mov_text"])
        command.extend(["-movflags", "+faststart"])
        command.append(str(output))
        return command

    def export_youtube_mp4(
        self,
        video_file: Path,
        output: Path,
        music_file: Path | None = None,
        subtitle_file: Path | None = None,
    ) -> Path:
        self.ensure_ffmpeg()
        if music_file and not music_file.exists():
            raise RuntimeError(f"Music file does not exist: {music_file}")
        if subtitle_file and not subtitle_file.exists():
            raise RuntimeError(f"Subtitle file does not exist: {subtitle_file}")
        output.parent.mkdir(parents=True, exist_ok=True)
        command = self.build_youtube_export_command(video_file, output, music_file=music_file, subtitle_file=subtitle_file)

        subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return output

    def _scale_crop_filter(self, orientation: str) -> str:
        if orientation == "landscape":
            return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        if orientation == "square":
            return "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080"
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
