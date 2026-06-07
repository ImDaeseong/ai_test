"""
import_input_songs.py

input/*.txt + input/*.mp3 파일을 ai_anime 파이프라인으로 처리해
output/web_inputs/<timestamp>/ 에 추가하고 __validate_all.py SONG_INPUTS 를 갱신한다.

사용법:
  python scripts/import_input_songs.py               # 신규 곡만 처리
  python scripts/import_input_songs.py --dry-run     # 처리 목록만 출력
  python scripts/import_input_songs.py --force       # 이미 처리된 곡도 재처리
  python scripts/import_input_songs.py --song "제목" # 제목 부분 일치로 특정 곡만
  python scripts/import_input_songs.py --no-update   # __validate_all.py 자동 갱신 비활성화
  python scripts/import_input_songs.py --no-audio    # 오디오 분석 비활성화
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windows 콘솔에서 한글이 깨지지 않도록 stdout/stderr 를 UTF-8 로 고정
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure:
        try:
            _reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
WEB_INPUTS_DIR = PROJECT_ROOT / "output" / "web_inputs"
VALIDATE_ALL_PATH = PROJECT_ROOT / "__validate_all.py"


# ---------------------------------------------------------------------------
# 입력 파일 파싱
# ---------------------------------------------------------------------------

def read_title_from_txt(path: Path) -> str:
    """txt 파일에서 Title: 줄을 찾아 제목 반환. 없으면 파일명(stem) 반환."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception:
        return path.stem
    for line in text.splitlines():
        m = re.match(r"[Tt]itle\s*:\s*(.+)", line.strip())
        if m:
            return m.group(1).strip()
        if line.strip().startswith("["):
            break
    return path.stem


