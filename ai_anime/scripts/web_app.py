from __future__ import annotations

import argparse
import html
import json
import shutil
import urllib.parse
from cgi import FieldStorage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import emotion_engine
import image_prompt_generator
import song_parser
import scene_generator
import video_prompt_generator
from common import PROJECT_ROOT, ensure_directories, read_json, slugify, timestamp, write_text
from run_pipeline import snapshot_outputs


MAX_TEXT_UPLOAD_SIZE = 8 * 1024 * 1024
MAX_AUDIO_UPLOAD_SIZE = 200 * 1024 * 1024
LYRIC_UPLOAD_EXTENSIONS = {".lrc", ".srt"}
AUDIO_UPLOAD_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
ALLOWED_UPLOAD_EXTENSIONS = LYRIC_UPLOAD_EXTENSIONS | AUDIO_UPLOAD_EXTENSIONS


def page_shell(content: str, status: str = "") -> bytes:
    status_html = f"<p class=\"status\">{html.escape(status)}</p>" if status else ""
    document = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Anime MV Builder</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1d2430;
      --muted: #687386;
      --line: #d8dee8;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --ink: #111827;
      --soft: #eaf4f2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      letter-spacing: 0;
    }}
    header {{
      background: var(--ink);
      color: white;
      padding: 22px 28px;
      border-bottom: 4px solid var(--accent);
    }}
    header h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 700;
    }}
    header p {{
      margin: 6px 0 0;
      color: #cfd8e3;
      font-size: 14px;
    }}
    main {{
      width: min(1280px, calc(100% - 32px));
      margin: 24px auto 48px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    section, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .form-panel {{ padding: 18px; }}
    label {{
      display: block;
      margin: 14px 0 7px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }}
    input[type="text"], textarea {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
      color: var(--text);
      font: inherit;
      font-size: 14px;
      padding: 10px 11px;
    }}
    textarea {{
      min-height: 360px;
      resize: vertical;
      line-height: 1.5;
      white-space: pre-wrap;
    }}
    input[type="file"] {{
      width: 100%;
      border: 1px dashed #9aa8ba;
      border-radius: 6px;
      padding: 12px;
      background: #fbfcfe;
      color: var(--muted);
    }}
    .check-row {{
      display: flex;
      align-items: center;
      gap: 9px;
      margin-top: 12px;
      color: var(--text);
      font-size: 13px;
      font-weight: 650;
    }}
    .check-row input {{
      width: 16px;
      height: 16px;
      accent-color: var(--accent);
    }}
    .actions {{
      display: flex;
      gap: 10px;
      margin-top: 16px;
      flex-wrap: wrap;
    }}
    button, .button {{
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      font-weight: 700;
      padding: 10px 14px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
    }}
    button:hover, .button:hover {{ background: var(--accent-strong); }}
    .button.secondary {{
      background: #eef2f7;
      color: var(--text);
      border: 1px solid var(--line);
    }}
    .status {{
      margin: 0 0 16px;
      padding: 12px 14px;
      border-radius: 6px;
      background: var(--soft);
      border: 1px solid #b8ddd7;
      color: #164e49;
      font-weight: 650;
    }}
    .results {{
      display: grid;
      gap: 14px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      padding: 14px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #fbfcfe;
    }}
    .metric b {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 5px;
    }}
    .metric span {{
      font-size: 18px;
      font-weight: 750;
      word-break: break-word;
    }}
    .scene {{
      padding: 14px;
      border-top: 1px solid var(--line);
    }}
    .story {{
      padding: 16px;
    }}
    .story h2 {{
      margin: 0 0 10px;
      font-size: 19px;
    }}
    .story p {{
      margin: 8px 0;
      line-height: 1.65;
      color: #2f3a4b;
    }}
    .scene:first-child {{ border-top: 0; }}
    .scene h3 {{
      margin: 0 0 8px;
      font-size: 17px;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }}
    .chip {{
      background: #eef2f7;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      color: #425066;
      font-size: 12px;
      font-weight: 650;
    }}
    details {{
      margin-top: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
    }}
    summary {{
      cursor: pointer;
      padding: 9px 11px;
      font-weight: 700;
      color: #2f3a4b;
    }}
    pre {{
      margin: 0;
      padding: 0 11px 11px;
      white-space: pre-wrap;
      word-break: break-word;
      color: #263142;
      font: 13px/1.45 Consolas, "Courier New", monospace;
    }}
    .empty {{
      padding: 28px;
      color: var(--muted);
      text-align: center;
    }}
    @media (max-width: 900px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .summary {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>AI Anime MV Builder</h1>
    <p>가사를 입력하고 필요하면 LRC/SRT와 음악 파일을 선택 첨부하면 storyboard, 이미지 프롬프트, 비디오 프롬프트를 생성합니다.</p>
  </header>
  <main>
    {status_html}
    {content}
  </main>
</body>
</html>"""
    return document.encode("utf-8")


def render_form(sample_text: str = "") -> str:
    return f"""
<div class="layout">
  <section class="form-panel">
    <form method="post" action="/generate" enctype="multipart/form-data">
      <label for="title">제목</label>
      <input id="title" name="title" type="text" placeholder="비워두면 입력 파일명 기준으로 생성">

      <label for="lyrics">가사 / 스타일 / 메타 정보</label>
      <textarea id="lyrics" name="lyrics" placeholder="Genre:, BPM:, Mood: 같은 메타 정보와 [Intro], [Verse], [Chorus] 섹션 가사를 입력하세요.">{html.escape(sample_text)}</textarea>

      <label for="lrc_file">LRC 파일 첨부 (선택)</label>
      <input id="lrc_file" name="lrc_file" type="file" accept=".lrc">

      <label for="srt_file">SRT 파일 첨부 (선택)</label>
      <input id="srt_file" name="srt_file" type="file" accept=".srt">

      <label for="audio_file">음악 파일 첨부 (선택, mp3/wav 가능)</label>
      <input id="audio_file" name="audio_file" type="file" accept=".mp3,.wav,.m4a,.aac,.flac,.ogg">
      <label class="check-row" for="apply_audio_analysis">
        <input id="apply_audio_analysis" name="apply_audio_analysis" type="checkbox" value="1">
        오디오 분석 결과를 생성에 반영
      </label>

      <div class="actions">
        <button type="submit">생성 실행</button>
        <a class="button secondary" href="/results">최근 결과 보기</a>
      </div>
    </form>
  </section>
  <section class="panel">
    <div class="empty">아직 표시할 결과가 없습니다. 왼쪽에서 입력 후 생성 실행을 누르세요.</div>
  </section>
</div>
"""


def render_results() -> str:
    song_path = PROJECT_ROOT / "input" / "song_master.json"
    scene_path = PROJECT_ROOT / "storyboard" / "scene_list.json"
    if not song_path.exists() or not scene_path.exists():
        return render_form()

    song = read_json(song_path)
    scene_list = read_json(scene_path)
    scenes = scene_list.get("scenes", [])
    story_arc = scene_list.get("story_arc", {})
    character_model_sheet = scene_list.get("character_model_sheet", {})
    world = scene_list.get("visual_world", {})
    source_files = song.get("source_files") or [song.get("source_file", "")]
    audio_files = song.get("audio_files", [])
    audio_analysis_checked = " checked" if load_ui_state().get("apply_audio_analysis") else ""
    scene_cards = "\n".join(render_scene(scene) for scene in scenes)

    return f"""
<div class="layout">
  <section class="form-panel">
    <form method="post" action="/generate" enctype="multipart/form-data">
      <label for="title">제목</label>
      <input id="title" name="title" type="text" value="{html.escape(song.get("title", ""))}">

      <label for="lyrics">가사 / 스타일 / 메타 정보</label>
      <textarea id="lyrics" name="lyrics">{html.escape(load_recent_raw_text())}</textarea>

      <label for="lrc_file">LRC 파일 첨부 (선택)</label>
      <input id="lrc_file" name="lrc_file" type="file" accept=".lrc">

      <label for="srt_file">SRT 파일 첨부 (선택)</label>
      <input id="srt_file" name="srt_file" type="file" accept=".srt">

      <label for="audio_file">음악 파일 첨부 (선택, mp3/wav 가능)</label>
      <input id="audio_file" name="audio_file" type="file" accept=".mp3,.wav,.m4a,.aac,.flac,.ogg">
      <label class="check-row" for="apply_audio_analysis">
        <input id="apply_audio_analysis" name="apply_audio_analysis" type="checkbox" value="1"{audio_analysis_checked}>
        오디오 분석 결과를 생성에 반영
      </label>

      <div class="actions">
        <button type="submit">다시 생성</button>
        <a class="button secondary" href="/api/song_master" target="_blank">song_master.json</a>
        <a class="button secondary" href="/api/story_arc" target="_blank">story_arc.json</a>
        <a class="button secondary" href="/api/scene_list" target="_blank">scene_list.json</a>
        <a class="button secondary" href="/character-reference" target="_blank">캐릭터 기준 프롬프트</a>
        <a class="button secondary" href="/story-summary" target="_blank">전체 스토리</a>
      </div>
    </form>
  </section>
  <div class="results">
    <section class="panel summary">
      <div class="metric"><b>제목</b><span>{html.escape(song.get("title", "Untitled"))}</span></div>
      <div class="metric"><b>BPM</b><span>{html.escape(str(song.get("bpm") or "-"))}</span></div>
      <div class="metric"><b>씬</b><span>{len(scenes)}</span></div>
      <div class="metric"><b>타임드 가사</b><span>{len(song.get("timed_lyrics", []))}</span></div>
      <div class="metric"><b>장르</b><span>{html.escape(song.get("genre", "-"))}</span></div>
      <div class="metric"><b>무드</b><span>{html.escape(", ".join(song.get("mood", [])))}</span></div>
      <div class="metric"><b>악센트</b><span>{html.escape(world.get("accent_color", "-"))}</span></div>
      <div class="metric"><b>소스</b><span>{html.escape(str(len(source_files)))}</span></div>
      <div class="metric"><b>음악 파일</b><span>{html.escape(str(len(audio_files)))}</span></div>
      <div class="metric"><b>오디오 반영</b><span>{'ON' if song.get("audio_analysis_applied") else 'OFF'}</span></div>
    </section>
    <section class="panel story">
      <h2>전체 스토리</h2>
      <p><strong>로그라인:</strong> {html.escape(story_arc.get("logline_ko", ""))}</p>
      <p>{html.escape(story_arc.get("story_summary_ko", ""))}</p>
    </section>
    {render_character_model_sheet(character_model_sheet)}
    <section class="panel">
      {scene_cards}
    </section>
  </div>
</div>
"""


def render_character_model_sheet(character_model_sheet: dict[str, Any]) -> str:
    if not character_model_sheet:
        return ""
    views = "\n".join(f"- {view}" for view in character_model_sheet.get("required_views", []))
    usage = "\n".join(f"- {item}" for item in character_model_sheet.get("usage", []))
    prompt = character_model_sheet.get("character_reference_prompt", "")
    return f"""
    <section class="panel scene">
      <h3>Step 00 · Character Turnaround Model Sheet</h3>
      <div class="meta">
        <span class="chip">identity reference</span>
        <span class="chip">generate first</span>
        <span class="chip">model sheet</span>
      </div>
      <details open>
        <summary>필수 뷰</summary>
        <pre>{html.escape(views)}</pre>
      </details>
      <details open>
        <summary>사용 방법</summary>
        <pre>{html.escape(usage)}</pre>
      </details>
      <details open>
        <summary>캐릭터 턴어라운드 이미지 프롬프트</summary>
        <pre>{html.escape(prompt)}</pre>
      </details>
    </section>
"""


def render_scene(scene: dict[str, Any]) -> str:
    lyrics = scene.get("lyrics_excerpt", "").strip() or "(instrumental)"
    return f"""
<article class="scene">
  <h3>Scene {scene.get("scene_number", "?"):02d} · {html.escape(scene.get("music_section", ""))}</h3>
  <div class="meta">
    <span class="chip">{html.escape(scene.get("emotion", ""))}</span>
    <span class="chip">{html.escape(scene.get("intensity", ""))}</span>
    <span class="chip">{html.escape(scene.get("environment", ""))}</span>
  </div>
  <details>
    <summary>가사</summary>
    <pre>{html.escape(lyrics)}</pre>
  </details>
  <details open>
    <summary>스토리 연결</summary>
    <pre>{html.escape(scene.get("story_beat_ko", ""))}

이전 연결: {html.escape(scene.get("continuity_from_previous_ko", ""))}
다음 연결: {html.escape(scene.get("continuity_to_next_ko", ""))}</pre>
  </details>
  <details open>
    <summary>이미지 프롬프트</summary>
    <pre>{html.escape(scene.get("image_prompt", ""))}</pre>
  </details>
  <details>
    <summary>비디오 프롬프트</summary>
    <pre>{html.escape(scene.get("video_prompt", ""))}</pre>
  </details>
</article>
"""


def load_recent_raw_text() -> str:
    path = PROJECT_ROOT / "input" / "raw_song.txt"
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_ui_state() -> dict:
    path = PROJECT_ROOT / "input" / "ui_state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_ui_state(state: dict) -> None:
    path = PROJECT_ROOT / "input" / "ui_state.json"
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def safe_filename(value: str, fallback: str) -> str:
    name = Path(value or fallback).name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS and fallback != "raw_song.txt":
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise ValueError(f"Only these upload types are allowed ({allowed}): {name}")
    return name or fallback


def write_upload(field: FieldStorage, target_dir: Path, fallback_name: str, max_size: int = MAX_TEXT_UPLOAD_SIZE) -> Path | None:
    if not getattr(field, "filename", ""):
        return None
    filename = safe_filename(field.filename, fallback_name)
    target = target_dir / filename
    data = field.file.read(max_size + 1)
    if len(data) > max_size:
        raise ValueError(f"Upload is too large: {filename}")
    target.write_bytes(data)
    return target


def generate_from_form(form: FieldStorage) -> Path:
    ensure_directories()
    run_input_dir = PROJECT_ROOT / "output" / "web_inputs" / timestamp()
    run_input_dir.mkdir(parents=True, exist_ok=False)

    lyrics_raw = form.getfirst("lyrics", "").replace("\r\n", "\n").replace("\r", "\n").strip()
    title = form.getfirst("title", "").strip()
    apply_audio_analysis = bool(form.getfirst("apply_audio_analysis"))
    if not lyrics_raw:
        raise ValueError("가사 또는 메타 정보를 입력해 주세요.")
    lyrics_for_pipeline = f"Title: {title}\n{lyrics_raw}" if title else lyrics_raw

    save_ui_state({"apply_audio_analysis": apply_audio_analysis})
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

    song_parser.run(
        input_path=run_input_dir,
        output_path=PROJECT_ROOT / "input" / "song_master.json",
        apply_audio_analysis=apply_audio_analysis,
    )
    emotion_engine.run()
    scene_generator.run()
    image_prompt_generator.run()
    video_prompt_generator.run()

    song = read_json(PROJECT_ROOT / "input" / "song_master.json")
    snapshot_dir = snapshot_outputs(slugify(song["title"]))
    if audio_uploads:
        audio_snapshot_dir = snapshot_dir / "input" / "audio"
        audio_snapshot_dir.mkdir(parents=True, exist_ok=True)
        for audio_path in audio_uploads:
            shutil.copy2(audio_path, audio_snapshot_dir / audio_path.name)
    return snapshot_dir


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"/", "/results"}:
            self.send_html(page_shell(render_results() if parsed.path == "/results" else render_form(load_recent_raw_text())))
            return
        if parsed.path == "/api/song_master":
            self.send_json_file(PROJECT_ROOT / "input" / "song_master.json")
            return
        if parsed.path == "/api/story_arc":
            self.send_json_file(PROJECT_ROOT / "storyboard" / "story_arc.json")
            return
        if parsed.path == "/api/scene_list":
            self.send_json_file(PROJECT_ROOT / "storyboard" / "scene_list.json")
            return
        if parsed.path == "/character-reference":
            self.send_text_file(PROJECT_ROOT / "character" / "character_reference_prompt.md")
            return
        if parsed.path == "/story-summary":
            self.send_text_file(PROJECT_ROOT / "storyboard" / "story_summary.md")
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/generate":
            self.send_error(404)
            return
        try:
            form = FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
                },
            )
            snapshot_dir = generate_from_form(form)
            content = render_results()
            self.send_html(page_shell(content, f"생성이 완료되었습니다. 스냅샷: {snapshot_dir}"))
        except Exception as exc:
            self.send_html(page_shell(render_form(load_recent_raw_text()), f"오류: {exc}"), status=500)

    def send_html(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
