from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = PROJECT_ROOT / "input"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
CONFIGS_DIR = PROJECT_ROOT / "configs"
REFERENCE_DIR = PROJECT_ROOT / "reference"

FILE_RETRY_ATTEMPTS = 40
FILE_RETRY_DELAY_SECONDS = 0.25

STYLE_REFERENCE_FILE = "00_style_reference.md"
STORYBOARD_FILE = "01_storyboard.md"
OVERVIEW_FILE = "00_prompt_overview.md"
ALL_OVERVIEW_FILE = "_ALL_PANEL_OVERVIEW.md"
PANEL_AUDIT_FILE = "_PANEL_AUDIT.md"

IDENTITY_LOCK_TERMS = [
    "original fantasy skeleton music band",
    "Do not redesign",
    "not based on any existing IP",
]

POLICY_RISK_TERMS = (
    "undead cyberpunk",
    "chained microphone",
    "chains",
    "spikes",
    "torn fabric",
    "rib cage",
    "skeletal hand",
    "skeletal fingers",
    "screams aggressively",
    "headbanging",
    "corpse",
    "blood",
    "gore",
    "weapon",
    "knife",
)


# ── 출력 스트림 설정 (Windows CP949 크래시 방지) ────────────────────────────

def configure_output_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (OSError, ValueError):
            pass


# ── Config 로드 ──────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Config 파일이 없습니다: {path}")


_WEBTOON_STYLES = load_json(CONFIGS_DIR / "webtoon_styles.json")
_CHARACTER_LOCK = load_json(CONFIGS_DIR / "character_lock.json")
_PANEL_TYPES    = load_json(CONFIGS_DIR / "panel_types.json")
_CUT_TIMING     = load_json(CONFIGS_DIR / "cut_timing.json")
_PANEL_SEQS     = load_json(CONFIGS_DIR / "panel_sequences.json")
_LYRIC_MAP      = load_json(CONFIGS_DIR / "lyric_visual_map.json")
_BAND_PROFILES  = load_json(CONFIGS_DIR / "band_performance_profiles.json")


# ── 파일 I/O ─────────────────────────────────────────────────────────────────

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    def _write() -> None:
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    run_with_retries("write", path, _write)


def run_with_retries(action: str, path: Path, callback) -> None:
    last_err: OSError | None = None
    for attempt in range(1, FILE_RETRY_ATTEMPTS + 1):
        try:
            callback()
            return
        except OSError as exc:
            last_err = exc
            if not _is_retryable(exc):
                raise
            if attempt < FILE_RETRY_ATTEMPTS:
                time.sleep(FILE_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"파일이 잠겨 있어 {action} 실패: {path}") from last_err


def _is_retryable(exc: OSError) -> bool:
    return getattr(exc, "winerror", None) in {32, 33} or isinstance(exc, PermissionError)


# ── Song 파싱 (ai_img_video_prompt와 동일한 입력 형식) ───────────────────────

FIELD_ALIASES: dict[str, str] = {
    "title": "title", "제목": "title", "song title": "title",
    "genre": "genre", "장르": "genre", "style": "genre", "스타일": "genre",
    "bpm": "bpm", "tempo": "tempo", "템포": "tempo",
    "mood": "mood", "분위기": "mood",
    "emotion": "emotion", "감정": "emotion",
    "energy": "energy", "에너지": "energy",
    "weirdness": "weirdness",
    "style influence": "style_influence",
}

SECTION_PATTERN = re.compile(
    r"^\[(?P<label>"
    r"Intro|Verse(?:\s*\d+)?|Pre[- ]?Chorus|Chorus(?:\s*\d+)?|Post[- ]?Chorus|"
    r"Build|Bridge|Final\s+Chorus|Outro|Interlude|Instrumental|Drop|Hook|Solo|Breakdown"
    r")(?:\s*[:|]\s*(?P<note>.*?))?\]$",
    re.IGNORECASE,
)


@dataclass
class Section:
    label: str
    note: str
    lines: list[str]


@dataclass
class Song:
    title: str
    genre: str
    bpm: str
    mood: str
    emotion: str
    sections: list[Section]
    raw_text: str