def read_bpm_genre_from_txt(path: Path) -> tuple[str, str]:
    """BPM 과 장르 태그 한 줄 반환 (미리보기용)."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception:
        return "", ""
    for line in text.splitlines():
        stripped = line.strip()
        m_genre = re.match(r"[Gg]enre\s*:\s*(.+)", stripped)
        if m_genre:
            tags = m_genre.group(1)
            bpm_m = re.search(r"\b(\d{2,3})\s*[Bb][Pp][Mm]\b", tags)
            bpm = bpm_m.group(1) if bpm_m else ""
            genre_short = tags[:60] + ("..." if len(tags) > 60 else "")
            return bpm, genre_short
        if stripped.startswith("["):
            break
    return "", ""


# ---------------------------------------------------------------------------
# 기처리 여부 확인
# ---------------------------------------------------------------------------

def get_existing_web_input_titles() -> dict[str, Path]:
    """output/web_inputs/ 에 이미 처리된 곡 제목 → 폴더 경로."""
    result: dict[str, Path] = {}
    if not WEB_INPUTS_DIR.exists():
        return result
    for folder in sorted(WEB_INPUTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        raw = folder / "raw_song.txt"
        if raw.exists():
            title = read_title_from_txt(raw)
            if title:
                result[title] = folder
    return result


def get_validate_all_titles() -> set[str]:
    """__validate_all.py SONG_INPUTS 에 등록된 제목 집합."""
    if not VALIDATE_ALL_PATH.exists():
        return set()
    text = VALIDATE_ALL_PATH.read_text(encoding="utf-8")
    return set(re.findall(r'\(\s*"([^"]+)",\s*"output/web_inputs/', text))


# ---------------------------------------------------------------------------
# 폴더 생성 및 파이프라인 실행
# ---------------------------------------------------------------------------

def find_matching_mp3(txt_path: Path) -> Path | None:
    """txt 파일과 같은 폴더에서 매칭 MP3 탐색.
    '기억나_.mp3' 처럼 stem 끝에 '_' 가 붙은 변형도 인식한다."""
    stem = txt_path.stem
    input_dir = txt_path.parent
    # 정확 일치
    exact = input_dir / (stem + ".mp3")
    if exact.exists():
        return exact
    # _ 접미사 변형 (예: 기억나_.mp3)
    underscore = input_dir / (stem + "_.mp3")
    if underscore.exists():
        return underscore
    return None


def create_web_input_folder(txt_path: Path, timestamp: str) -> tuple[Path, bool]:
    """output/web_inputs/<timestamp>/ 생성 후 raw_song.txt (+ MP3) 복사.
    반환: (폴더 경로, MP3 포함 여부)"""
    folder = WEB_INPUTS_DIR / timestamp
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(txt_path, folder / "raw_song.txt")
    mp3 = find_matching_mp3(txt_path)
    if mp3:
        shutil.copy2(mp3, folder / mp3.name)
        return folder, True
    return folder, False


def run_pipeline(folder: Path, apply_audio: bool = False) -> tuple[bool, str]:
    """scripts/run_pipeline.py 실행. (성공여부, 요약 메시지) 반환."""
    cmd = [sys.executable,
           str(PROJECT_ROOT / "scripts" / "run_pipeline.py"),
           "--input", str(folder)]
    if apply_audio:
        cmd.append("--apply-audio-analysis")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        return False, lines[-1] if lines else "파이프라인 오류"
    for line in result.stdout.splitlines():
        if "video prompt" in line.lower():
            return True, line.strip()
    return True, "완료"


# ---------------------------------------------------------------------------
# 출력 검증 (기본)
# ---------------------------------------------------------------------------

def safe_slug(title: str) -> str:
    """Windows 파일명 금지 문자 제거."""
    return re.sub(r'[\\/:*?"<>|]', "_", title.strip())


def validate_video_prompts(title: str) -> list[str]:
    """output/<slug>/video_prompts/ 의 Kling·Sora·Wan 기본 검증."""
    issues: list[str] = []
    video_dir = PROJECT_ROOT / "output" / safe_slug(title) / "video_prompts"
    if not video_dir.exists():
        return [f"video_prompts 폴더 없음"]
    for fname in sorted(video_dir.iterdir()):
        if not fname.is_file():
            continue
        content = fname.read_text(encoding="utf-8")
        if "neon magenta" in content.lower() or "cyber pink" in content.lower():
            issues.append(f"{fname.name}: RAW COLOR 잔존")
        if "## Kling AI" in content:
            m = re.search(
                r"## Kling AI\r?\n(.*?)(\r?\n\r?\n>|\r?\n##)", content, re.DOTALL
            )
            if m:
                k = m.group(1).strip()
                wc = len(k.split())
                if wc > 65:
                    issues.append(f"{fname.name} [Kling]: {wc}단어 초과")
                if not k.endswith("."):
                    issues.append(f"{fname.name} [Kling]: 마침표 없음")
        for sec in ["**Scene:**", "**Cinematography:**", "**Actions:**",
                    "**Style:**", "**Sound:**"]:
            if "## Sora" in content and sec not in content:
                issues.append(f"{fname.name} [Sora]: {sec} 누락")
        if "## Wan 2.1" in content and "Negative prompt" not in content:
            issues.append(f"{fname.name} [Wan]: Negative prompt 없음")
    return issues


# ---------------------------------------------------------------------------
# __validate_all.py 갱신
# ---------------------------------------------------------------------------

def append_to_validate_all(new_entries: list[tuple[str, str]]) -> None:
    """SONG_INPUTS 에 항목 추가 또는 갱신.
    - 같은 제목이 이미 있으면 경로를 최신 타임스탬프로 교체 (중복 방지)
    - 없는 제목은 리스트 끝에 삽입"""
    if not new_entries or not VALIDATE_ALL_PATH.exists():
        return
    text = VALIDATE_ALL_PATH.read_text(encoding="utf-8")
    existing = set(re.findall(r'\(\s*"([^"]+)",\s*"output/web_inputs/', text))

    to_update = [(n, ts) for n, ts in new_entries if n in existing]
    to_insert = [(n, ts) for n, ts in new_entries if n not in existing]

    # 기존 항목 경로 교체 (같은 제목 → 최신 타임스탬프)
    for name, ts in to_update:
        text = re.sub(
            rf'(\("{re.escape(name)}",\s*")(output/web_inputs/[^"]+)(")',
            rf'\g<1>output/web_inputs/{ts}\g<3>',
            text,
        )

    # 신규 항목 삽입 (닫는 ] 앞)
    if to_insert:
        insert_block = "".join(
            f'    ("{name}", "output/web_inputs/{ts}"),\n'
            for name, ts in to_insert
        )
        start = text.find("SONG_INPUTS = [")
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "[":
                    depth += 1
                elif text[i] == "]":
                    depth -= 1
                    if depth == 0:
                        text = text[:i] + insert_block + text[i:]
                        break

    VALIDATE_ALL_PATH.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="input/*.txt → ai_anime 파이프라인 처리 후 __validate_all.py 갱신"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="실제 처리 없이 대상 목록만 출력")
    parser.add_argument("--force", action="store_true",
                        help="이미 처리된 곡도 재처리")
    parser.add_argument("--song",
                        help="특정 곡 제목 (부분 일치, 대소문자 무시)")
    parser.add_argument("--no-update", action="store_true",
                        help="__validate_all.py SONG_INPUTS 자동 갱신 비활성화")
    parser.add_argument("--no-audio", action="store_true",
                        help="MP3 파일이 있어도 오디오 분석 적용 안 함")
    args = parser.parse_args()

    txt_files = sorted(f for f in INPUT_DIR.glob("*.txt")
                       if f.name != "song_master.json")
    if not txt_files:
        print(f"처리할 .txt 파일이 없습니다: {INPUT_DIR}")
        return 1

    existing_web = get_existing_web_input_titles()
    existing_validated = get_validate_all_titles()
    already_known = existing_web.keys() | existing_validated

    # 처리 대상 수집
    targets: list[tuple[Path, str]] = []
    for txt_path in txt_files:
        title = read_title_from_txt(txt_path)
        if args.song and args.song.lower() not in title.lower():
            continue
        if title in already_known and not args.force:
            continue
        targets.append((txt_path, title))

    skip_count = len(txt_files) - len(targets)
    if args.song:
        skip_count = 0  # --song 필터 시 skip 수 표기 생략

    print("=" * 60)
    print(f"  input/*.txt 총 {len(txt_files)}개")
    print(f"  기처리(건너뜀): {skip_count}개")
    print(f"  신규 처리 대상: {len(targets)}개")
    print("=" * 60)

    if not targets:
        print("처리할 신규 곡이 없습니다.")
        print("전체 재처리는 --force 옵션을 사용하세요.")
        return 0

    if args.dry_run:
        print("\n[DRY-RUN] 처리 예정 목록:")
        for txt_path, title in targets:
            bpm, _ = read_bpm_genre_from_txt(txt_path)
            mp3 = find_matching_mp3(txt_path)
            bpm_str = f"  BPM {bpm}" if bpm else ""
            audio_str = "  [MP3 있음]" if mp3 else ""
            print(f"  → {title}{bpm_str}{audio_str}")
        return 0

    new_entries: list[tuple[str, str]] = []
    processed = failed = 0

    for idx, (txt_path, title) in enumerate(targets, 1):
        bpm, _ = read_bpm_genre_from_txt(txt_path)
        bpm_str = f" (BPM {bpm})" if bpm else ""
        print(f"\n[{idx:03d}/{len(targets):03d}] {title}{bpm_str}")

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder, has_mp3 = create_web_input_folder(txt_path, ts)

        apply_audio = has_mp3 and not args.no_audio
        if has_mp3:
            print(f"  MP3 포함 {'(오디오 분석 적용)' if apply_audio else '(오디오 분석 비활성화)'}")

        ok, msg = run_pipeline(folder, apply_audio=apply_audio)
        if not ok:
            print(f"  ✗  파이프라인 실패: {msg}")
            shutil.rmtree(folder, ignore_errors=True)
            failed += 1
            continue

        issues = validate_video_prompts(title)
        if issues:
            print(f"  완료 — 검증 경고 {len(issues)}건:")
            for iss in issues:
                print(f"    ⚠  {iss}")
        else:
            print(f"  ✓  완료 · 검증 통과")

        new_entries.append((title, ts))
        processed += 1

    # __validate_all.py 갱신
    if new_entries and not args.no_update:
        append_to_validate_all(new_entries)
        print(f"\n__validate_all.py 에 {len(new_entries)}곡 추가 완료")

    print(f"\n{'=' * 60}")
    print(f"  완료: 성공 {processed}곡 / 실패 {failed}곡 / 건너뜀 {skip_count}곡")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
