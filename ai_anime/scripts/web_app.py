from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import logging
import re
import shutil
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import queue

logger = logging.getLogger(__name__)

import config_learner
import emotion_engine
import image_prompt_generator
import output_docs
import song_parser
import scene_generator
import video_prompt_generator
from common import PROJECT_ROOT, clean_tags, ensure_directories, read_json, timestamp, write_text
from _web_ui import (
    load_recent_raw_text,
    page_shell,
    render_form,
    render_results,
    save_ui_state,
)

# ─── SSE progress bus ─────────────────────────────────────────────────────────
# 파이프라인 실행 중 각 단계 완료 이벤트를 SSE 클라이언트로 스트리밍한다.
_progress_queue: queue.Queue[str | None] = queue.Queue()


def _emit(msg: str) -> None:
    """파이프라인 단계 완료 메시지를 SSE 버스에 올린다."""
    _progress_queue.put(msg)


def _emit_done() -> None:
    """파이프라인 종료 신호 (None)를 버스에 올린다."""
    _progress_queue.put(None)


MAX_TEXT_UPLOAD_SIZE = 8 * 1024 * 1024
MAX_AUDIO_UPLOAD_SIZE = 200 * 1024 * 1024
LYRIC_UPLOAD_EXTENSIONS = {".lrc", ".srt"}
AUDIO_UPLOAD_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
ALLOWED_UPLOAD_EXTENSIONS = LYRIC_UPLOAD_EXTENSIONS | AUDIO_UPLOAD_EXTENSIONS

# [A] Serialize pipeline runs — shared files + module-level globals in scene_generator
_generate_lock = threading.Lock()


# ─── Multipart form parser (replaces deprecated cgi.FieldStorage) ────────────

class _Field:
    __slots__ = ("name", "filename", "file", "_data")

    def __init__(self, name: str, data: bytes, filename: str | None = None) -> None:
        self.name = name
        self.filename = filename
        self._data = data
        self.file = io.BytesIO(data)

    def getvalue(self) -> str:
        return self._data.decode("utf-8", errors="replace")


class _Form:
    def __init__(self, fields: dict[str, list[_Field]]) -> None:
        self._fields = fields

    def getfirst(self, name: str, default: str | None = None) -> str | None:
        bucket = self._fields.get(name)
        return bucket[0].getvalue() if bucket else default

    def __contains__(self, name: str) -> bool:
        return name in self._fields

    def __getitem__(self, name: str) -> "_Field | list[_Field]":
        bucket = self._fields[name]
        return bucket[0] if len(bucket) == 1 else bucket


def _parse_form(fp: Any, headers: Any) -> _Form:
    content_type: str = headers.get("Content-Type", "")
    content_length = int(headers.get("Content-Length", "0") or "0")
    max_body = MAX_TEXT_UPLOAD_SIZE + MAX_AUDIO_UPLOAD_SIZE + 65536
    body = fp.read(min(content_length, max_body))

    boundary: bytes | None = None
    for token in content_type.split(";"):
        token = token.strip()
        if token.lower().startswith("boundary="):
            boundary = token[9:].strip('"').encode("latin-1")
            break

    if not boundary:
        parsed = urllib.parse.parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
        return _Form({k: [_Field(k, v.encode("utf-8")) for v in vals] for k, vals in parsed.items()})

    fields: dict[str, list[_Field]] = {}
    delimiter = b"--" + boundary
    for part in body.split(delimiter)[1:]:
        if part[:2] == b"--":
            break
        if part[:2] in (b"\r\n", b"\n\r", b"\n "):
            part = part[2:] if part[:2] == b"\r\n" else part[1:]
        sep = b"\r\n\r\n" if b"\r\n\r\n" in part else b"\n\n"
        header_bytes, _, content = part.partition(sep)
        content = content.rstrip(b"\r\n")

        name: str | None = None
        filename: str | None = None
        for line in header_bytes.decode("utf-8", errors="replace").splitlines():
            if "content-disposition" in line.lower():
                for seg in line.split(";"):
                    seg = seg.strip()
                    if seg.lower().startswith("name="):
                        name = seg[5:].strip('"')
                    elif seg.lower().startswith("filename="):
                        filename = seg[9:].strip('"')
        if name is None:
            continue
        fields.setdefault(name, []).append(_Field(name, content, filename or None))

    return _Form(fields)


