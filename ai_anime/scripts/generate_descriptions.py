"""
26곡 이미지 / 영상 프롬프트 → 한국어 설명 파일 생성기
출력: output/이미지_설명.md, output/영상_설명.md
"""
from __future__ import annotations
import pathlib
import re
import sys

OUT_DIR = pathlib.Path("output")

# 섹션 이름 한국어 매핑
_SEC_KO = {
    "intro": "인트로", "verse": "버스", "pre_chorus": "프리코러스",
    "pre-chorus": "프리코러스", "chorus": "코러스", "bridge": "브릿지",
    "outro": "아웃트로", "hook": "훅", "refrain": "리프레인",
    "drop": "드롭", "buildup": "빌드업", "breakdown": "브레이크다운",
    "turnaround": "캐릭터 시트", "model_sheet": "캐릭터 시트",
}


def _section_ko(stem: str) -> str:
    low = stem.lower()
    # 씬 번호 이후 부분 추출: scene_03_pre_chorus → pre_chorus
    m = re.search(r"scene_?\d+[_-](.+)$", low)
    key = m.group(1) if m else low
    key = key.replace("-", "_")
    return _SEC_KO.get(key, key.replace("_", " ").title())


def _scene_num(stem: str) -> int:
    m = re.search(r"\d+", stem)
    return int(m.group()) if m else 0


def _between(text: str, start: str, *ends: str) -> str:
    i = text.find(start)
    if i == -1:
        return ""
    i += len(start)
    for end in ends:
        j = text.find(end, i)
        if j != -1:
            return text[i:j].strip()
    return text[i:].strip()


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# ---------------------------------------------------------------------------
# 이미지 프롬프트 파싱
# ---------------------------------------------------------------------------

def parse_image(stem: str, text: str) -> str:
    """파일 내용 → 한국어 설명 1~2문단"""
    is_char = "turnaround" in stem.lower() or "model_sheet" in stem.lower()
    num = _scene_num(stem)
    sec = _section_ko(stem)

    if is_char:
        # 캐릭터 시트 — 외형 정보를 compact하게 추출
        # FLUX.1 섹션이 가장 간결한 자연어
        flux = _between(text, "## FLUX.1 (Black Forest Labs)\n", "\n\n**규칙:**")
        if not flux:
            flux = _between(text, "## FLUX.1 (Black Forest Labs)\n", "\n**규칙:**")
        # 첫 문장만
        first_sent = flux.split(".")[0].strip() if flux else ""
        hair_m = re.search(r"(\w[\w\s-]+(?:hair|hairstyle|cut)[^,]{0,40})", text, re.I)
        outfit_m = re.search(r"((?:jacket|coat|hoodie|shirt|outfit)[^,]{0,50})", text, re.I)
        hair = _clean(hair_m.group(1)) if hair_m else ""
        outfit = _clean(outfit_m.group(1)) if outfit_m else ""
        color_m = re.search(r"single\s+([\w\s]+?)\s+identity accent", text, re.I)
        color = _clean(color_m.group(1)) if color_m else ""

        lines = [f"**씬 {num} — {sec}**"]
        lines.append("이 곡 전용 주인공 캐릭터의 기준 외형 설정 이미지입니다.")
        if hair:
            lines.append(f"헤어스타일: {hair}.")
        if outfit:
            lines.append(f"의상: {outfit}.")
        if color:
            lines.append(f"곡 대표색: {color}.")
        return "  " + "\n  ".join(lines)

    # 일반 씬
    # 1) FLUX.1 섹션 — 이미 자연어 문장
    flux = _between(text, "## FLUX.1 (Black Forest Labs)\n", "\n\n**규칙:**")
    if not flux:
        flux = _between(text, "## FLUX.1 (Black Forest Labs)\n", "\n**규칙:**")
    flux = _clean(flux)
    # anime style 태그 이후 제거
    flux = re.sub(r"\.\s*anime style.*$", ".", flux, flags=re.I | re.DOTALL)
    flux = _clean(flux)

    # 2) 가사 단서 (한국어)
    lyric_m = re.search(r"Lyric mood:\s*([^\n.]+)", text, re.I)
    lyric = _clean(lyric_m.group(1)) if lyric_m else ""

    # 3) 핵심 시각 상징
    sym_m = re.search(r"Visual symbol:\s*([^;.]+?)(?:;|supporting symbols:|\n)", text, re.I)
    symbol = _clean(sym_m.group(1)) if sym_m else ""

    # 4) 분위기
    mood_m = re.search(r"([a-zA-Z ,'–—-]{10,60}?)\s+(?:cinematic anime|anime pop)\s+mood", text, re.I)
    mood = _clean(mood_m.group(1)) if mood_m else ""

    lines = [f"**씬 {num} — {sec}**"]
    if lyric:
        lines.append(f"가사 이미지: 『{lyric}』")
    if flux:
        lines.append(flux)
    if symbol:
        lines.append(f"핵심 시각 상징: {symbol}.")
    if mood:
        lines.append(f"분위기: {mood}.")
    if not flux and not lyric:
        lines.append("(씬 상세 정보 없음)")
    return "  " + "\n  ".join(lines)


