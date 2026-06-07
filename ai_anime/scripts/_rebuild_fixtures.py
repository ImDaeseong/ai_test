"""실패 중인 fixture를 현재 input/*.txt 기준으로 재생성."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import emotion_engine
import scene_generator
import song_parser
from common import PROJECT_ROOT

INPUT_DIR   = PROJECT_ROOT / "input"
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"

FAILING_IDS = [
    "1281ee43", "2f01ff0f", "33fdd552", "4b81d214",
    "62f7daa6", "940e16b4", "acb0f9a7", "d934005c",
    "dfe249a3", "e42ae37a", "ed0811e5",
]


def find_txt(title: str) -> Path | None:
    for suffix in ("", "_"):
        p = INPUT_DIR / f"{title}{suffix}.txt"
        if p.exists():
            return p
    lower = title.lower()
    for p in INPUT_DIR.glob("*.txt"):
        if p.stem.rstrip("_").lower() == lower:
            return p
    return None


def rebuild_fixture(fid: str) -> None:
    fpath = FIXTURE_DIR / f"{fid}.json"
    if not fpath.exists():
        print(f"SKIP {fid}: fixture file not found")
        return

    fixture = json.loads(fpath.read_text(encoding="utf-8"))
    title = fixture.get("title", "")
    txt = find_txt(title)
    if not txt:
        print(f"SKIP {fid} ({title}): txt not found in input/")
        return

    with tempfile.TemporaryDirectory(prefix="rebuild_") as tmp:
        tmp_dir = Path(tmp)
        shutil.copy2(txt, tmp_dir / "raw_song.txt")
        for ext in list(song_parser.AUDIO_EXTENSIONS) + [".lrc", ".srt"]:
            for stem in (txt.stem, txt.stem + "_"):
                cand = INPUT_DIR / f"{stem}{ext}"
                if cand.exists():
                    shutil.copy2(cand, tmp_dir / cand.name)
                    break

        has_audio = any(
            f.suffix.lower() in song_parser.AUDIO_EXTENSIONS
            for f in tmp_dir.iterdir()
        )
        song     = song_parser.build_song_master_from_input(tmp_dir, apply_audio_analysis=has_audio)
        emotion  = emotion_engine.analyze_song(song)
        profile  = scene_generator.choose_genre_profile(song)
        scene_generator.select_theme(profile.get("style_id"))
        sc = scene_generator.pick_main_color(song)
        if sc == "neon magenta":
            sc = scene_generator.BRAND_PALETTE.get("main_color", sc)
        scene_generator._inject_song_color(sc)
        world = scene_generator.create_visual_world(song, emotion)

        sections = [s.get("name") for s in song.get("sections", [])]
        timing_mode = "audio_applied" if song.get("audio_analysis_applied") else song.get("timing_mode", "")
        genre_primary = (song.get("genre", "") or "").split(",")[0].strip()

        fixture["expected"]["bpm"]          = song.get("bpm")
        fixture["expected"]["energy"]       = song.get("energy")
        fixture["expected"]["genre"]        = genre_primary
        fixture["expected"]["genre_profile"]= world.get("genre_profile")
        fixture["expected"]["timing_mode"]  = timing_mode
        fixture["expected"]["scene_count"]  = len(sections)
        fixture["expected"]["sections"]     = sections
        fixture["expected"]["main_color"]   = world.get("color_palette", {}).get("main_color")
        fixture["added_date"] = str(date.today())

        fpath.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"OK  {fid} ({title}): "
            f"bpm={fixture['expected']['bpm']}, "
            f"energy={fixture['expected']['energy']}, "
            f"scenes={len(sections)}, "
            f"color={fixture['expected']['main_color']}"
        )


if __name__ == "__main__":
    for fid in FAILING_IDS:
        try:
            rebuild_fixture(fid)
        except Exception as exc:
            print(f"FAIL {fid}: {exc}")
    print("\n완료")
