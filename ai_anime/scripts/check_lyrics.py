"""
26곡 가사 반영 품질 검증 — 결과를 output/lyric_check_result.txt 에 저장
"""
from __future__ import annotations
import pathlib, re, sys

OUT_DIR = pathlib.Path("output")
RESULT_PATH = OUT_DIR / "lyric_check_result.txt"

VALIDATE_ALL = pathlib.Path("__validate_all.py")
code = VALIDATE_ALL.read_text(encoding="utf-8")
SONGS = re.findall(r'"([^"]+)",\s*"output/web_inputs/([^"]+)"', code)
SONG_NAMES = [name for name, _ in SONGS]

def has_korean(text: str) -> bool:
    return any("가" <= c <= "힣" for c in text)

def extract_lyric_mood(text: str) -> str:
    m = re.search(r"(?:Lyric mood|Scene atmosphere):\s*([^\n.]+)", text)
    return m.group(1).strip() if m else ""

def is_scene_atmosphere(text: str) -> bool:
    return bool(re.search(r"Scene atmosphere:", text))

def is_fallback(mood: str) -> bool:
    return bool(re.search(r"emotional cue|section.*cue|music.*cue", mood, re.I))

lines: list[str] = []
def w(s: str = "") -> None:
    lines.append(s)

w("=" * 70)
w("26곡 가사 반영 품질 검증")
w("=" * 70)
w()

all_results = []

for name in SONG_NAMES:
    song_dir = OUT_DIR / name
    img_dir = song_dir / "image_prompts"

    if not img_dir.exists():
        all_results.append({"name": name, "status": "NO_OUTPUT", "issues": ["폴더 없음"], "moods": []})
        continue

    scene_files = sorted(f for f in img_dir.glob("scene_*.md"))
    if not scene_files:
        all_results.append({"name": name, "status": "NO_SCENES", "issues": ["씬 없음"], "moods": []})
        continue

    moods = []
    for f in scene_files:
        text = f.read_text(encoding="utf-8")
        mood = extract_lyric_mood(text)
        instr = is_scene_atmosphere(text)
        moods.append((f.stem, mood, instr))

    issues = []
    n_total = len(moods)
    n_instrumental = sum(1 for _, _, instr in moods if instr)
    n_lyric_scenes = n_total - n_instrumental
    n_has_ko = sum(1 for _, m, instr in moods if not instr and has_korean(m))
    n_fallback = sum(1 for _, m, instr in moods if not instr and is_fallback(m))
    unique_moods = len(set(m for _, m, _ in moods if m))

    if n_fallback > n_lyric_scenes * 0.3:
        issues.append(f"fallback 씬 {n_fallback}/{n_lyric_scenes} — 가사 파싱 실패")
    if n_lyric_scenes > 0 and n_has_ko < n_lyric_scenes * 0.5:
        issues.append(f"한국어 가사 없는 씬 {n_lyric_scenes - n_has_ko}/{n_lyric_scenes}")
    if unique_moods < n_total * 0.5:
        issues.append(f"씬별 가사 중복 ({unique_moods} unique / {n_total})")

    all_results.append({
        "name": name, "status": "PASS" if not issues else "WARN",
        "n_total": n_total, "n_instrumental": n_instrumental,
        "n_lyric_scenes": n_lyric_scenes, "n_has_ko": n_has_ko,
        "n_fallback": n_fallback, "unique_moods": unique_moods,
        "issues": issues, "moods": moods,
    })

# 요약 테이블
w(f"{'곡명':<28} {'상태':<6} {'씬수':<5} {'가사씬':<6} {'한국어가사':<11} {'연주':<5} {'fallback':<9} {'중복없음'}")
w("-" * 80)
for r in all_results:
    if "n_total" not in r:
        w(f"{r['name']:<28} {r['status']:<6}")
        continue
    flag = " <<<" if r["issues"] else ""
    nl = r.get("n_lyric_scenes", r["n_total"])
    ni = r.get("n_instrumental", 0)
    w(f"{r['name']:<28} {r['status']:<6} {r['n_total']:<5} "
      f"{nl:<6} {r['n_has_ko']}/{nl:<9} {ni:<5} {r['n_fallback']:<9} "
      f"{r['unique_moods']}/{r['n_total']}{flag}")

w()
w("=" * 70)
warn = [r for r in all_results if r.get("issues")]
if warn:
    w(f"문제 발견: {len(warn)}곡")
    for r in warn:
        w(f"\n  [{r['name']}]")
        for iss in r["issues"]:
            w(f"    - {iss}")
else:
    w("전 곡 PASS — 모든 곡의 가사가 씬에 반영되고 있습니다.")

# 씬별 가사 샘플
w()
w("=" * 70)
w("씬별 가사 샘플 (씬2~씬4, 곡별 비교)")
w("=" * 70)
for r in all_results:
    if not r.get("moods"):
        continue
    w(f"\n▶ {r['name']}")
    for stem, mood, instr in r["moods"][1:4]:
        sec = re.sub(r"scene_\d+_?", "", stem).replace("_", " ")
        if instr:
            ko_flag = "♪"
            fb = " [INSTRUMENTAL]"
        else:
            ko_flag = "O" if has_korean(mood) else "X"
            fb = " [FALLBACK]" if is_fallback(mood) else ""
        w(f"  [{sec}] {ko_flag}  {mood[:90]}{fb}")

# 파일로 저장
RESULT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f"결과 저장: {RESULT_PATH}")
pass_count = sum(1 for r in all_results if r.get("status") == "PASS")
warn_count = sum(1 for r in all_results if r.get("status") == "WARN")
print(f"PASS {pass_count} / WARN {warn_count} / 총 {len(all_results)}곡")