# ---------------------------------------------------------------------------
# 영상 프롬프트 파싱
# ---------------------------------------------------------------------------

def parse_video(stem: str, text: str) -> str:
    """파일 내용 → 한국어 설명"""
    num = _scene_num(stem)
    sec = _section_ko(stem)

    # Kling AI 섹션 — 40-60단어, 핵심 동작/카메라/분위기
    kling = _between(text, "## Kling AI\n", "\n\n>")
    if not kling:
        kling = _between(text, "## Kling AI\n", "\n>")
    kling = _clean(kling)

    # 가사 단서 (한국어) — Luma 섹션에 포함됨
    lyric_m = re.search(r"\*\*Lyric cue:\*\*\s*([^\n]+)", text)
    if not lyric_m:
        lyric_m = re.search(r"Lyric mood:\s*([^\n.]+)", text)
    lyric = _clean(lyric_m.group(1)) if lyric_m else ""

    # 타이밍
    timing_m = re.search(r"section starts at\s*([\d.]+)s and ends at\s*([\d.]+)s", text)
    timing = f"{float(timing_m.group(1)):.0f}초~{float(timing_m.group(2)):.0f}초" if timing_m else ""

    lines = [f"**씬 {num} — {sec}**" + (f"  [{timing}]" if timing else "")]
    if lyric:
        lines.append(f"가사 흐름: 『{lyric}』")
    if kling:
        lines.append(kling)
    else:
        lines.append("(영상 설명 없음)")
    return "  " + "\n  ".join(lines)


# ---------------------------------------------------------------------------
# 단일 곡 처리
# ---------------------------------------------------------------------------

def process_song(song_dir: pathlib.Path) -> tuple[str, str]:
    name = song_dir.name
    img_dir = song_dir / "image_prompts"
    vid_dir = song_dir / "video_prompts"

    img_files = sorted(img_dir.glob("*.md")) if img_dir.exists() else []
    vid_files = sorted(vid_dir.glob("*.md")) if vid_dir.exists() else []

    if not img_files:
        return "", ""

    img_blocks = [parse_image(f.stem, f.read_text(encoding="utf-8")) for f in img_files]
    vid_blocks = [parse_video(f.stem, f.read_text(encoding="utf-8")) for f in vid_files]

    img_section = f"## {name}\n\n" + "\n\n".join(img_blocks)
    vid_section = f"## {name}\n\n" + "\n\n".join(vid_blocks)
    return img_section, vid_section


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    song_dirs = [
        d for d in sorted(OUT_DIR.iterdir())
        if d.is_dir()
        and d.name not in {"web_inputs", "storyboard", "images", "videos"}
        and (d / "image_prompts").exists()
    ]

    if not song_dirs:
        print("출력 디렉토리에서 곡 폴더를 찾을 수 없습니다.")
        sys.exit(1)

    print(f"처리 대상: {len(song_dirs)}곡")

    img_sections: list[str] = []
    vid_sections: list[str] = []

    for sd in song_dirs:
        print(f"  [{sd.name}]")
        ib, vb = process_song(sd)
        if ib:
            img_sections.append(ib)
        if vb:
            vid_sections.append(vb)

    img_header = (
        "# 이미지 씬 설명서\n\n"
        "> 각 곡의 씬별로 어떤 배경·캐릭터·색감·분위기의 이미지를 생성하는지 설명합니다.\n"
        "> 이미지 AI(GPT Image, Midjourney 등)에 전달하는 프롬프트의 핵심 내용을 사람이 읽기 쉬운 형태로 정리했습니다.\n\n"
        "---\n\n"
    )
    vid_header = (
        "# 영상 씬 설명서\n\n"
        "> 각 씬에서 카메라가 어떻게 움직이고, 주인공이 어떤 동작을 하는지 설명합니다.\n"
        "> 영상 AI(Kling AI 기준 40~60단어)의 핵심 장면 묘사를 사람이 읽기 쉬운 형태로 정리했습니다.\n\n"
        "---\n\n"
    )

    separator = "\n\n---\n\n"
    img_path = OUT_DIR / "이미지_설명.md"
    vid_path = OUT_DIR / "영상_설명.md"

    img_path.write_text(img_header + separator.join(img_sections), encoding="utf-8")
    vid_path.write_text(vid_header + separator.join(vid_sections), encoding="utf-8")

    total_img = sum(1 for _ in img_path.read_text(encoding="utf-8").split("**씬 ")) - 1
    total_vid = sum(1 for _ in vid_path.read_text(encoding="utf-8").split("**씬 ")) - 1

    print(f"\n완료:")
    print(f"  이미지 설명 → {img_path}  ({img_path.stat().st_size:,} bytes, 약 {total_img}개 씬)")
    print(f"  영상 설명   → {vid_path}  ({vid_path.stat().st_size:,} bytes, 약 {total_vid}개 씬)")


if __name__ == "__main__":
    main()
