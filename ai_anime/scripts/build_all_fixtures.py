"""전체 26곡 regression 픽스처 생성 스크립트.

이미 존재하는 fixtures는 덮어쓰지 않음 (--overwrite 플래그로 강제 재생성 가능).
생성된 값은 현재 파이프라인 출력을 기준으로 함 — 검증 완료된 상태에서 실행할 것.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import emotion_engine
import scene_generator
import song_parser
from common import PROJECT_ROOT, slugify

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"

SONG_INPUTS: list[tuple[str, str]] = [
    ("그대로 접힌 양말",             "output/web_inputs/20260521-121308"),
    ("들리잖아",                     "output/web_inputs/20260521-121203"),
    ("오늘은 좀 괜찮아",             "output/web_inputs/20260521-121103"),
    ("환승역",                       "output/web_inputs/20260521-120955"),
    ("아직 우리",                    "output/web_inputs/20260521-120821"),
    ("나는 힘들 때 웃어 본다",       "output/web_inputs/20260520-082130"),
    ("사랑이 다가올 때",             "output/web_inputs/20260519-165705"),
    ("이별을 배운다",                "output/web_inputs/20260519-163812"),
    ("하나야",                       "output/web_inputs/20260519-123304"),
    ("커피 한 잔",                   "output/web_inputs/20260519-115621"),
    ("차가운 안녕",                  "output/web_inputs/20260519-115448"),
    ("날개짓",                       "output/web_inputs/20260519-115321"),
    ("다시 마주한 순간",             "output/web_inputs/20260519-102140"),
    ("위험해",                       "output/web_inputs/20260519-101944"),
    ("떠나고 싶어",                  "output/web_inputs/20260519-084155"),
    ("오늘도 네 곁을 맴돌아",        "output/web_inputs/20260519-083812"),
    ("헤어진 날",                    "output/web_inputs/20260518-142326"),
    ("100 Seconds",                  "output/web_inputs/20260518-134425"),
    ("아무 일도 일어나지 않는 하루", "output/web_inputs/20260518-112401"),
    ("우산 없는 날",                 "output/web_inputs/20260518-112013"),
    ("나 혼자",                      "output/web_inputs/20260518-110401"),
    ("너는 완벽했어",                "output/web_inputs/20260518-104806"),
    ("그 시절이 그립다",             "output/web_inputs/20260518-104613"),
    ("같은 하늘 다른 세상",          "output/web_inputs/20260518-104429"),
    ("별빛 미소",                    "output/web_inputs/20260518-100127"),
    ("너한테 가고 있어",             "output/web_inputs/20260518-094837"),
]


def existing_song_ids() -> set[str]:
    return {
        json.loads(p.read_text(encoding="utf-8")).get("song_id", "")
        for p in FIXTURE_DIR.glob("*.json")
    }


def build_fixture(input_dir: Path) -> dict:
    apply_audio = any(
        f.suffix.lower() in song_parser.AUDIO_EXTENSIONS
        for f in input_dir.iterdir()
    )
    song = song_parser.build_song_master_from_input(input_dir, apply_audio_analysis=apply_audio)
    emotion = emotion_engine.analyze_song(song)
    profile = scene_generator.choose_genre_profile(song)
    scene_generator.select_theme(profile.get("style_id"))

    song_color = scene_generator.pick_main_color(song)
    if song_color == "neon magenta":
        song_color = scene_generator.BRAND_PALETTE.get("main_color", "neon magenta")
    scene_generator._inject_song_color(song_color)

    world = scene_generator.create_visual_world(song, emotion)

    sections = [s.get("name") for s in song.get("sections", [])]
    timing_mode = "audio_applied" if song.get("audio_analysis_applied") else song.get("timing_mode", "")
    genre_raw = song.get("genre", "")
    genre_primary = genre_raw.split(",")[0].strip() if genre_raw else ""

    return {
        "song_id": slugify(song["title"]),
        "source_file": "raw_song.txt",
        "input_dir": input_dir.name,
        "title": song["title"],
        "expected": {
            "bpm": song.get("bpm"),
            "energy": song.get("energy"),
            "genre": genre_primary,
            "genre_profile": world.get("genre_profile"),
            "timing_mode": timing_mode,
            "scene_count": len(sections),
            "sections": sections,
            "main_color": world.get("color_palette", {}).get("main_color"),
            "no_duplicate_cameras": True,
            "no_raw_palette_in_lighting": True,
        },
        "added_date": str(date.today()),
        "notes": "",
        "known_issues": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="전체 26곡 regression 픽스처 생성")
    parser.add_argument("--overwrite", action="store_true", help="기존 픽스처도 덮어씀")
    args = parser.parse_args()

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    existing = existing_song_ids()
    created = skipped = failed = 0

    for title, input_rel in SONG_INPUTS:
        input_dir = PROJECT_ROOT / input_rel
        if not input_dir.exists():
            print(f"  [SKIP] {title}: 입력 폴더 없음 ({input_rel})")
            skipped += 1
            continue

        try:
            fixture = build_fixture(input_dir)
        except Exception as e:
            print(f"  [FAIL] {title}: {e}")
            failed += 1
            continue

        song_id = fixture["song_id"]
        out_path = FIXTURE_DIR / f"{song_id}.json"

        if song_id in existing and not args.overwrite:
            print(f"  [SKIP] {title} ({song_id}): 이미 존재")
            skipped += 1
            continue

        out_path.write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        action = "overwrite" if song_id in existing else "created"
        print(f"  [OK] {title} ({song_id}): {action} — "
              f"bpm={fixture['expected']['bpm']}, "
              f"scenes={fixture['expected']['scene_count']}, "
              f"color={fixture['expected']['main_color']}")
        created += 1

    print(f"\n완료: 생성 {created}, 스킵 {skipped}, 실패 {failed}")


if __name__ == "__main__":
    main()