# ─── Song pattern analysis & Suno import ────────────────────────────────────

_BPM_RE          = re.compile(r"(\d{2,3})\s*bpm", re.I)
_NON_GENRE_RE    = re.compile(r"^\d+\s*bpm$|^\d+/\d+$|^\d{1,2}$|^[a-g]#?\s*(major|minor|maj|min)$", re.I)
# split_csv가 /로도 분리하므로 파서 넘기기 전에 태그 문자열에서 미리 제거
_STRIP_TAG_RE    = re.compile(r"\b\d{2,3}\s*bpm\b|\b\d+/\d+\b|\b[a-g]#?\s*(?:major|minor|maj|min)\b", re.I)


def analyze_song_patterns(title: str, tags: str, lyrics: str) -> dict[str, Any]:
    """Extract structured patterns from raw song data (tags + lyrics)."""
    # 태그 감싼 따옴표 제거 (Suno가 'tag...' 형태로 저장하는 경우)
    tags = tags.strip("'\"").strip()

    # 가사 정규화: literal \n → 실제 줄바꿈, Suno 내부 ID 접두사 제거
    lyrics = lyrics.replace("\\n", "\n")
    if lyrics and "[" in lyrics:
        first_bracket = lyrics.index("[")
        if first_bracket > 0:
            lyrics = lyrics[first_bracket:]

    # BPM: 태그 문자열에서 직접 추출 (parser가 key:value 라인을 우선하기 때문)
    bpm: int | None = None
    m = _BPM_RE.search(tags)
    if m:
        bpm = int(m.group(1))

    # 파서에 넘기기 전 태그에서 BPM/박자/조성 토큰 제거 (split_csv가 /로도 분리하므로 미리 처리)
    tags_for_parser = re.sub(r",\s*,", ",", _STRIP_TAG_RE.sub("", tags)).strip(", ")

    parts: list[str] = []
    if title:
        parts.append(f"Title: {title}")
    if bpm:
        parts.append(f"BPM: {bpm}")
    if tags_for_parser:
        parts.append(f"Music style tags: {tags_for_parser}")
    if lyrics:
        parts.append(lyrics)
    synthetic = "\n".join(parts)

    metadata = song_parser.extract_metadata(synthetic)
    sections  = song_parser.parse_sections(synthetic) if lyrics.strip() else []

    # BPM/박자/조성 등 비장르 항목 제거 후 장르 정제
    clean_tags_list = [t for t in metadata.get("style_tags", []) if not _NON_GENRE_RE.match(t.strip())]
    genre = ", ".join(clean_tags_list[:3]) if clean_tags_list else metadata.get("genre", "")

    vocal_keywords = ["female vocals", "male vocals", "female vocal", "male vocal",
                      "rap", "choir", "a cappella", "instrumental"]
    tag_lower = tags.lower()
    vocal_style = next((k for k in vocal_keywords if k in tag_lower), "")

    return {
        "genre":             genre,
        "bpm":               bpm or metadata.get("bpm"),
        "mood":              metadata.get("mood", []),
        "energy":            metadata.get("energy", ""),
        "instruments":       metadata.get("instruments", []),
        "style_tags":        clean_tags_list,
        "vocal_style":       vocal_style,
        "section_structure": [s["section"] for s in sections],
        "section_count":     len(sections),
    }


