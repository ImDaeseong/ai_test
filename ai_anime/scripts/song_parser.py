from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any
import wave

try:
    import librosa as _librosa
    _LIBROSA_AVAILABLE = True
except ImportError:
    _LIBROSA_AVAILABLE = False

from common import (
    DEFAULT_SECTIONS,
    PROJECT_ROOT,
    ensure_directories,
    load_config,
    normalize_section_name,
    read_text,
    split_csv,
    write_json,
)

_BPM_CONFIG = load_config("bpm_thresholds")
_SECTIONS_CONFIG = load_config("song_sections")
_INFERENCE_CONFIG = load_config("song_inference")
_TAG_CONFIG = load_config("tag_classification")


KEY_ALIASES = {
    "title": "title",
    "genre": "genre",
    "bpm": "bpm",
    "mood": "mood",
    "emotion": "mood",
    "energy": "energy",
    "instruments": "instruments",
    "style": "style_tags",
    "music style tags": "style_tags",
    "style tags": "style_tags",
    "negative tags": "negative_tags",
    "visual cues": "visual_cues",
    "atmosphere": "atmosphere",
    "pacing": "pacing",
}


SECTION_LABEL_PATTERN = re.compile(
    r"^\[(?:(?:Final|Repeat|Double|Opening|Extended|Bonus)\s+)?"
    r"(Intro|Verse(?:\s*\d+)?|Pre[- ]?Chorus|Chorus(?:\s*\d+)?|Post[- ]?Chorus"
    r"|Bridge|Build(?:[- ]?[Uu]p)?|Drop|Hook|Solo|Interlude|Breakdown|Outro)"
    r"(?::\s*(.*?))?\]$",
    re.I,
)
# These section names are also used as production notes (e.g. "[Drop: Grand soundscape]"
# inside a Chorus block). Only treat them as new sections when the current section already
# has lyrics; otherwise they are instrumentation cues, not section boundaries.
_PRODUCTION_NOTE_SECTION_RE = re.compile(
    r"^(build|drop|hook|solo|interlude|breakdown)", re.I
)
TIMESTAMP_PATTERN = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,2}))?\]")
SRT_TIME_PATTERN = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
_FFMPEG_AVAILABLE: bool | None = None
NEGATIVE_PREFIXES = ("-", "‑", "–", "—")
BPM_TAG_RE = re.compile(r"^\d{2,3}\s*bpm$", re.I)
KEY_TAG_RE = re.compile(r"^(major|minor|[a-g][#b]?\s*(major|minor)?|[a-g][#b]?\s*(maj|min)?\s*key|major key|minor key)$", re.I)
ENERGY_TAGS = _TAG_CONFIG.get("energy_tags", {})
INSTRUMENT_TERMS = _TAG_CONFIG.get("instrument_terms", [])
GENRE_TERMS = _TAG_CONFIG.get("genre_terms", [])
GENRE_INSTRUMENT_EXCEPTIONS = _TAG_CONFIG.get("genre_instrument_exceptions", [])
VOCAL_TERMS = _TAG_CONFIG.get("vocal_terms", [])
MOOD_TAG_MAP = [
    (item.get("terms", []), item.get("mood", ""))
    for item in _TAG_CONFIG.get("mood_tag_map", [])
]
NON_GENRE_TERMS = _TAG_CONFIG.get("non_genre_terms", [])


def check_ffmpeg() -> bool:
    global _FFMPEG_AVAILABLE
    if _FFMPEG_AVAILABLE is not None:
        return _FFMPEG_AVAILABLE
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        _FFMPEG_AVAILABLE = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        _FFMPEG_AVAILABLE = False
        print("WARNING: ffmpeg or ffprobe not found in system PATH. Audio analysis will be skipped.")
    return _FFMPEG_AVAILABLE


def seconds_from_lrc_match(match: re.Match[str]) -> float:
    minutes, seconds, centiseconds = match.groups()
    timestamp = int(minutes) * 60 + int(seconds)
    if centiseconds:
        timestamp += int(centiseconds.ljust(2, "0")) / 100
    return round(timestamp, 2)


def seconds_from_srt_parts(parts: tuple[str, str, str, str]) -> float:
    hours, minutes, seconds, milliseconds = parts
    return round(int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000, 3)


def normalize_section_label(label: str) -> str:
    label = re.sub(r"\s*\d+$", "", label.strip())
    label = label.replace("-", " ")
    normalized = normalize_section_name(label)
    if normalized == "Post Chorus":
        return "Post-Chorus"
    return normalized


