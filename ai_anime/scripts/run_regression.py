from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import emotion_engine
import scene_generator
import song_parser
from common import PROJECT_ROOT, load_config


FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"
WEB_INPUTS_DIR = PROJECT_ROOT / "output" / "web_inputs"
_VALIDATION_CONFIG = load_config("validation_rules")


def load_fixtures(song_id: str | None = None) -> list[dict[str, Any]]:
    paths = sorted(FIXTURE_DIR.glob("*.json"))
    fixtures: list[dict[str, Any]] = []
    for path in paths:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if song_id and fixture.get("song_id") != song_id:
            continue
        fixture["_fixture_path"] = str(path)
        fixtures.append(fixture)
    return fixtures


def actual_timing_mode(song: dict[str, Any]) -> str:
    if song.get("audio_analysis_applied"):
        return "audio_applied"
    return song.get("timing_mode", "")


def has_duplicate(values: list[str]) -> bool:
    normalized = [value.strip().lower() for value in values if value.strip()]
    return len(normalized) != len(set(normalized))


def has_raw_palette_token(text: str) -> bool:
    blocked = _VALIDATION_CONFIG.get("raw_palette_tokens", [])
    lowered = text.lower()
    return any(token in lowered for token in blocked)


def build_song_for_fixture(source_path: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    expected = fixture.get("expected", {})
    apply_audio = expected.get("timing_mode") == "audio_applied"
    if source_path.is_dir() and fixture.get("source_file") == "raw_song.txt":
        with tempfile.TemporaryDirectory(prefix="ai_anime_regression_") as tmp:
            tmp_dir = Path(tmp)
            shutil.copy2(source_path / "raw_song.txt", tmp_dir / "raw_song.txt")
            for extra in source_path.iterdir():
                if extra.suffix.lower() in (".lrc", ".srt"):
                    shutil.copy2(extra, tmp_dir / extra.name)
            if apply_audio:
                for audio_path in source_path.iterdir():
                    if audio_path.suffix.lower() in song_parser.AUDIO_EXTENSIONS:
                        shutil.copy2(audio_path, tmp_dir / audio_path.name)
            return song_parser.build_song_master_from_input(tmp_dir, apply_audio_analysis=apply_audio)
    return song_parser.build_song_master_from_input(source_path, apply_audio_analysis=apply_audio)


INPUT_DIR = PROJECT_ROOT / "input"


def _find_input_title_file(title: str) -> Path | None:
    """input/<title>.txt 또는 input/<title>_.txt 파일을 찾는다."""
    for suffix in ("", "_"):
        candidate = INPUT_DIR / f"{title}{suffix}.txt"
        if candidate.exists():
            return candidate
    # 제목이 완전히 일치하는 .txt 파일 탐색 (대소문자 무시)
    lower = title.lower()
    for p in INPUT_DIR.glob("*.txt"):
        if p.stem.rstrip("_").lower() == lower:
            return p
    return None


def find_source_for_fixture(fixture: dict[str, Any]) -> tuple[Path | None, str]:
    expected_title = fixture.get("title", "")
    source_file = fixture.get("source_file", "")
    direct_path = PROJECT_ROOT / "input" / source_file if source_file else None

    # Prefer explicit input_dir when present (avoids ambiguity when multiple folders share a title)
    input_dir_name = fixture.get("input_dir", "")
    if input_dir_name and WEB_INPUTS_DIR.exists():
        exact = WEB_INPUTS_DIR / input_dir_name
        if exact.is_dir() and (exact / "raw_song.txt").exists():
            return exact, "output/web_inputs"

    if direct_path and direct_path.exists() and direct_path.name != "raw_song.txt":
        song = build_song_for_fixture(direct_path, fixture)
        if not expected_title or song.get("title") == expected_title:
            return direct_path, "input"

    if WEB_INPUTS_DIR.exists():
        for raw_path in sorted(WEB_INPUTS_DIR.glob("*/raw_song.txt"), reverse=True):
            source_dir = raw_path.parent
            try:
                song = build_song_for_fixture(source_dir, fixture)
            except Exception:
                continue
            if expected_title and song.get("title") == expected_title:
                return source_dir, "output/web_inputs"

    if direct_path and direct_path.exists():
        song = build_song_for_fixture(direct_path, fixture)
        if not expected_title or song.get("title") == expected_title:
            return direct_path, "input"

    # 최후 폴백: input/<title>.txt 직접 탐색
    if expected_title:
        txt_file = _find_input_title_file(expected_title)
        if txt_file:
            return txt_file, f"input-txt"

    if direct_path and direct_path.exists():
        return direct_path, "input-title-mismatch"
    return None, "missing"


def source_has_audio(source_path: Path) -> bool:
    """회귀 소스가 실제 오디오 분석에 사용할 파일을 포함하는지 확인한다."""
    if source_path.is_dir():
        return any(
            path.is_file() and path.suffix.lower() in song_parser.AUDIO_EXTENSIONS
            for path in source_path.iterdir()
        )
    if source_path.suffix.lower() in song_parser.AUDIO_EXTENSIONS:
        return True
    return any(
        (source_path.parent / f"{source_path.stem}{suffix}").exists()
        or (source_path.parent / f"{source_path.stem}_{suffix}").exists()
        for suffix in song_parser.AUDIO_EXTENSIONS
    )


def build_actual(source_path: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    song = build_song_for_fixture(source_path, fixture)
    emotion = emotion_engine.analyze_song(song)
    profile = scene_generator.choose_genre_profile(song)
    scene_generator.select_theme(profile.get("style_id"))
    _song_color = scene_generator.pick_main_color(song)
    if _song_color == "neon magenta":
        _song_color = scene_generator.BRAND_PALETTE.get("main_color", "neon magenta")
    scene_generator._inject_song_color(_song_color)
    world = scene_generator.create_visual_world(song, emotion)
    protagonist = scene_generator.create_protagonist(song, world)
    scenes = scene_generator.generate_scenes(song, emotion, world, protagonist)
    return {
        "song": song,
        "emotion": emotion,
        "world": world,
        "scenes": scenes,
    }


def genre_matches(expected: str, actual: str) -> bool:
    expected = (expected or "").strip().lower()
    actual = (actual or "").strip().lower()
    return actual == expected or actual.startswith(f"{expected},")


# 픽스처 expected 딕셔너리에서 인식되는 키 목록
_KNOWN_EXPECTED_KEYS = frozenset({
    "bpm", "energy", "genre_profile", "timing_mode", "scene_count", "main_color",
    "genre", "sections", "mood", "no_duplicate_cameras", "no_raw_palette_in_lighting",
})

# 팔레트 토큰 검증 대상 씬 필드 (lighting 외 추가 필드 포함)
_PALETTE_CHECK_FIELDS = ("lighting", "movement", "image_prompt")


def _build_actual_from_txt(txt_file: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    """input/<title>.txt + 동명 MP3로 임시 디렉토리 구성 후 빌드."""
    expected = fixture.get("expected", {})
    apply_audio = expected.get("timing_mode") == "audio_applied"
    with tempfile.TemporaryDirectory(prefix="ai_anime_regression_") as tmp:
        tmp_dir = Path(tmp)
        shutil.copy2(txt_file, tmp_dir / "raw_song.txt")
        # 동명 오디오·타이밍 파일 함께 복사
        for ext in song_parser.AUDIO_EXTENSIONS | {".lrc", ".srt"}:
            for candidate in (
                txt_file.parent / f"{txt_file.stem}{ext}",
                txt_file.parent / f"{txt_file.stem}_{ext}",
            ):
                if candidate.exists():
                    shutil.copy2(candidate, tmp_dir / candidate.name)
                    break
        song = song_parser.build_song_master_from_input(tmp_dir, apply_audio_analysis=apply_audio)
        emotion = emotion_engine.analyze_song(song)
        profile = scene_generator.choose_genre_profile(song)
        scene_generator.select_theme(profile.get("style_id"))
        _song_color = scene_generator.pick_main_color(song)
        if _song_color == "neon magenta":
            _song_color = scene_generator.BRAND_PALETTE.get("main_color", "neon magenta")
        scene_generator._inject_song_color(_song_color)
        world = scene_generator.create_visual_world(song, emotion)
        protagonist = scene_generator.create_protagonist(song, world)
        scenes = scene_generator.generate_scenes(song, emotion, world, protagonist)
        return {"song": song, "emotion": emotion, "world": world, "scenes": scenes}


def check_fixture(fixture: dict[str, Any]) -> tuple[str, list[str]]:
    expected = fixture.get("expected", {})
    source_path, source_kind = find_source_for_fixture(fixture)
    if not source_path:
        return "skip", [f"missing source for fixture title {fixture.get('title', '')!r}"]
    if expected.get("timing_mode") == "audio_applied" and not source_has_audio(source_path):
        return "skip", [
            f"missing audio asset required by fixture ({source_kind}: {source_path})"
        ]

    if source_kind == "input-txt":
        actual = _build_actual_from_txt(source_path, fixture)
    else:
        actual = build_actual(source_path, fixture)
    song = actual["song"]
    world = actual["world"]
    scenes = actual["scenes"]
    failures: list[str] = []
    warnings: list[str] = []

    # 인식되지 않는 expected 키 경고 (오타·구버전 필드 조기 발견)
    unknown_keys = set(expected.keys()) - _KNOWN_EXPECTED_KEYS
    for k in sorted(unknown_keys):
        warnings.append(f"warn: unrecognized expected key {k!r} (ignored)")

    checks = {
        "bpm": song.get("bpm"),
        "energy": song.get("energy"),
        "genre_profile": world.get("genre_profile"),
        "timing_mode": actual_timing_mode(song),
        "scene_count": len(song.get("sections", [])),
        "main_color": world.get("color_palette", {}).get("main_color"),
    }
    for key, actual_value in checks.items():
        if key in expected and actual_value != expected[key]:
            failures.append(f"{key}: expected {expected[key]!r}, got {actual_value!r}")

    if "genre" in expected and not genre_matches(str(expected["genre"]), str(song.get("genre", ""))):
        failures.append(f"genre: expected primary {expected['genre']!r}, got {song.get('genre')!r}")

    if "sections" in expected:
        sections = [section.get("name") for section in song.get("sections", [])]
        if sections != expected["sections"]:
            failures.append(f"sections: expected {expected['sections']!r}, got {sections!r}")

    if "mood" in expected:
        mood = song.get("mood", [])
        if mood != expected["mood"]:
            failures.append(f"mood: expected {expected['mood']!r}, got {mood!r}")

    if expected.get("no_duplicate_cameras"):
        cameras = [scene.get("camera_direction", "") for scene in scenes]
        if has_duplicate(cameras):
            failures.append("camera directions contain duplicates")

    if expected.get("no_raw_palette_in_lighting"):
        for field in _PALETTE_CHECK_FIELDS:
            combined = " ".join(scene.get(field, "") for scene in scenes)
            if has_raw_palette_token(combined):
                failures.append(f"{field} still contains raw fallback palette tokens")

    details = [f"source: {source_kind} ({source_path})"]
    details.extend(warnings)
    details.extend(failures)
    return ("fail" if failures else "pass"), details if (failures or warnings) else []


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixture-based regression checks without writing pipeline outputs.")
    parser.add_argument("--song_id", help="Run one fixture by song_id.")
    parser.add_argument("--verbose", action="store_true", help="Show source path for passing fixtures too.")
    args = parser.parse_args()

    fixtures = load_fixtures(args.song_id)
    if not fixtures:
        print("No fixtures found.")
        raise SystemExit(1)

    counts = {"pass": 0, "fail": 0, "skip": 0}
    for fixture in fixtures:
        status, details = check_fixture(fixture)
        counts[status] += 1
        label = fixture.get("song_id", fixture.get("_fixture_path", "unknown"))
        title = fixture.get("title", "")
        label_line = f"[{status.upper()}] {label}" + (f" ({title})" if title and title != label else "")
        print(label_line)
        if details or args.verbose:
            for detail in details:
                print(f"  - {detail}")

    print(f"\nSummary: {counts['pass']} passed, {counts['fail']} failed, {counts['skip']} skipped")
    if counts["fail"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