def _normalize_field_key(key: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", key.strip().lstrip("﻿").lower())
    return FIELD_ALIASES.get(cleaned)


def _strip_noise_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if re.fullmatch(r"\d+[dhms,\s]+ago", stripped, re.IGNORECASE):
            continue
        if stripped.lower().startswith("cover image for "):
            continue
        if re.fullmatch(r"\d+:\d{2}(?::\d{2})?", stripped):
            continue
        lines.append(line)
    return lines


def _parse_key_value(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    normalized = _normalize_field_key(key)
    if not normalized:
        return None
    return normalized, value.strip()


def _parse_loose_metadata(line: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"(Weirdness|Style Influence)\s+(.+)", line.strip(), re.IGNORECASE)
    if not match:
        return None
    key = _normalize_field_key(match.group(1))
    return (key, match.group(2).strip()) if key else None


def _is_negative_tag(tag: str) -> bool:
    c = tag.strip().lstrip()
    return c.startswith(("-", "‑", "–", "—")) or c.lower().startswith(("no ", "not "))


def _clean_genre(text: str) -> str:
    return ", ".join(i.strip() for i in text.split(",") if i.strip() and not _is_negative_tag(i))


def _normalize_section_label(label: str) -> str:
    text = re.sub(r"\s+", " ", label.strip().replace("-", " "))
    words = text.split()
    if not words:
        return "Section"
    if words[0].lower() == "pre":
        return "Pre-Chorus"
    if words[0].lower() == "post":
        return "Post-Chorus"
    if text.lower() == "final chorus":
        return "Final Chorus"
    return " ".join(w.capitalize() for w in words)


def _parse_sections(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    for raw_line in lines:
        match = SECTION_PATTERN.match(raw_line.strip())
        if match:
            if current:
                sections.append(current)
            current = Section(
                label=_normalize_section_label(match.group("label")),
                note=(match.group("note") or "").strip(),
                lines=[],
            )
            continue
        if current is not None:
            current.lines.append(raw_line.rstrip())
    if current:
        sections.append(current)
    return sections


def _is_arrangement_note(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return False
    return SECTION_PATTERN.match(stripped) is None


def _lyric_lines(section: Section) -> list[str]:
    return [ln for ln in section.lines if ln.strip() and not _is_arrangement_note(ln)]


def _infer_title(
    lines: list[str],
    fields: dict[str, str],
    title_override: str | None = None,
    title_fallback: str | None = None,
) -> str:
    if title_override and title_override.strip():
        return title_override.strip()
    if fields.get("title"):
        return fields["title"].strip()
    for index, line in enumerate(lines):
        if "제목" in line and ":" in line:
            c = line.split(":", 1)[1].strip()
            if c:
                return c
        if line.strip().lower().startswith("title:"):
            return line.split(":", 1)[1].strip()
        if line.strip().startswith("["):
            break
        lowered = line.strip().lower()
        if lowered.startswith(("weirdness", "style influence")):
            continue
        if "%" in line or re.search(r"\b\d+\s*bpm\b", line, re.IGNORECASE):
            continue
        if index < 8 and line.strip() and "," not in line and len(line.strip()) <= 40:
            if not re.search(r"[가-힣]", line) and len(line.strip().split()) == 1:
                continue
            return line.strip()
    if title_fallback and title_fallback.strip():
        return title_fallback.strip()
    raise ValueError("곡 제목을 찾지 못했습니다. --title 옵션을 쓰거나 입력에 'Title:' 또는 '제목:'을 넣어 주세요.")


def parse_song(
    path: Path,
    title_override: str | None = None,
    title_fallback: str | None = None,
) -> Song:
    raw_text = read_text(path)
    lines = _strip_noise_lines(raw_text)
    fields: dict[str, str] = {}
    for line in lines:
        parsed = _parse_key_value(line.strip()) or _parse_loose_metadata(line.strip())
        if parsed:
            key, value = parsed
            fields[key] = value

    title = _infer_title(lines, fields, title_override, title_fallback)
    genre_raw = fields.get("genre", "")
    bpm = fields.get("bpm", "")
    if not bpm:
        m = re.search(r"\b(\d{2,3})\s*bpm\b", genre_raw, re.IGNORECASE)
        if m:
            bpm = f"{m.group(1)} BPM"

    return Song(
        title=title,
        genre=_clean_genre(genre_raw),
        bpm=bpm,
        mood=fields.get("mood", ""),
        emotion=fields.get("emotion", ""),
        sections=_parse_sections(lines),
        raw_text="\n".join(lines),
    )


def song_slug(title: str) -> str:
    forbidden = '<>:"/\\|?*'
    slug = "".join("_" if c in forbidden else c for c in title).strip().strip(".")
    if not slug:
        raise ValueError("폴더 이름으로 사용할 수 없는 곡 제목입니다.")
    return slug


def display_metadata(value: str, fallback: str = "미지정") -> str:
    return value.strip() or fallback


# ── 웹툰 파이프라인 로직 ─────────────────────────────────────────────────────

def detect_bpm_range(bpm_str: str) -> str:
    m = re.search(r"\b(\d{2,3})\b", bpm_str)
    if not m:
        return "medium"
    bpm = int(m.group(1))
    for key, r in _CUT_TIMING["bpm_ranges"].items():
        if r["min"] <= bpm <= r["max"]:
            return key
    return "medium"


def select_style(song: Song) -> tuple[str, dict]:
    # 부정 태그 포함 raw_text 제외 — 청소된 genre+mood+emotion만 사용
    lower = f"{song.genre} {song.mood} {song.emotion}".lower()
    bpm_range = detect_bpm_range(song.bpm)
    amap = _WEBTOON_STYLES["adaptive_style_map"]

    def _has(keywords: list[str]) -> bool:
        """단어 경계 기반 매칭 — 부분 문자열 오매칭 방지."""
        for kw in keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, lower):
                return True
        return False

    # ── 1순위: 감정/분위기 키워드 (BPM보다 우선) ──────────────────────────────
    _emotional_kw = [
        "bittersweet", "nostalgic", "melancholic", "melancholy", "longing",
        "heartbreak", "heartfelt", "wistful", "tender", "intimate",
    ]
    _soft_genre_kw = [
        "ballad", "acoustic", "folk", "lo-fi", "lofi",
        "soft pop", "indie folk", "bedroom pop",
    ]
    _dark_kw = [
        "dark pop", "gothic", "post-punk", "shoegaze", "noir",
        "dark electronic", "heavy rock", "heavy metal",
    ]
    _dance_kw = ["dance pop", "city pop", "bubblegum pop", "j-pop", "funk", "disco", "groovy"]
    _signal_kw = [
        "signal pop", "korean signal pop", "telephone pulse rhythm",
        "telephone connection tone", "ajaeng lead", "ajaeng motif",
    ]
    _aggressive_kw = ["metal", "punk", "hardcore", "heavy rock", "garage rock"]

    if _has(_signal_kw):
        energy = "medium_signal"
    elif _has(_dark_kw):
        energy = "dark_heavy"
    elif _has(_emotional_kw):
        energy = "slow_ballad" if bpm_range in ("slow", "medium") else "medium_emotional"
    elif bpm_range == "very_fast" and _has(_aggressive_kw):
        energy = "fast_aggressive"
    elif _has(_soft_genre_kw):
        energy = "slow_ballad" if bpm_range in ("slow", "medium") else "medium_emotional"
    elif _has(_dance_kw):
        energy = "medium_pop"
    # ── 2순위: BPM 기반 ──────────────────────────────────────────────────────
    elif bpm_range in ("fast", "very_fast"):
        energy = "fast_energetic"
    elif bpm_range == "slow":
        energy = "slow_acoustic"
    else:
        energy = "medium_emotional"

    style_key = amap.get(energy, _WEBTOON_STYLES["default_style"])
    if style_key not in _WEBTOON_STYLES["styles"]:
        style_key = _WEBTOON_STYLES["default_style"]
    return style_key, _WEBTOON_STYLES["styles"][style_key]


def _stable_index(seed: str, size: int) -> int:
    if size <= 0:
        raise ValueError("size must be greater than zero")
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % size


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return re.search(pattern, text) is not None


def select_performance_profile(song: Song) -> tuple[str, dict]:
    text = f"{song.genre} {song.mood} {song.emotion}".lower()
    bpm_range = detect_bpm_range(song.bpm)
    style_key, _ = select_style(song)
    candidates: list[tuple[int, str, dict]] = []

    for profile_key, profile in _BAND_PROFILES["profiles"].items():
        match = profile.get("match", {})
        score = sum(
            int(match.get("keyword_weight", 4))
            for keyword in match.get("keywords", [])
            if _contains_keyword(text, keyword)
        )
        if bpm_range in match.get("bpm_ranges", []):
            score += int(match.get("bpm_weight", 1))
        if style_key in match.get("style_keys", []):
            score += int(match.get("style_weight", 2))
        candidates.append((score, profile_key, profile))

    if not candidates:
        profile_key = _BAND_PROFILES["default_profile"]
        return profile_key, _BAND_PROFILES["profiles"][profile_key]
    best_score = max(score for score, _, _ in candidates)
    if best_score <= 0:
        fallback_keys = _BAND_PROFILES["fallback_by_style"].get(
            style_key,
            [_BAND_PROFILES["default_profile"]],
        )
        profile_key = fallback_keys[_stable_index(song.title, len(fallback_keys))]
        return profile_key, _BAND_PROFILES["profiles"][profile_key]

    best = [(key, profile) for score, key, profile in candidates if score == best_score]
    return best[_stable_index(song.title, len(best))]


def select_profile_variant(
    song: Song,
    profile_key: str,
    profile: dict,
    field: str,
    panel_num: int,
) -> str:
    values = profile.get(field, [])
    if not values:
        return ""
    seed = f"{song.title}|{profile_key}|{field}|{panel_num}"
    return values[_stable_index(seed, len(values))]


def _normalize_section_key(label: str) -> str:
    lower = re.sub(r"\s+", "_", label.lower().replace("-", "_"))
    base = re.sub(r"_?\d+$", "", lower)
    key_map = {
        "intro": "intro", "verse": "verse",
        "pre_chorus": "pre_chorus", "chorus": "chorus",
        "bridge": "bridge", "outro": "outro",
        "final_chorus": "chorus", "post_chorus": "chorus",
        "build": "pre_chorus", "drop": "chorus", "hook": "chorus",
        "solo": "instrumental", "breakdown": "bridge",
        "interlude": "instrumental", "instrumental": "instrumental",
    }
    return key_map.get(base, "instrumental")


def get_panel_timing(section_label: str, bpm_range: str) -> tuple[int, int]:
    key = _normalize_section_key(section_label)
    try:
        t = _CUT_TIMING["sections"][key][bpm_range]
        return t["panel_count"], t["seconds_per_panel"]
    except KeyError:
        return 2, 4


def get_panel_sequence(section_label: str, panel_count: int) -> list[str]:
    key = _normalize_section_key(section_label)
    sec_data = _PANEL_SEQS["sequences"].get(key, _PANEL_SEQS["sequences"]["instrumental"])
    default_seq: list[str] = sec_data.get("default", ["wide", "medium"])
    short_seq: list[str] = sec_data.get("short", [default_seq[0]])
    extended_seq: list[str] = sec_data.get("extended", default_seq * 2)

    if panel_count <= len(short_seq):
        base = short_seq
    elif panel_count <= len(default_seq):
        base = default_seq
    else:
        base = extended_seq

    return [base[i % len(base)] for i in range(panel_count)]


def find_lyric_visual(lyric_text: str) -> dict | None:
    for _cat, mappings in _LYRIC_MAP["mappings"].items():
        for _key, data in mappings.items():
            for kw in data.get("keywords", []):
                if kw in lyric_text:
                    return data
    return None


# ── 프롬프트 빌더 ─────────────────────────────────────────────────────────────

_IDENTITY_SUFFIX = (
    "Original characters only — not based on any existing IP. "
    "Do not redesign the band members. "
    "Do not change the skeleton music band identity. "
    "Do not make characters scary — keep them cute and charming. "
    "Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image."
)


def build_panel_prompt(
    song: Song,
    panel_num: int,
    panel_total: int,
    panel_type: str,
    section_label: str,
    duration: int,
    lyric_text: str,
    style_key: str,
    style: dict,
    profile_key: str,
    profile: dict,
) -> str:
    char = _CHARACTER_LOCK
    pt = _PANEL_TYPES["types"].get(panel_type, _PANEL_TYPES["types"]["wide"])

    visual = find_lyric_visual(lyric_text)
    if visual:
        lyric_scene = visual["visual_scene"]
        lyric_mood  = visual["mood"]
    else:
        fb = _LYRIC_MAP["fallback_visual"]
        lyric_scene = fb["visual_scene"]
        lyric_mood  = fb["mood"]

    lyric_display = lyric_text.strip() if lyric_text.strip() else f"Instrumental — {pt['description']}"

    art = char["art_style_anchor"]
    char_desc = (
        f"{char['identity_block']['band_description']}. "
        f"{art['base']}. "
        f"{char['identity_block']['moon']}. "
        f"{char['identity_block']['costume']}."
    )
    char_kw = f"{art['line_art']}, {art['color']}"
    niji_flags = style.get("nijijourney_flags", "--niji 7 --ar 16:9 --s 250")
    lighting = select_profile_variant(song, profile_key, profile, "lighting_variants", panel_num)
    camera = select_profile_variant(song, profile_key, profile, "camera_variants", panel_num)
    performance = select_profile_variant(
        song, profile_key, profile, "performance_variants", panel_num
    )
    audience = select_profile_variant(song, profile_key, profile, "audience_variants", panel_num)
    performance_block = (
        f"Performance archetype: {profile['stage_layout']}. "
        f"Lighting treatment: {lighting}. Camera language: {camera}. "
        f"Band movement: {performance}. Audience treatment: {audience}. "
        f"Wardrobe treatment: {profile['wardrobe_treatment']}. "
        "Use transformed concert-design attributes only; do not recreate, name, or imitate "
        "any real artist, logo, costume, face, or signature stage."
    )

    gpt = (
        f"{style['prompt_anchor']}, {char_desc} "
        f"{pt['camera']}, {pt['subject']}, {pt['composition']}. "
        f"{lyric_scene}. {performance_block} "
        f"Safe concert performance scene. {_IDENTITY_SUFFIX}"
    )

    # Nijijourney: 캐릭터 일관성을 위해 핵심 고정 블록 포함
    char_niji = (
        f"the same original fantasy skeleton cartoon band, "
        f"simple round skull, large circular hollow eye sockets with neon magenta glow, "
        f"chubby rounded body, {char['identity_block']['moon'].split(',')[0]}"
    )
    niji = (
        f"{style['prompt_anchor'].split(',')[0]}, {art['base'].split('—')[0].strip()}, "
        f"{char_niji}, "
        f"{pt['camera']}, {pt['subject'].split(',')[0]}, "
        f"{lyric_mood}, {profile['stage_layout']}, {lighting}, {camera}, {performance} "
        f"{niji_flags} --no watermark, text, letters, numbers, logo, UI overlay, realistic, scary, horror, existing cartoon characters"
    )

    flux = (
        f"A {style['name']} illustration of {char['identity_block']['band_description']}. "
        f"{art['base']}. "
        f"{pt['camera']}, showing {pt['subject']}. "
        f"The scene conveys {lyric_mood}. {lyric_scene}. {performance_block} "
        f"{char_kw}. {_IDENTITY_SUFFIX}"
    )

    gemini = (
        f"{style['name']} 스타일 일러스트레이션. "
        f"{char['identity_block']['band_description']}. "
        f"{pt['description']} — {pt['camera']}. "
        f"분위기: {lyric_mood}. {lyric_scene.split(',')[0]}. "
        f"{performance_block} "
        f"{art['line_art']}, {art['color']}. "
        "Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image. "
        "Original characters only, not based on any existing IP."
    )

    return f"""# Panel {panel_num:03d} — {section_label} / {panel_type.capitalize()}

## 타이밍
- 섹션: {section_label}
- 컷 번호: {panel_num}/{panel_total}
- 권장 지속 시간: {duration}초

## 가사 연결
{lyric_display}

## 스타일 고정
> `00_style_reference.md` 블록 전체 참조. 레퍼런스 이미지 반드시 첨부.

---

## GPT Image (gpt-image-2) — 1792x1024

```
{gpt}
```

---

## Nijijourney (--niji 7)

```
{niji}
```

---

## FLUX.1 (무료, 자연어)

```
{flux}
```

---

## Gemini / Imagen 3

```
{gemini}
```
"""


def build_style_reference(
    song: Song,
    style_key: str,
    style: dict,
    profile_key: str,
    profile: dict,
) -> str:
    char = _CHARACTER_LOCK
    bpm_range = detect_bpm_range(song.bpm)
    niji_flags = style.get("nijijourney_flags", "--niji 7 --ar 16:9 --s 250")
    members = char["identity_block"]["members"]
    negative_rules = "\n".join(char["negative_rules"])
    source_lines = "\n".join(
        f"- {source['artist']} — {source['url']}"
        for source_key in profile.get("source_refs", [])
        if (source := _BAND_PROFILES["sources"].get(source_key))
    )

    char_block = (
        f"{char['identity_block']['band_description']}.\n\n"
        f"Members:\n"
        f"- Vocalist: {members['vocalist']}\n"
        f"- Guitarist: {members['guitarist']}\n"
        f"- Bassist: {members['bassist']}\n"
        f"- Drummer: {members['drummer']}\n\n"
        f"Stage: {char['identity_block']['stage']}\n"
        f"Moon: {char['identity_block']['moon']}\n"
        f"Costume: {char['identity_block']['costume']}\n"
        f"Palette: {char['identity_block']['palette']}"
    )

    return f"""# {song.title} — 웹툰 스타일 고정 블록

> 모든 패널 프롬프트 생성 시 이 블록을 맨 앞에 붙인다.
> 스타일: **{style_key}** — {style["description"]}

---

## 캐릭터 스타일 고정

```
{style["prompt_anchor"]}
```

## 스켈레톤 밴드 정체성

```
{char_block}
```

## 곡 스타일 ({style["name"]})

- 스타일: {style_key} — {style["description"]}
- 분위기: {display_metadata(song.mood)} / 감정: {display_metadata(song.emotion)}
- BPM 구간: {bpm_range} ({song.bpm})
- 선 굵기: {style.get("line_weight", "bold outlines")}
- 색상: {style.get("color_mode", "flat bright colors")}
- 표정 연출: {style.get("expression_style", "exaggerated cartoon expressions")}
- Nijijourney: `{niji_flags}`

## Performance Direction

- Profile: `{profile_key}` — {profile["name_ko"]}
- Stage layout: {profile["stage_layout"]}
- Wardrobe range: {profile["wardrobe_treatment"]}
- Selection basis: genre, BPM, mood, and emotion; never a hardcoded song title

### Research Sources

> Real artists are research provenance only. Their names must not enter image prompts.

{source_lines}

## 금지 규칙

```
{negative_rules}
```

## 레퍼런스 이미지

> `ai-webtoon/reference/` 폴더의 기준 이미지를 반드시 첨부한다.
"""


def build_storyboard(song: Song, panels: list[dict]) -> str:
    total = len(panels)
    rows = "\n".join(
        f"| panel_{p['num']:03d} | {p['section']} | {p['type']} | {p['duration']}초 | {p['lyric_preview']} |"
        for p in panels
    )
    section_counts: dict[str, int] = {}
    for p in panels:
        section_counts[p["section"]] = section_counts.get(p["section"], 0) + 1
    section_summary = " / ".join(f"{k}({v})" for k, v in section_counts.items())

    return f"""# {song.title} — 웹툰 스토리보드

> BPM: {song.bpm} | 장르: {song.genre}
> 총 패널 수: {total}패널

---

## 섹션별 패널 계획

| 패널 번호 | 섹션 | 타입 | 지속 시간 | 가사 미리보기 |
|-----------|------|------|-----------|--------------|
{rows}

---

## 섹션 요약

{section_summary}

## 편집 가이드

- BPM 기반으로 패널 지속 시간 자동 설정됨
- 편집 도구: CapCut 또는 DaVinci Resolve (이미지 슬라이드쇼 + 음악 싱크)
- 레퍼런스 이미지: `ai-webtoon/reference/` 폴더 사용
"""


def build_overview(song: Song, panels: list[dict], errors: list[str]) -> str:
    status = "정상" if not errors else "확인 필요"
    error_lines = "\n".join(f"- {e}" for e in errors) if errors else ""
    return f"""# {song.title} 패널 설명

## 전체 MV 방향

곡: `{song.title}` | 장르: `{song.genre}` | 감정: `{display_metadata(song.emotion)}`
BPM: {song.bpm} | 분위기: {display_metadata(song.mood)}

## 패널 현황

- 총 패널 수: {len(panels)}
- 스타일 참조: `00_style_reference.md`
- 스토리보드: `01_storyboard.md`

## 검증 상태

- 상태: {status}
{error_lines}

## 웹툰 제작 흐름

1. `00_style_reference.md` — 스타일과 캐릭터 고정 블록 확인
2. `01_storyboard.md` — 전체 패널 계획 확인
3. `panels/` — 패널 파일 순서대로 이미지 생성 (레퍼런스 이미지 반드시 첨부)
4. CapCut / DaVinci Resolve — 이미지 슬라이드쇼 편집 + 음악 싱크
"""


# ── 폴더 생성 / 검증 ─────────────────────────────────────────────────────────

def has_identity_lock(text: str) -> bool:
    return any(term in text for term in IDENTITY_LOCK_TERMS)


def validate_song_folder(folder: Path) -> list[str]:
    errors: list[str] = []
    if not folder.exists():
        return [f"폴더가 없습니다: {folder}"]
    for required in [STYLE_REFERENCE_FILE, STORYBOARD_FILE]:
        if not (folder / required).exists():
            errors.append(f"누락 파일: {required}")
    panels_dir = folder / "panels"
    if not panels_dir.exists():
        errors.append("panels/ 폴더가 없습니다")
        return errors
    panel_files = sorted(panels_dir.glob("panel_*.md"))
    if not panel_files:
        errors.append("panels/ 폴더에 패널 파일이 없습니다")
        return errors
    for pf in panel_files:
        text = read_text(pf)
        if not has_identity_lock(text):
            errors.append(f"정체성 고정 문장 부족: {pf.name}")
        for term in POLICY_RISK_TERMS:
            if term in text.lower():
                errors.append(f"정책 위험 표현: {pf.name} → {term}")
    return errors


def _remove_folder(path: Path) -> None:
    for child in path.iterdir():
        if child.is_symlink():
            run_with_retries("delete", child, child.unlink)
        elif child.is_dir():
            _remove_folder(child)
        else:
            run_with_retries("delete", child, child.unlink)
    run_with_retries("rmdir", path, path.rmdir)


def create_song_folder(song: Song, output_dir: Path, force: bool = False) -> Path:
    destination = output_dir / song_slug(song.title)
    if destination.exists():
        if not force:
            raise FileExistsError(f"이미 폴더가 있습니다: {destination}. 덮어쓰려면 --force를 사용하세요.")
        _remove_folder(destination)
    destination.mkdir(parents=True, exist_ok=True)

    style_key, style = select_style(song)
    profile_key, profile = select_performance_profile(song)
    bpm_range = detect_bpm_range(song.bpm)

    # 전체 패널 계획
    panels: list[dict] = []
    panel_num = 1
    for section in song.sections:
        panel_count, duration = get_panel_timing(section.label, bpm_range)
        panel_types = get_panel_sequence(section.label, panel_count)
        lyric_full = "\n".join(_lyric_lines(section))
        lyric_ctx  = lyric_full if lyric_full else (section.note or "Instrumental")
        preview    = (lyric_ctx[:30] + "...") if len(lyric_ctx) > 30 else lyric_ctx
        preview    = preview.replace("\n", " ")

        for panel_type in panel_types:
            panels.append({
                "num": panel_num,
                "section": section.label,
                "type": panel_type,
                "duration": duration,
                "lyric_text": lyric_ctx,
                "lyric_preview": preview,
            })
            panel_num += 1

    total = len(panels)
    if total == 0:
        raise ValueError("섹션 정보가 없어 패널을 생성할 수 없습니다. 입력 파일에 [Intro], [Chorus] 등 섹션 마커가 있는지 확인하세요.")

    # 출력 파일 생성
    write_text(
        destination / STYLE_REFERENCE_FILE,
        build_style_reference(song, style_key, style, profile_key, profile),
    )
    write_text(destination / STORYBOARD_FILE, build_storyboard(song, panels))

    panels_dir = destination / "panels"
    panels_dir.mkdir(parents=True, exist_ok=True)
    for p in panels:
        sec_key   = _normalize_section_key(p["section"])
        file_name = f"panel_{p['num']:03d}_{sec_key}_{p['type']}.md"
        content   = build_panel_prompt(
            song=song,
            panel_num=p["num"], panel_total=total,
            panel_type=p["type"], section_label=p["section"],
            duration=p["duration"], lyric_text=p["lyric_text"],
            style_key=style_key, style=style,
            profile_key=profile_key, profile=profile,
        )
        write_text(panels_dir / file_name, content)

    errors = validate_song_folder(destination)
    write_text(destination / OVERVIEW_FILE, build_overview(song, panels, errors))
    return destination


def input_text_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"입력 폴더가 없습니다: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"입력 경로가 폴더가 아닙니다: {input_dir}")
    return sorted(p for p in input_dir.glob("*.txt") if p.is_file())


# ── 요약 ─────────────────────────────────────────────────────────────────────

def _summarize(input_dir: Path, output_dir: Path) -> tuple[list[dict], list[Path]]:
    rows: list[dict] = []
    written: list[Path] = []
    for input_file in input_text_files(input_dir):
        try:
            song   = parse_song(input_file, title_fallback=input_file.stem)
            folder = output_dir / song_slug(song.title)
            errors = validate_song_folder(folder)
            panels_dir = folder / "panels"
            panel_count = len(list(panels_dir.glob("panel_*.md"))) if panels_dir.exists() else 0
            rows.append({
                "title": song.title, "genre": song.genre, "emotion": song.emotion,
                "status": "PASS" if not errors else "CHECK",
                "panel_count": panel_count, "folder": folder, "errors": errors,
            })
        except Exception as exc:
            rows.append({
                "title": input_file.stem, "genre": "", "emotion": "",
                "status": "CHECK", "panel_count": 0,
                "folder": output_dir / input_file.stem, "errors": [str(exc)],
            })
    pass_count = sum(1 for r in rows if r["status"] == "PASS")
    table = "\n".join(
        f"| {r['title']} | {r['status']} | {r['panel_count']} | {r['genre'][:60]} |"
        for r in rows
    )
    overview_text = (
        f"# All Panel Overview\n\n"
        f"Input songs: {len(rows)} | Passed: {pass_count} | Check: {len(rows) - pass_count}\n\n"
        f"| Song | Status | Panels | Genre |\n| --- | --- | ---: | --- |\n{table}\n"
    )
    audit_lines = ["# Panel Audit\n"]
    for r in rows:
        if r["errors"]:
            audit_lines.append(f"## {r['title']}")
            audit_lines.extend(f"- {e}" for e in r["errors"])
            audit_lines.append("")
    if not any(r["errors"] for r in rows):
        audit_lines.append("No issues found.")

    op = output_dir / ALL_OVERVIEW_FILE
    ap = output_dir / PANEL_AUDIT_FILE
    write_text(op, overview_text)
    write_text(ap, "\n".join(audit_lines) + "\n")
    written.extend([op, ap])
    return rows, written


# ── CLI 명령 ─────────────────────────────────────────────────────────────────

def command_create(args: argparse.Namespace) -> int:
    song = parse_song(Path(args.input), args.title, title_fallback=Path(args.input).stem)
    dest = create_song_folder(song=song, output_dir=Path(args.output_dir), force=args.force)
    errors = validate_song_folder(dest)
    print(f"생성 완료: {dest}")
    if errors:
        print("검증 실패:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("검증 통과")
    return 0


def command_create_all(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir)
    files = input_text_files(input_dir)
    if not files:
        print(f"처리할 txt 파일이 없습니다: {input_dir}")
        return 1
    print(f"입력 파일 {len(files)}개 처리 시작: {input_dir}")
    failed: list[tuple[Path, str]] = []
    for index, input_file in enumerate(files, start=1):
        print(f"\n[{index}/{len(files)}] {input_file.name}")
        try:
            song = parse_song(input_file, title_fallback=input_file.stem)
            dest = create_song_folder(song=song, output_dir=Path(args.output_dir), force=args.force)
            errors = validate_song_folder(dest)
            print(f"생성 완료: {dest}")
            if errors:
                for e in errors:
                    print(f"- {e}")
                failed.append((input_file, "검증 실패"))
            else:
                print("검증 통과")
        except Exception as exc:
            print(f"오류: {exc}")
            failed.append((input_file, str(exc)))
    _summarize(input_dir, Path(args.output_dir))
    print(f"\n처리 완료: 성공 {len(files) - len(failed)}개, 실패 {len(failed)}개")
    if failed:
        for f, reason in failed:
            print(f"- {f.name}: {reason}")
        return 1
    return 0


def command_validate(args: argparse.Namespace) -> int:
    errors = validate_song_folder(Path(args.folder))
    if errors:
        print("검증 실패:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("검증 통과")
    return 0


def command_summarize_all(args: argparse.Namespace) -> int:
    rows, written = _summarize(Path(args.input_dir), Path(args.output_dir))
    failed = [r for r in rows if r["status"] != "PASS"]
    print(f"written: {len(written)} | songs: {len(rows)} | passed: {len(rows) - len(failed)} | check: {len(failed)}")
    if failed:
        for r in failed:
            print(f"- {r['title']}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="웹툰 MV 이미지 프롬프트 생성기 (영상 프롬프트 없음)")
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create", help="입력 txt로 곡별 패널 프롬프트 생성")
    c.add_argument("--input", required=True)
    c.add_argument("--title")
    c.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    c.add_argument("--force", action="store_true")
    c.set_defaults(func=command_create)

    ca = sub.add_parser("create-all", help="input 폴더의 모든 txt 처리")
    ca.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    ca.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    ca.add_argument("--force", action="store_true")
    ca.set_defaults(func=command_create_all)

    v = sub.add_parser("validate", help="생성된 폴더 검증")
    v.add_argument("--folder", required=True)
    v.set_defaults(func=command_validate)

    sa = sub.add_parser("summarize-all", help="전체 출력 폴더 요약")
    sa.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    sa.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    sa.set_defaults(func=command_summarize_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_output_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