def strip_inline_timestamps(text: str) -> str:
    return TIMESTAMP_PATTERN.sub("", text).strip()


def is_section_marker(text: str) -> bool:
    return bool(SECTION_LABEL_PATTERN.match(text.strip()))


def is_bracketed_direction(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("[") and stripped.endswith("]")


def parse_lrc(text: str) -> list[dict[str, Any]]:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        matches = list(TIMESTAMP_PATTERN.finditer(line))
        if not matches:
            continue
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
            lyric = line[start:end].strip()
            if lyric:
                lines.append({"time": seconds_from_lrc_match(match), "text": lyric})
    return lines


def parse_srt(text: str) -> list[dict[str, Any]]:
    lines = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        block_lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(block_lines) < 2:
            continue
        time_index = next((i for i, line in enumerate(block_lines) if SRT_TIME_PATTERN.search(line)), None)
        if time_index is None:
            continue
        match = SRT_TIME_PATTERN.search(block_lines[time_index])
        if not match:
            continue
        start_time = seconds_from_srt_parts(match.groups()[:4])
        lyric = "\n".join(block_lines[time_index + 1 :]).strip()
        if lyric:
            lines.append({"time": start_time, "text": lyric})
    return lines


def normalize_tag(tag: str) -> str:
    return re.sub(r"\s+", " ", tag.strip().strip("'\"")).strip()


def split_style_tags(value: str) -> list[str]:
    return [normalize_tag(item) for item in re.split(r"[,;]", value) if normalize_tag(item)]


def pre_section_metadata_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("["):
            break
        if ":" in line:
            key = line.split(":", 1)[0].strip().lower()
            if key in KEY_ALIASES:
                continue
        lines.append(line)
    return lines


def style_tags_from_preamble(text: str) -> list[str]:
    tags: list[str] = []
    for line in pre_section_metadata_lines(text):
        if "," in line or ";" in line:
            tags.extend(split_style_tags(line))
        else:
            tags.append(normalize_tag(line))
    return list(dict.fromkeys(tag for tag in tags if tag))


def tag_text(tag: str) -> str:
    return normalize_tag(tag).lower().lstrip("".join(NEGATIVE_PREFIXES)).strip()


def is_negative_tag(tag: str) -> bool:
    normalized = normalize_tag(tag)
    return normalized.startswith(NEGATIVE_PREFIXES) or normalized.lower().startswith("no ")


def is_bpm_or_key_tag(tag: str) -> bool:
    normalized = tag_text(tag)
    return bool(BPM_TAG_RE.match(normalized) or KEY_TAG_RE.match(normalized))


def has_tag_term(tag: str, terms: list[str]) -> bool:
    normalized = tag_text(tag)
    return any(term in normalized for term in terms)


def classify_style_tags(tags: list[str]) -> dict[str, Any]:
    clean_tags = [normalize_tag(tag) for tag in tags if normalize_tag(tag)]
    negative_tags = [tag for tag in clean_tags if is_negative_tag(tag)]
    positive_tags = [tag for tag in clean_tags if not is_negative_tag(tag)]

    instrument_tags = []
    vocal_tags = []
    genre_tags = []
    for tag in positive_tags:
        lowered = tag_text(tag)
        genre_like = any(term in lowered for term in GENRE_TERMS)
        instrument_like = has_tag_term(tag, INSTRUMENT_TERMS)
        genre_instrument_exception = any(term in lowered for term in GENRE_INSTRUMENT_EXCEPTIONS)
        non_genre_like = any(term in lowered for term in NON_GENRE_TERMS)
        if is_bpm_or_key_tag(tag):
            continue
        if instrument_like and not genre_instrument_exception:
            instrument_tags.append(tag)
        if has_tag_term(tag, VOCAL_TERMS):
            vocal_tags.append(tag)
        if genre_like and (not non_genre_like or genre_instrument_exception) and (not instrument_like or genre_instrument_exception):
            genre_tags.append(tag)

    energy_scores = {
        level: sum(1 for tag in positive_tags if has_tag_term(tag, terms))
        for level, terms in ENERGY_TAGS.items()
    }
    energy = ""
    if energy_scores["high"] > energy_scores["low"]:
        energy = "high"
    elif energy_scores["low"] > energy_scores["high"]:
        energy = "low"

    moods: list[str] = []
    for terms, mood in MOOD_TAG_MAP:
        if any(has_tag_term(tag, terms) for tag in positive_tags) and mood not in moods:
            moods.append(mood)
    if moods and "cinematic" not in moods:
        moods.append("cinematic")

    return {
        "style_tags": positive_tags,
        "negative_tags": negative_tags,
        "genre_tags": genre_tags,
        "instruments": instrument_tags,
        "vocal_tags": vocal_tags,
        "energy": energy,
        "mood": moods,
    }


def enrich_metadata_from_style_tags(metadata: dict[str, Any], genre_was_derived: bool) -> None:
    classified = classify_style_tags(metadata.get("style_tags", []))
    metadata["style_tags"] = classified["style_tags"]
    if classified["negative_tags"]:
        metadata["negative_tags"] = list(dict.fromkeys([*metadata.get("negative_tags", []), *classified["negative_tags"]]))
    if not metadata.get("instruments") and classified["instruments"]:
        metadata["instruments"] = classified["instruments"]
    if classified["energy"] and (not metadata.get("energy") or metadata.get("energy") == "medium"):
        metadata["energy"] = classified["energy"]
    if not metadata.get("mood") and classified["mood"]:
        metadata["mood"] = classified["mood"]
    if classified["vocal_tags"]:
        metadata["vocal_style"] = classified["vocal_tags"][0]
    if genre_was_derived and classified["genre_tags"]:
        metadata["genre"] = ", ".join(classified["genre_tags"][:3])


def extract_metadata(text: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "title": "",
        "genre": "anime cinematic pop",
        "bpm": None,
        "energy": "medium",
        "mood": [],
        "instruments": [],
        "style_tags": [],
        "negative_tags": [],
        "visual_cues": [],
        "atmosphere": "",
        "pacing": "",
        "vocal_style": "",
    }
    genre_was_derived = False
    preamble_tags = style_tags_from_preamble(text)
    if preamble_tags:
        metadata["style_tags"] = preamble_tags
        preamble_text = " ".join(preamble_tags)
        bpm_match = re.search(r"(\d{2,3})\s*BPM", preamble_text, re.I)
        if bpm_match:
            metadata["bpm"] = int(bpm_match.group(1))
        if metadata["style_tags"]:
            metadata["genre"] = ", ".join(metadata["style_tags"][:3])
            genre_was_derived = True
    elif style_seed_line := find_style_seed_line(text):
        metadata["style_tags"] = split_style_tags(re.sub(r"Weirdness\s+\d+%.*", "", style_seed_line, flags=re.I))
        bpm_match = re.search(r"(\d{2,3})\s*BPM", style_seed_line, re.I)
        if bpm_match:
            metadata["bpm"] = int(bpm_match.group(1))
        if metadata["style_tags"]:
            metadata["genre"] = ", ".join(metadata["style_tags"][:3])
            genre_was_derived = True

    for raw_line in text.splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        normalized = KEY_ALIASES.get(key.strip().lower())
        if not normalized:
            continue
        value = value.strip()
        if normalized == "bpm":
            bpm_match = re.search(r"\d+", value)
            metadata[normalized] = int(bpm_match.group(0)) if bpm_match else None
        elif normalized == "genre":
            # [Style: term1, term2, ...] 포맷 처리: 브래킷과 "Style:" 접두어 제거
            clean_value = value
            style_bracket = re.match(r"^\[Style:\s*(.*?)\]$", value.strip(), re.I | re.DOTALL)
            if style_bracket:
                clean_value = style_bracket.group(1).strip()
            # 장르 텍스트에서 부정 태그(‑ 또는 -)로 시작하는 쉼표 구분 항목 제거
            # 부정 태그가 프로파일 키워드와 매칭되면 잘못된 장르 분류가 발생함
            parts = [p for p in re.split(r",\s*", clean_value)
                     if not p.lstrip().startswith(("‑", "-", "–"))]
            metadata[normalized] = ", ".join(parts)
            # Genre: 라인에 "78 BPM" 형태로 BPM이 내장된 경우 추출
            if metadata["bpm"] is None:
                bpm_match = re.search(r"(\d{2,3})\s*BPM", value, re.I)
                if bpm_match:
                    metadata["bpm"] = int(bpm_match.group(1))
        elif normalized == "style_tags":
            metadata[normalized] = split_style_tags(value)
            if normalized == "style_tags" and metadata["genre"] == "anime cinematic pop":
                genre_was_derived = True
        elif normalized in {"mood", "instruments", "negative_tags", "visual_cues"}:
            metadata[normalized] = split_csv(value)
        else:
            metadata[normalized] = value
    # Derive genre from style_tags if not explicitly set
    if metadata["genre"] == "anime cinematic pop" and metadata["style_tags"]:
        metadata["genre"] = ", ".join(metadata["style_tags"][:3])
        genre_was_derived = True
    enrich_metadata_from_style_tags(metadata, genre_was_derived)
    return metadata


def find_style_seed_line(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("["):
            continue
        if ":" in line:
            key = line.split(":", 1)[0].strip().lower()
            if key in KEY_ALIASES:
                continue
        if re.search(r"\b\d{2,3}\s*BPM\b", line, re.I) or "," in line:
            return line
    return ""


def infer_title_from_text(text: str, source_name: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.lower() == "cover of" and index + 1 < len(lines):
            return lines[index + 1]
    for line in lines:
        match = re.match(r"^(.*?)\s+artwork$", line, re.I)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return Path(source_name).stem.replace("_", " ").replace("-", " ").title()


def parse_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = strip_inline_timestamps(raw_line.strip())
        bracket_match = SECTION_LABEL_PATTERN.match(line)
        if bracket_match:
            section_name, description = bracket_match.groups()
            # Build/Drop/Hook/etc. double as production notes when no lyrics exist yet.
            if _PRODUCTION_NOTE_SECTION_RE.match(section_name) and current is not None and len(current["lyrics"]) == 0:
                continue
            if current:
                current["lyrics"] = "\n".join(current["lyrics"]).strip()
                sections.append(current)
            current = {
                "section": normalize_section_label(section_name),
                "lyrics": [],
                "description": description or "",
            }
            continue
        if current and line and not re.match(r"^\[[A-Za-z -]+:", line):
            current["lyrics"].append(line)

    if current:
        current["lyrics"] = "\n".join(current["lyrics"]).strip()
        sections.append(current)

    if sections:
        return sections

    lyric_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and ":" not in line and not line.startswith("[")
    ]
    n_sections = max(1, min(len(DEFAULT_SECTIONS), len(lyric_lines)))
    chunk_size = max(1, len(lyric_lines) // n_sections)
    inferred = []
    for index, section_name in enumerate(DEFAULT_SECTIONS[:n_sections]):
        chunk = lyric_lines[index * chunk_size : (index + 1) * chunk_size]
        if chunk:
            inferred.append({"section": section_name, "lyrics": "\n".join(chunk), "description": "inferred"})
    return inferred


def sections_from_timed_lyrics(timed_lyrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for item in timed_lyrics:
        text = item["text"].strip()
        marker = SECTION_LABEL_PATTERN.match(text)
        if marker:
            section_name, description = marker.groups()
            # Build/Drop/Hook/etc. double as production notes when no lyrics exist yet.
            if _PRODUCTION_NOTE_SECTION_RE.match(section_name) and current is not None and len(current["lyrics"]) == 0:
                continue
            if current:
                current["lyrics"] = "\n".join(current["lyrics"]).strip()
                current["end_time"] = item.get("time")
                sections.append(current)
            current = {
                "section": normalize_section_label(section_name),
                "lyrics": [],
                "description": description or "",
                "start_time": item.get("time"),
                "end_time": None,
            }
            continue
        if current and is_bracketed_direction(text):
            cue = text.strip()[1:-1].strip()
            if cue:
                current["description"] = " ".join(part for part in [current.get("description", ""), cue] if part).strip()
            continue
        if current and text and not is_bracketed_direction(text):
            current["lyrics"].append(text)
    if current:
        current["lyrics"] = "\n".join(current["lyrics"]).strip()
        sections.append(current)
    return sections


def discover_input_files(input_path: Path) -> dict[str, list[Path]]:
    if input_path.is_file():
        return {input_path.suffix.lower(): [input_path]}

    files: dict[str, list[Path]] = {".txt": [], ".lrc": [], ".srt": []}
    for suffix in AUDIO_EXTENSIONS:
        files[suffix] = []
    for path in sorted(input_path.iterdir()):
        if path.name == "song_master.json" or not path.is_file():
            continue
        if path.suffix.lower() in files:
            files[path.suffix.lower()].append(path)
    return files


def probe_audio_duration(path: Path) -> float | None:
    if not check_ffmpeg():
        return None

    if path.suffix.lower() == ".wav":
        with contextlib.suppress(Exception), wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            if rate:
                return round(frames / float(rate), 3)

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    with contextlib.suppress(Exception):
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        duration = float(result.stdout.strip())
        if duration > 0:
            return round(duration, 3)
    return None


def probe_audio_stream(path: Path) -> dict[str, Any]:
    if not check_ffmpeg():
        return {}
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,bit_rate:stream=codec_name,channels,sample_rate",
        "-of",
        "json",
        str(path),
    ]
    with contextlib.suppress(Exception):
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        data = json.loads(result.stdout or "{}")
        stream = next((item for item in data.get("streams", []) if item.get("codec_name")), {})
        duration = data.get("format", {}).get("duration")
        bit_rate = data.get("format", {}).get("bit_rate")
        return {
            "codec": stream.get("codec_name"),
            "sample_rate": int(stream["sample_rate"]) if str(stream.get("sample_rate", "")).isdigit() else None,
            "channels": stream.get("channels"),
            "bit_rate": int(bit_rate) if str(bit_rate or "").isdigit() else None,
            "duration_seconds": round(float(duration), 3) if duration else None,
        }
    return {}


def probe_audio_loudness(path: Path) -> dict[str, Any]:
    if not check_ffmpeg():
        return {}
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "NUL" if __import__("os").name == "nt" else "/dev/null",
    ]
    with contextlib.suppress(Exception):
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        output = "\n".join([result.stdout, result.stderr])
        mean_match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
        max_match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
        return {
            "mean_volume_db": float(mean_match.group(1)) if mean_match else None,
            "max_volume_db": float(max_match.group(1)) if max_match else None,
        }
    return {}


def classify_audio_energy(mean_volume_db: float | None, max_volume_db: float | None) -> str:
    if mean_volume_db is None:
        return "medium"
    audio_cfg = _BPM_CONFIG.get("audio_energy", {})
    high_cfg = audio_cfg.get("high", {})
    low_cfg = audio_cfg.get("low", {})
    if mean_volume_db >= high_cfg.get("min_mean_db", -14) or (
        max_volume_db is not None and max_volume_db >= high_cfg.get("min_max_db", -1)
    ):
        return "high"
    if mean_volume_db <= low_cfg.get("max_mean_db", -24):
        return "low"
    return "medium"


def infer_audio_pacing(duration_seconds: float | None, energy: str) -> str:
    if energy == "high":
        return "energetic cuts with stronger motion accents"
    if duration_seconds and duration_seconds >= 240:
        return "slow build with longer cinematic sections"
    if duration_seconds and duration_seconds <= 120:
        return "compact pacing with concise scene beats"
    if energy == "low":
        return "slow cinematic cuts with lingering frames"
    return "medium cinematic pacing informed by the audio reference"


def analyze_audio_with_librosa(path: Path) -> dict[str, Any]:
    """BPM과 RMS 에너지를 librosa로 직접 감지한다. ffmpeg 텍스트 파싱보다 정확하다."""
    if not _LIBROSA_AVAILABLE:
        return {}
    with contextlib.suppress(Exception):
        y, sr = _librosa.load(str(path), sr=None, mono=True, duration=60.0)
        tempo, _ = _librosa.beat.beat_track(y=y, sr=sr)
        bpm = round(float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo))
        rms = float(_librosa.feature.rms(y=y).mean())
        # RMS→에너지 레벨: 경험적 임계값
        if rms > 0.08:
            energy = "high"
        elif rms < 0.025:
            energy = "low"
        else:
            energy = "medium"
        return {"librosa_bpm": bpm, "librosa_rms": round(rms, 4), "librosa_energy": energy}
    return {}


def analyze_audio_file(path: Path) -> dict[str, Any]:
    stream_info = probe_audio_stream(path)
    loudness = probe_audio_loudness(path)
    duration = stream_info.get("duration_seconds") or probe_audio_duration(path)
    ffmpeg_energy = classify_audio_energy(loudness.get("mean_volume_db"), loudness.get("max_volume_db"))
    librosa_data = analyze_audio_with_librosa(path)

    # librosa BPM이 있으면 우선 사용 (텍스트 태그 BPM보다 정확)
    detected_bpm: int | None = librosa_data.get("librosa_bpm")
    # 에너지: ffmpeg 볼륨 데이터가 없을 때(=None)만 librosa fallback 사용
    # ffmpeg volumedetect가 성공했으면 그것이 기준 (기존 동작 유지)
    energy = ffmpeg_energy if loudness.get("mean_volume_db") is not None else (librosa_data.get("librosa_energy") or ffmpeg_energy)

    return {
        "file": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "duration_seconds": duration,
        "codec": stream_info.get("codec"),
        "sample_rate": stream_info.get("sample_rate"),
        "channels": stream_info.get("channels"),
        "bit_rate": stream_info.get("bit_rate"),
        "mean_volume_db": loudness.get("mean_volume_db"),
        "max_volume_db": loudness.get("max_volume_db"),
        "detected_bpm": detected_bpm,
        "librosa_rms": librosa_data.get("librosa_rms"),
        "energy_hint": energy,
        "pacing_hint": infer_audio_pacing(duration, energy),
    }


def audio_file_metadata(files: dict[str, list[Path]]) -> list[dict[str, Any]]:
    audio_files = [path for suffix in AUDIO_EXTENSIONS for path in files.get(suffix, [])]
    return [analyze_audio_file(path) for path in sorted(audio_files)]


def summarize_audio_analysis(audio_files: list[dict[str, Any]]) -> dict[str, Any]:
    if not audio_files:
        return {
            "available": False,
            "applied_to_generation": False,
            "note": "No audio file was provided.",
        }
    primary = audio_files[0]
    result: dict[str, Any] = {
        "available": True,
        "applied_to_generation": False,
        "primary_file": primary.get("file"),
        "duration_seconds": primary.get("duration_seconds"),
        "energy_hint": primary.get("energy_hint", "medium"),
        "pacing_hint": primary.get("pacing_hint", "medium cinematic pacing informed by the audio reference"),
        "mean_volume_db": primary.get("mean_volume_db"),
        "max_volume_db": primary.get("max_volume_db"),
        "note": "Audio analysis is stored as reference data unless apply_audio_analysis is enabled.",
    }
    if primary.get("detected_bpm") is not None:
        result["detected_bpm"] = primary["detected_bpm"]
        result["librosa_rms"] = primary.get("librosa_rms")
        result["note"] = f"librosa detected BPM {primary['detected_bpm']}. " + result["note"]
    return result


def apply_audio_analysis_to_song(song: dict[str, Any], audio_analysis: dict[str, Any]) -> None:
    if not audio_analysis.get("available"):
        return
    energy_hint = audio_analysis.get("energy_hint")
    pacing_hint = audio_analysis.get("pacing_hint")
    current_energy = (song.get("energy") or "").lower()
    if energy_hint and current_energy in {"", "medium"}:
        song["energy"] = energy_hint
    if pacing_hint:
        song["pacing"] = pacing_hint
    # librosa BPM: 태그에 BPM이 없거나 0일 때만 적용
    detected_bpm = audio_analysis.get("detected_bpm")
    if detected_bpm and not song.get("bpm"):
        song["bpm"] = detected_bpm
        song["bpm_source"] = "librosa"
    mood = song.get("mood", [])
    if "audio-informed" not in [item.lower() for item in mood]:
        song["mood"] = [*mood, "audio-informed"]
    song["audio_analysis_applied"] = True
    audio_analysis["applied_to_generation"] = True
    audio_analysis["note"] = "Audio analysis was applied to energy, pacing, and mood hints for generation."


_INFERENCE_DEFAULT = _INFERENCE_CONFIG.get("default", {})
DEFAULT_MOOD = _INFERENCE_DEFAULT.get("legacy_mood", ["melancholic", "cinematic"])
DEFAULT_VISUAL_CUES = _INFERENCE_DEFAULT.get("legacy_visual_cues", ["empty street", "rain", "silhouette"])
NEUTRAL_VISUAL_CUES = _INFERENCE_DEFAULT.get("neutral_visual_cues", ["song-specific setting", "signature prop", "expressive lighting"])


def compact_song_text(text: str, sections: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
    fields = [
        text,
        metadata.get("genre", ""),
        " ".join(metadata.get("style_tags", [])),
        " ".join(metadata.get("instruments", [])),
        metadata.get("atmosphere", ""),
    ]
    for section in sections:
        fields.extend([section.get("description", ""), section.get("lyrics", "")])
    return " ".join(fields).lower()


def has_any_term(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text for term in terms)


def is_default_list(value: list[str], default: list[str]) -> bool:
    return [item.lower() for item in value] == [item.lower() for item in default]


def match_inference_profile(text: str) -> dict[str, Any]:
    for profile in _INFERENCE_CONFIG.get("profiles", []):
        if has_any_term(text, profile.get("keys", [])):
            return profile
    return {}


def infer_mood_from_song(text: str, explicit_mood: list[str]) -> list[str]:
    if explicit_mood and not is_default_list(explicit_mood, DEFAULT_MOOD):
        return explicit_mood
    profile = match_inference_profile(text)
    if profile:
        moods = list(profile.get("mood", []))
        stress_mood = profile.get("stress_mood")
        if stress_mood and has_any_term(text, profile.get("stress_keys", [])):
            moods.append(stress_mood)
        return moods
    return explicit_mood or _INFERENCE_DEFAULT.get("neutral_mood", ["cinematic"])


def infer_visual_cues_from_song(text: str, explicit_visual_cues: list[str]) -> list[str]:
    if explicit_visual_cues and not is_default_list(explicit_visual_cues, DEFAULT_VISUAL_CUES):
        return explicit_visual_cues
    profile = match_inference_profile(text)
    if profile:
        return profile.get("visual_cues", NEUTRAL_VISUAL_CUES)
    return explicit_visual_cues or NEUTRAL_VISUAL_CUES


def choose_primary_text_file(files: dict[str, list[Path]]) -> Path | None:
    text_files = files.get(".txt", [])
    if not text_files:
        return None
    raw_song = next((path for path in text_files if path.name.lower() == "raw_song.txt"), None)
    return raw_song or text_files[0]


def build_song_master_from_input(input_path: Path, apply_audio_analysis: bool = False) -> dict[str, Any]:
    files = discover_input_files(input_path)
    primary_text_file = choose_primary_text_file(files)
    source_files = [path.name for paths in files.values() for path in paths]
    audio_files = audio_file_metadata(files)

    if primary_text_file:
        primary_text = read_text(primary_text_file)
        source_name = primary_text_file.name
    else:
        lyric_source = (files.get(".lrc") or files.get(".srt") or [None])[0]
        if lyric_source is None:
            raise FileNotFoundError(f"No .txt, .lrc, or .srt files found in {input_path}")
        primary_text = read_text(lyric_source)
        source_name = lyric_source.name

    timed_lyrics: list[dict[str, Any]] = []
    for lrc_path in files.get(".lrc", []):
        timed_lyrics.extend(parse_lrc(read_text(lrc_path)))
    if not timed_lyrics:
        for srt_path in files.get(".srt", []):
            timed_lyrics.extend(parse_srt(read_text(srt_path)))

    song_master = build_song_master(primary_text, source_name)
    if timed_lyrics:
        song_master["timed_lyrics"] = timed_lyrics
        timed_sections = sections_from_timed_lyrics(timed_lyrics)
        if timed_sections:
            # LRC rarely contains instrumental sections (e.g. Outro). Preserve any
            # TXT-parsed trailing sections that the LRC doesn't cover.
            txt_sections = song_master.get("sections", [])
            timed_names_lower = [s.get("section", "").lower() for s in timed_sections]
            for txt_sec in txt_sections:
                sec_name = txt_sec.get("name", "")
                if sec_name.lower() not in timed_names_lower:
                    timed_sections.append({
                        "section": sec_name,
                        "lyrics": txt_sec.get("lyrics", ""),
                        "description": txt_sec.get("description", ""),
                    })
            song_master["sections"] = structure_sections(timed_sections, song_master)
    song_master["source_files"] = source_files
    song_master["audio_files"] = audio_files
    song_master["audio_analysis"] = summarize_audio_analysis(audio_files)
    song_master["audio_analysis_applied"] = False
    song_master["timing_mode"] = "reference_only"
    song_master["timing_note"] = "Audio, LRC, and SRT timing data are stored as references only. Scene timing is not auto-assigned."
    first_audio_duration = next((item["duration_seconds"] for item in audio_files if item.get("duration_seconds")), None)
    if first_audio_duration:
        song_master["duration_seconds"] = first_audio_duration
        song_master["duration_source"] = "audio_file"
        if song_master.get("sections"):
            last_section = song_master["sections"][-1]
            if last_section.get("start_time") is not None and last_section.get("end_time") is None:
                last_section["end_time"] = first_audio_duration
    if any(section.get("start_time") is not None for section in song_master.get("sections", [])):
        song_master["timing_mode"] = "timed_sections"
        song_master["timing_note"] = "LRC/SRT section timing is assigned to sections; audio duration is used to close the final section when available."
    if apply_audio_analysis:
        apply_audio_analysis_to_song(song_master, song_master["audio_analysis"])
    return song_master


def infer_intensity(section: str, index: int, total: int, energy: str) -> str:
    intensity_defaults = _SECTIONS_CONFIG.get("intensity_defaults", {})
    if section == "Chorus":
        return intensity_defaults.get("Chorus", "high") if ("high" in energy.lower() or "rising" in energy.lower()) else "medium-high"
    if section in intensity_defaults:
        return intensity_defaults[section]
    if index >= total - 1:
        return _SECTIONS_CONFIG.get("final_section_intensity", "falling")
    return "medium"


def structure_sections(sections: list[dict[str, Any]], song: dict[str, Any]) -> list[dict[str, Any]]:
    visual_cues = song.get("visual_cues") or NEUTRAL_VISUAL_CUES
    structured_sections = []
    for index, section in enumerate(sections, start=1):
        structured_sections.append(
            {
                "index": index,
                "name": section["section"],
                "lyrics": section["lyrics"],
                "description": section.get("description", ""),
                "intensity": infer_intensity(section["section"], index, len(sections), song.get("energy", "medium")),
                "visual_cues": visual_cues,
                **({"start_time": section["start_time"]} if section.get("start_time") is not None else {}),
                **({"end_time": section["end_time"]} if section.get("end_time") is not None else {}),
            }
        )
    return structured_sections


def build_song_master(text: str, source_name: str) -> dict[str, Any]:
    metadata = extract_metadata(text)
    sections = parse_sections(text)
    lrc_lines = parse_lrc(text)
    title = metadata.get("title") or infer_title_from_text(text, source_name)
    inference_text = compact_song_text(text, sections, metadata)
    mood = infer_mood_from_song(inference_text, metadata.get("mood", []))
    visual_cues = infer_visual_cues_from_song(inference_text, metadata.get("visual_cues", []))

    song = {
        "title": title,
        "source_file": source_name,
        "genre": metadata["genre"],
        "bpm": metadata["bpm"],
        "energy": metadata["energy"],
        "mood": mood,
        "instruments": metadata["instruments"],
        "vocal_style": metadata.get("vocal_style", ""),
        "style_tags": metadata["style_tags"],
        "negative_tags": metadata["negative_tags"],
        "visual_cues": visual_cues,
        "atmosphere": metadata["atmosphere"] or ", ".join(mood),
        "pacing": metadata["pacing"] or infer_pacing(metadata["bpm"], metadata["energy"]),
        "sections": [],
        "timed_lyrics": lrc_lines,
    }
    song["sections"] = structure_sections(sections, song)
    return song


def infer_pacing(bpm: int | None, energy: str) -> str:
    thresholds = _BPM_CONFIG.get("thresholds", {})
    fast_bpm = thresholds.get("fast", {}).get("min_bpm", 120)
    slow_bpm = thresholds.get("slow", {}).get("max_bpm", 80)
    pacing_desc = _BPM_CONFIG.get("pacing_desc", {})
    if bpm and bpm >= fast_bpm:
        return pacing_desc.get("fast", "fast cuts with energetic camera movement")
    if bpm and bpm <= slow_bpm:
        return pacing_desc.get("slow", "slow cinematic cuts with lingering frames")
    if "rising" in energy.lower():
        return pacing_desc.get("rising", "measured pacing that expands in chorus sections")
    return pacing_desc.get("default", "medium cinematic pacing")


def run(
    input_path: Path | None = None,
    output_path: Path | None = None,
    apply_audio_analysis: bool = False,
) -> None:
    ensure_directories()
    inp = input_path or (PROJECT_ROOT / "input")
    out = output_path or (PROJECT_ROOT / "input" / "song_master.json")
    song_master = build_song_master_from_input(inp, apply_audio_analysis=apply_audio_analysis)
    write_json(out, song_master)
    print(f"Wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse raw music input into song_master.json.")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "input"), help="Input file or folder containing .txt/.lrc/.srt files.")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "input" / "song_master.json"))
    parser.add_argument("--apply-audio-analysis", action="store_true", help="Apply optional audio analysis hints to generation metadata.")
    args = parser.parse_args()

    run(
        input_path=Path(args.input),
        output_path=Path(args.output),
        apply_audio_analysis=args.apply_audio_analysis,
    )


if __name__ == "__main__":
    main()