def _audio_file_hash(path: Path) -> str:
    """SHA256 of audio file bytes — stable unique ID for local MP3/WAV uploads."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_to_suno_history(url: str, data: dict[str, Any], audio_path: Path | None = None) -> None:
    history_dir = PROJECT_ROOT / "data"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "suno_history.jsonl"

    title   = data.get("title", "")
    tags    = data.get("tags", "")
    lyrics  = data.get("lyrics", "")
    cleaned_tags = clean_tags(tags)
    patterns = analyze_song_patterns(title, tags, lyrics)

    log_entry = {
        "timestamp":      timestamp(),
        "source":         "suno_import",
        "url":            url,
        "title":          title,
        "raw_tags":       tags,
        "cleaned_tags":   cleaned_tags,
        "lyrics_len":     len(lyrics),
        "lyrics_preview": (lyrics[:100] + "...") if lyrics else "",
        "patterns":       patterns,
    }
    if audio_path and audio_path.exists():
        log_entry["audio_hash"] = _audio_file_hash(audio_path)

    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def fetch_suno_metadata(url: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode("utf-8", errors="replace")

        # Robust extraction logic
        def clean_val(val):
            if not val: return ""
            try:
                # Handle unicode escape (ሴ)
                val = val.encode('utf-8').decode('unicode-escape')
                # Handle double-encoding mojibake
                if any(ord(c) > 127 for c in val):
                    try: val = val.encode('latin1').decode('utf-8')
                    except Exception as e: logger.debug("latin1 decode skipped: %s", e)
            except Exception as e: logger.debug("unicode-escape decode skipped: %s", e)
            return val.replace('\\n', '\n').replace('\\"', '"')

        def extract_json_field(field_name, text):
            patterns = [
                rf'"{field_name}":"(.*?)"',
                rf'\\"{field_name}\\":\\"(.*?)\\"',
                rf'\\\\"{field_name}\\\\":\\\\"(.*?)\\\\"'
            ]
            for p in patterns:
                m = re.search(p, text)
                if m: return clean_val(m.group(1))
            return ""

        # 1. Try to get chunks from self.__next_f.push
        chunks = []
        matches = re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html_content)
        for m in matches:
            chunks.append(m.group(1).replace('\\"', '"').replace('\\\\', '\\'))

        # 2. Extract basic info
        title = extract_json_field("title", html_content)
        tags = extract_json_field("tags", html_content) or extract_json_field("display_tags", html_content)

        # 3. Extract lyrics (can be in a field or a raw chunk)
        lyrics = extract_json_field("lyrics", html_content) or extract_json_field("prompt", html_content)

        if not lyrics or len(lyrics) < 20:
            for chunk in chunks:
                if "[Intro]" in chunk or "[Verse" in chunk or "[Chorus]" in chunk:
                    clean_chunk = chunk
                    if clean_chunk.startswith("49:["):
                        try:
                            text_match = re.search(r'\["(.*?)",', clean_chunk)
                            if text_match: clean_chunk = text_match.group(1)
                        except Exception as e: logger.debug("chunk parse skipped: %s", e)

                    if len(clean_chunk) > len(lyrics):
                        lyrics = clean_chunk

        if lyrics or tags:
            cleaned = clean_tags(tags)
            data = {
                "title": html.unescape(title),
                "lyrics": html.unescape(lyrics),
                "tags": ", ".join(cleaned),
                "analysis": {
                    "tag_count": len(cleaned),
                    "lyrics_chars": len(lyrics),
                    "top_tags": cleaned[:5]
                }
            }
            save_to_suno_history(url, data)
            return data

        return {"error": "데이터를 찾을 수 없습니다. 공개된 곡인지 확인해 주세요."}
    except Exception as e:
        return {"error": str(e)}


def backfill_history_patterns() -> int:
    """모든 이력 항목에 최신 패턴 분석 재적용 + 복합 키 기준 중복 제거."""
    history_file = PROJECT_ROOT / "data" / "suno_history.jsonl"
    if not history_file.exists():
        return 0

    lines = [l for l in history_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    updated = 0
    seen: dict[str, dict] = {}  # composite_key → entry (가장 최근 항목 유지)

    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not entry.get("source"):
            entry["source"] = "suno_import"

        if entry.get("source") == "generate_storyboard":
            # song_master.json 완전 처리 결과를 그대로 보존 (덮어쓰지 않음)
            pass
        else:
            # suno_import: 최신 로직으로 패턴 재분석
            raw_tags = entry.get("raw_tags") or entry.get("tags") or ""
            title    = entry.get("title") or ""
            preview  = entry.get("lyrics_preview") or entry.get("lyrics") or ""
            patterns = analyze_song_patterns(title, raw_tags, preview)
            patterns["section_structure"] = []
            patterns["section_count"]     = 0
            entry["patterns"] = patterns
            updated += 1

        key = config_learner.composite_key(entry)
        ts  = entry.get("timestamp", "")
        if key not in seen or ts > seen[key].get("timestamp", ""):
            seen[key] = entry

    new_lines = [json.dumps(e, ensure_ascii=False) for e in seen.values()]
    history_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return updated


def _is_same_song(entry: dict[str, Any], title: str, bpm: int | None, tags: list[str]) -> bool:
    """제목 + BPM 또는 태그 유사도로 동일 곡 여부 판단.

    - 제목은 필수 조건 (대소문자·공백 무시 완전 일치)
    - 제목 일치 후 BPM(±5) 또는 태그(공통 2개 이상) 중 1개 이상 확인 신호 필요
    - BPM·태그 모두 없으면 데이터 부족으로 False (제목만으로는 불충분)
    """
    if entry.get("title", "").strip().lower() != title:
        return False

    confirm = 0

    # BPM: 양쪽 모두 값이 있을 때만 신호로 사용
    entry_bpm = entry.get("patterns", {}).get("bpm")
    if bpm and entry_bpm and abs(int(bpm) - int(entry_bpm)) <= 5:
        confirm += 1

    # 태그 유사도
    entry_tags = {t.strip().lower() for t in (entry.get("cleaned_tags") or []) if len(t.strip()) > 2}
    new_tags   = {t.strip().lower() for t in tags if len(t.strip()) > 2}
    if len(entry_tags & new_tags) >= 2:
        confirm += 1

    return confirm >= 1


def save_generate_to_history(song: dict[str, Any], audio_path: Path | None = None) -> None:
    """Generate Storyboard 실행 시 song_master 분석 결과를 이력에 저장."""
    history_dir = PROJECT_ROOT / "data"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "suno_history.jsonl"

    sections = song.get("sections", [])
    style_tags = song.get("style_tags", [])

    # MP3가 있으면 해시 먼저 계산 — 이후 URL 연결 판단에 사용
    audio_hash = _audio_file_hash(audio_path) if (audio_path and audio_path.exists()) else ""

    # 제목+BPM+태그 유사도로 동일 곡의 suno_import 항목을 찾아 URL 인계
    inherited_url = ""
    if history_file.exists():
        with open(history_file, encoding="utf-8") as f:
            existing = [json.loads(line) for line in f if line.strip()]
        song_title = song.get("title", "").strip().lower()
        song_bpm   = song.get("bpm")
        for entry in reversed(existing):
            if (entry.get("source") == "suno_import"
                    and entry.get("url")
                    and not entry.get("audio_hash")
                    and _is_same_song(entry, song_title, song_bpm, style_tags)):
                inherited_url = entry["url"]
                break

    log_entry = {
        "timestamp":      timestamp(),
        "source":         "generate_storyboard",
        "url":            inherited_url,
        "title":          song.get("title", ""),
        "raw_tags":       ", ".join(style_tags),
        "cleaned_tags":   style_tags,
        "lyrics_len":     sum(len(s.get("lyrics", "")) for s in sections),
        "lyrics_preview": sections[0].get("lyrics", "")[:100] if sections else "",
        "patterns": {
            "genre":             song.get("genre", ""),
            "bpm":               song.get("bpm"),
            "mood":              song.get("mood", []),
            "energy":            song.get("energy", ""),
            "instruments":       song.get("instruments", []),
            "style_tags":        style_tags,
            "vocal_style":       next(
                (k for k in ["female vocals", "male vocals", "rap", "choir"]
                 if any(k in t.lower() for t in style_tags)), ""
            ),
            "section_structure": [s.get("name", "") for s in sections],
            "section_count":     len(sections),
        },
    }
    if audio_hash:
        log_entry["audio_hash"] = audio_hash

    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def safe_folder_name(title: str) -> str:
    """Remove Windows-forbidden path characters from song title."""
    name = re.sub(r'[\\/:*?"<>|]', "_", title.strip())
    return name or "untitled"


def save_prompts_to_song_dir(song_title: str) -> Path:
    """Copy generated prompts into output/<song_title>/ and return the folder."""
    out_dir = PROJECT_ROOT / "output" / safe_folder_name(song_title)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    char_ref = PROJECT_ROOT / "character" / "character_reference_prompt.md"
    if char_ref.exists():
        shutil.copy2(char_ref, out_dir / "character_reference_prompt.md")

    img_src = PROJECT_ROOT / "prompts" / "image_prompts"
    if img_src.exists():
        shutil.copytree(img_src, out_dir / "image_prompts", dirs_exist_ok=True)

    vid_src = PROJECT_ROOT / "prompts" / "video_prompts"
    if vid_src.exists():
        shutil.copytree(vid_src, out_dir / "video_prompts", dirs_exist_ok=True)

    clip_src = PROJECT_ROOT / "prompts" / "video_clip_prompts"
    if clip_src.exists():
        shutil.copytree(clip_src, out_dir / "video_clip_prompts", dirs_exist_ok=True)

    output_docs.write_output_docs(out_dir)
    output_docs.write_output_root_guide(PROJECT_ROOT / "output")
    return out_dir


def safe_filename(value: str, fallback: str) -> str:
    name = Path(value or fallback).name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS and fallback != "raw_song.txt":
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise ValueError(f"Only these upload types are allowed ({allowed}): {name}")
    return name or fallback


def write_upload(field: _Field, target_dir: Path, fallback_name: str, max_size: int = MAX_TEXT_UPLOAD_SIZE) -> Path | None:
    if not getattr(field, "filename", ""):
        return None
    filename = safe_filename(field.filename, fallback_name)
    target = target_dir / filename
    data = field.file.read(max_size + 1)
    if len(data) > max_size:
        raise ValueError(f"Upload is too large: {filename}")
    target.write_bytes(data)
    return target


def generate_from_form(form: _Form) -> Path:
    try:
        with _generate_lock:
            return _generate_from_form_locked(form)
    finally:
        _emit_done()


def _generate_from_form_locked(form: _Form) -> Path:
    ensure_directories()
    run_input_dir = PROJECT_ROOT / "output" / "web_inputs" / timestamp()
    run_input_dir.mkdir(parents=True, exist_ok=False)

    lyrics_raw = form.getfirst("lyrics", "").replace("\r\n", "\n").replace("\r", "\n").strip()
    title = form.getfirst("title", "").strip()
    style_id = form.getfirst("style_id", "").strip()
    apply_audio_analysis = bool(form.getfirst("apply_audio_analysis"))
    if not lyrics_raw:
        raise ValueError("가사 또는 메타 정보를 입력해 주세요.")
    lyrics_for_pipeline = f"Title: {title}\n{lyrics_raw}" if title else lyrics_raw

    save_ui_state({"apply_audio_analysis": apply_audio_analysis, "style_id": style_id})
    raw_path = run_input_dir / "raw_song.txt"
    write_text(raw_path, lyrics_for_pipeline)
    write_text(PROJECT_ROOT / "input" / "raw_song.txt", lyrics_raw)

    for field_name, fallback in [("lrc_file", "lyrics.lrc"), ("srt_file", "lyrics.srt")]:
        field = form[field_name] if field_name in form else None
        if isinstance(field, list):
            for item in field:
                write_upload(item, run_input_dir, fallback)
        elif field is not None:
            write_upload(field, run_input_dir, fallback)

    audio_uploads: list[Path] = []
    audio_field = form["audio_file"] if "audio_file" in form else None
    if isinstance(audio_field, list):
        for item in audio_field:
            uploaded = write_upload(item, run_input_dir, "music.mp3", MAX_AUDIO_UPLOAD_SIZE)
            if uploaded:
                audio_uploads.append(uploaded)
    elif audio_field is not None:
        uploaded = write_upload(audio_field, run_input_dir, "music.mp3", MAX_AUDIO_UPLOAD_SIZE)
        if uploaded:
            audio_uploads.append(uploaded)

    _emit("1/5 곡 파싱 중…")
    song_parser.run(
        input_path=run_input_dir,
        output_path=PROJECT_ROOT / "input" / "song_master.json",
        apply_audio_analysis=apply_audio_analysis,
    )
    _emit("2/5 감정 분석 중…")
    emotion_engine.run()
    _emit("3/5 씬 생성 중…")
    scene_generator.run(style_id=style_id or None)
    _emit("4/5 이미지 프롬프트 생성 중…")
    image_prompt_generator.run()
    _emit("5/5 영상 프롬프트 생성 중…")
    video_prompt_generator.run()

    song = read_json(PROJECT_ROOT / "input" / "song_master.json")
    save_generate_to_history(song, audio_path=audio_uploads[0] if audio_uploads else None)
    song_dir = save_prompts_to_song_dir(song["title"])
    if audio_uploads:
        audio_dst_dir = song_dir / "audio"
        audio_dst_dir.mkdir(parents=True, exist_ok=True)
        for audio_path in audio_uploads:
            shutil.copy2(audio_path, audio_dst_dir / audio_path.name)
    return song_dir


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_home()
        elif parsed.path == "/results":
            self.send_results()
        elif parsed.path == "/api/import_suno":
            self.handle_import_suno(parsed.query)
        elif parsed.path == "/api/config_learn":
            self.handle_config_learn(dry_run=True)
        elif parsed.path == "/api/song_master":
            self.send_json_file(PROJECT_ROOT / "input" / "song_master.json")
        elif parsed.path == "/api/story_arc":
            self.send_json_file(PROJECT_ROOT / "storyboard" / "story_arc.json")
        elif parsed.path == "/api/scene_list":
            self.send_json_file(PROJECT_ROOT / "storyboard" / "scene_list.json")
        elif parsed.path == "/api/progress":
            self.handle_sse_progress()
        elif parsed.path == "/character-reference":
            self.send_text_file(PROJECT_ROOT / "character" / "character_reference_prompt.md")
        elif parsed.path == "/story-summary":
            self.send_text_file(PROJECT_ROOT / "storyboard" / "story_summary.md")
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/config_learn":
            self.handle_config_learn(dry_run=False)
            return
        if self.path != "/generate":
            self.send_error(404)
            return
        try:
            form = _parse_form(self.rfile, self.headers)
            snapshot_dir = generate_from_form(form)
            content = render_results()
            self.send_html(page_shell(content, f"생성이 완료되었습니다. 스냅샷: {snapshot_dir}"))
        except Exception as exc:
            self.send_html(page_shell(render_form(load_recent_raw_text()), f"오류: {exc}"), status=500)

    def handle_sse_progress(self) -> None:
        """Server-Sent Events 스트림 — 파이프라인 진행률을 실시간으로 전달한다."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            while True:
                try:
                    msg = _progress_queue.get(timeout=30)
                except queue.Empty:
                    # keepalive comment
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                if msg is None:
                    self.wfile.write(b"event: done\ndata: done\n\n")
                    self.wfile.flush()
                    break
                payload = json.dumps({"message": msg}, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def handle_config_learn(self, dry_run: bool) -> None:
        try:
            report = config_learner.run(dry_run=dry_run)
        except Exception as exc:
            report = {"status": "error", "reason": str(exc)}
        self._send_json(report)

    def handle_import_suno(self, query_str: str) -> None:
        query = urllib.parse.parse_qs(query_str)
        url = query.get("url", [""])[0]
        data = {"error": "No URL provided"} if not url else fetch_suno_metadata(url)
        self._send_json(data)

    def send_home(self) -> None:
        self.send_html(page_shell(render_form(load_recent_raw_text())))

    def send_results(self) -> None:
        self.send_html(page_shell(render_results()))

    def send_html(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json_file(self, path: Path) -> None:
        if not path.exists():
            self.send_error(404)
            return
        body = json.dumps(read_json(path), ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text_file(self, path: Path) -> None:
        if not path.exists():
            self.send_error(404)
            return
        content = path.read_text(encoding="utf-8", errors="replace")
        body = page_shell(f"<section class=\"panel\"><pre>{html.escape(content)}</pre></section>")
        self.send_html(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="Run the local web UI for the AI anime MV pipeline.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    ensure_directories()
    server = ThreadingHTTPServer((args.host, args.port), WebHandler)
    print(f"Web UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
