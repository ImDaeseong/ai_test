from __future__ import annotations

import argparse
import html
import io
import json
import re
import shutil
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import config_learner
import emotion_engine
import image_prompt_generator
import song_parser
import scene_generator
import video_prompt_generator
from common import PROJECT_ROOT, clean_tags, ensure_directories, load_config, read_json, timestamp, write_text


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
    select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
      color: var(--text);
      font: inherit;
      font-size: 14px;
      padding: 10px 11px;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23687386' viewBox='0 0 16 16'%3E%3Cpath d='M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: calc(100% - 12px) center;
    }}
    .suno-row {{
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      background: #f1f4f9;
      padding: 12px;
      border-radius: 8px;
      border: 1px dashed var(--line);
    }}
    .suno-row input {{
      flex: 1;
      margin-bottom: 0 !important;
    }}
    .suno-row button {{
      white-space: nowrap;
      padding: 8px 16px;
      background: #444;
    }}
    .suno-row button:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
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
    #msg-bar {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 9999;
      padding: 14px 24px;
      font-size: 14px;
      font-weight: 600;
      line-height: 1.6;
      border-bottom: 3px solid;
      box-shadow: 0 2px 12px rgba(0,0,0,0.18);
    }}
    #msg-bar .msg-close {{
      float: right;
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
      opacity: 0.6;
      margin-left: 16px;
    }}
    #msg-bar .msg-close:hover {{ opacity: 1; }}
    #msg-bar.ok   {{ background: #d1fae5; border-color: #059669; color: #065f46; }}
    #msg-bar.warn {{ background: #fef9c3; border-color: #ca8a04; color: #713f12; }}
    #msg-bar.err  {{ background: #fee2e2; border-color: #dc2626; color: #7f1d1d; }}
  </style>
</head>
<body>
  <header>
    <h1>AI Anime MV Builder</h1>
    <p>가사를 입력하고 필요하면 LRC/SRT와 음악 파일을 선택 첨부하면 storyboard, 이미지 프롬프트, 비디오 프롬프트를 생성할 수 있습니다.</p>
  </header>
  <main>
    {status_html}
    <div id="msg-bar" role="alert"></div>
    {content}
  </main>
  <script>
    function esc(s) {{
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }}
    function showMsg(html_content, type) {{
      const bar = document.getElementById('msg-bar');
      if (!bar) return;
      bar.className = 'msg-bar ' + (type || 'ok');
      bar.innerHTML = '<span class="msg-close" onclick="clearMsg()">&#x2715;</span>' + html_content;
      bar.style.display = 'block';
    }}
    function clearMsg() {{
      const bar = document.getElementById('msg-bar');
      if (bar) {{ bar.style.display = 'none'; bar.innerHTML = ''; }}
    }}

    async function importSuno() {{
      const urlInput = document.getElementById('suno_url');
      const btn = document.getElementById('suno_btn');
      const url = urlInput.value.trim();
      if (!url) {{ showMsg('Suno 곡 URL을 입력해주세요.', 'warn'); return; }}
      clearMsg();
      btn.disabled = true;
      btn.innerText = '가져오는 중...';
      try {{
        const res = await fetch('/api/import_suno?url=' + encodeURIComponent(url));
        const data = await res.json();
        if (data.error) {{
          showMsg('오류: ' + esc(data.error), 'err');
        }} else {{
          if (data.title) {{
            const titleInput = document.getElementById('title');
            if (titleInput) titleInput.value = data.title;
          }}
          let content = '';
          if (data.tags) content += 'Style: ' + data.tags + '\\n\\n';
          if (data.lyrics) content += data.lyrics;
          const lyricsArea = document.getElementById('lyrics');
          if (lyricsArea && content) lyricsArea.value = content;
          if (data.analysis) {{
            showMsg(
              `가져오기 완료 &nbsp;—&nbsp; 제목: <b>${{esc(data.title || '없음')}}</b> &nbsp;/&nbsp; 태그 <b>${{data.analysis.tag_count}}</b>개 &nbsp;/&nbsp; 가사 <b>${{data.analysis.lyrics_chars}}</b>자`,
              'ok'
            );
          }}
        }}
      }} catch (e) {{
        showMsg('연결 오류: ' + esc(e.message), 'err');
      }} finally {{
        btn.disabled = false;
        btn.innerText = '가져오기';
      }}
    }}

    let _learnReport = null;

    async function learnConfig() {{
      const btn = document.getElementById('learn_btn');
      if (!btn) return;
      clearMsg();
      btn.disabled = true;
      btn.innerText = '분석 중...';
      try {{
        const res = await fetch('/api/config_learn', {{method: 'GET'}});
        const report = await res.json();

        if (report.status === 'skipped') {{
          showMsg('Suno 이력이 없습니다. 먼저 Suno URL로 곡을 가져와 주세요.', 'warn');
          return;
        }}

        const gUpdates = report.genre_updates || {{}};
        const aUpdates = report.atmosphere_updates || {{}};
        const totalGenre = Object.values(gUpdates).reduce((s, v) => s + v.length, 0);
        const totalUrban = (aUpdates.urban_keywords || []).length;
        const totalSeason = Object.keys(aUpdates.season_rules || {{}}).length;

        if (totalGenre + totalUrban + totalSeason === 0) {{
          showMsg(`분석 완료 (${{report.entries_analyzed}}곡) &nbsp;—&nbsp; 추가할 새 키워드 없음. 모든 태그가 이미 Config에 포함되어 있습니다.`, 'ok');
          return;
        }}

        let lines = [];
        if (totalGenre > 0) {{
          for (const [profile, keys] of Object.entries(gUpdates)) {{
            lines.push(`장르 <b>${{esc(profile)}}</b> 키 추가: ${{esc(keys.join(', '))}}`);
          }}
        }}
        if (totalUrban > 0) lines.push(`도시 키워드 추가: ${{esc(aUpdates.urban_keywords.join(', '))}}`);
        if (totalSeason > 0) lines.push(`계절 규칙 추가: ${{esc(Object.keys(aUpdates.season_rules).join(', '))}}`);
        if (report.bpm_stats) {{
          const b = report.bpm_stats;
          lines.push(`BPM 분포 (${{b.count}}곡): 평균 ${{b.mean}} / 중앙값 ${{b.median}} / 범위 ${{b.min}}~${{b.max}}`);
        }}

        _learnReport = report;
        showMsg(
          `분석 완료 (${{report.entries_analyzed}}곡)<br>` +
          `<ul style="margin:8px 0 12px 18px;">${{lines.map(l=>`<li>${{l}}</li>`).join('')}}</ul>` +
          `<button onclick="applyLearnConfig()" style="background:var(--accent);color:white;border:0;padding:8px 18px;border-radius:6px;cursor:pointer;font-weight:700;margin-right:8px;">Config에 적용</button>` +
          `<button onclick="clearMsg()" style="background:#eef2f7;color:#1d2430;border:1px solid #d8dee8;padding:8px 16px;border-radius:6px;cursor:pointer;">취소</button>`,
          'warn'
        );
      }} catch (e) {{
        showMsg('오류: ' + esc(e.message), 'err');
      }} finally {{
        btn.disabled = false;
        btn.innerText = 'Config 자동 학습';
      }}
    }}

    async function applyLearnConfig() {{
      clearMsg();
      try {{
        const applyRes = await fetch('/api/config_learn', {{method: 'POST'}});
        const applied = await applyRes.json();
        const changed = (applied.configs_changed || []).join(', ');
        const backup = applied.backup_path ? ` <small style="color:#444">(백업: ${{esc(applied.backup_path)}})</small>` : '';
        showMsg(`Config 업데이트 완료! &nbsp; 변경 파일: <b>${{esc(changed || '없음')}}</b>${{backup}}`, 'ok');
      }} catch (e) {{
        showMsg('적용 오류: ' + esc(e.message), 'err');
      }}
      _learnReport = null;
    }}
  </script>
</body>
</html>"""
    return document.encode("utf-8")


def render_form(sample_text: str = "") -> str:
    return f"""
<div class="layout">
  <section class="form-panel">
    <form method="post" action="/generate" enctype="multipart/form-data">
      <div class="suno-row">
        <input id="suno_url" type="text" placeholder="Suno 곡 URL (선택)">
        <button id="suno_btn" type="button" onclick="importSuno()">가져오기</button>
      </div>

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
        <button type="submit" style="background: var(--accent-strong); font-size: 16px;">Generate Storyboard</button>
        <a class="button secondary" href="/results">최근 결과 보기</a>
      </div>
    </form>
    <div style="margin-top:16px; padding-top:12px; border-top:1px solid var(--line);">
      <button id="learn_btn" type="button" class="secondary" onclick="learnConfig()"
              style="width:100%; font-size:13px;">Config 자동 학습 (Suno 이력 반영)</button>
    </div>
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
    ui_state = load_ui_state()
    audio_analysis_checked = " checked" if ui_state.get("apply_audio_analysis") else ""
    theme_options = render_theme_options(ui_state.get("style_id", ""))
    scene_cards = "\n".join(render_scene(scene) for scene in scenes)

    return f"""
<div class="layout">
  <section class="form-panel">
    <div class="suno-row">
      <input id="suno_url" type="text" placeholder="Suno 곡 URL (선택)">
      <button id="suno_btn" type="button" onclick="importSuno()">가져오기</button>
    </div>
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

      <label for="style_id">비주얼 스타일</label>
      <select id="style_id" name="style_id">
        {theme_options}
      </select>

      <div class="actions">
        <button type="submit" style="background: var(--accent-strong); font-size: 16px;">Generate Storyboard</button>
        <a class="button secondary" href="/api/song_master" target="_blank">song_master.json</a>
        <a class="button secondary" href="/api/story_arc" target="_blank">story_arc.json</a>
        <a class="button secondary" href="/api/scene_list" target="_blank">scene_list.json</a>
        <a class="button secondary" href="/character-reference" target="_blank">캐릭터 기준 프롬프트</a>
        <a class="button secondary" href="/story-summary" target="_blank">전체 스토리</a>
      </div>
    </form>
    <div style="margin-top:16px; padding-top:12px; border-top:1px solid var(--line);">
      <button id="learn_btn" type="button" class="secondary" onclick="learnConfig()"
              style="width:100%; font-size:13px;">Config 자동 학습 (Suno 이력 반영)</button>
    </div>
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


def render_theme_options(selected_id: str | None = None) -> str:
    config = load_config("visual_styles")
    styles = config.get("styles", {})
    selected_id = selected_id or ""
    options = [
        '<option value="" selected>Auto - match song</option>' if not selected_id else '<option value="">Auto - match song</option>'
    ]
    for sid, data in styles.items():
        is_selected = " selected" if sid == selected_id else ""
        name = data.get("name", sid)
        options.append(f'<option value="{sid}"{is_selected}>{html.escape(name)}</option>')
    return "\n".join(options)





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
    clean_tags = [t for t in metadata.get("style_tags", []) if not _NON_GENRE_RE.match(t.strip())]
    genre = ", ".join(clean_tags[:3]) if clean_tags else metadata.get("genre", "")

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
        "style_tags":        clean_tags,
        "vocal_style":       vocal_style,
        "section_structure": [s["section"] for s in sections],
        "section_count":     len(sections),
    }


def save_to_suno_history(url: str, data: dict[str, Any]) -> None:
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
                # Handle unicode escape (\u1234)
                val = val.encode('utf-8').decode('unicode-escape')
                # Handle double-encoding mojibake
                if any(ord(c) > 127 for c in val):
                    try: val = val.encode('latin1').decode('utf-8')
                    except: pass
            except: pass
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
        # Try JSON fields first (lyrics or prompt)
        lyrics = extract_json_field("lyrics", html_content) or extract_json_field("prompt", html_content)
        
        # If still no lyrics, look for the "lyrics chunk" (usually starts with section markers)
        if not lyrics or len(lyrics) < 20:
            for chunk in chunks:
                if "[Intro]" in chunk or "[Verse" in chunk or "[Chorus]" in chunk:
                    # Found a chunk that looks like lyrics
                    # Sometimes it's inside a JSON-like array string, let's clean it
                    clean_chunk = chunk
                    if clean_chunk.startswith("49:["): # Common Next.js RSC prefix
                        try:
                            # Try a very loose extraction of the first large string block
                            text_match = re.search(r'\["(.*?)",', clean_chunk)
                            if text_match: clean_chunk = text_match.group(1)
                        except: pass
                    
                    if len(clean_chunk) > len(lyrics):
                        lyrics = clean_chunk

        if lyrics or tags:
            cleaned = clean_tags(tags)
            data = {
                "title": html.unescape(title),
                "lyrics": html.unescape(lyrics),
                "tags": ", ".join(cleaned), # Saved as cleaned CSV
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


def backfill_history_patterns() -> int:
    """모든 이력 항목에 최신 패턴 분석 재적용 + URL 기준 중복 제거."""
    history_file = PROJECT_ROOT / "data" / "suno_history.jsonl"
    if not history_file.exists():
        return 0

    lines = [l for l in history_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    updated = 0
    seen_urls: dict[str, dict] = {}   # url → entry (가장 최근 항목 유지)

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

        url = entry.get("url") or entry.get("timestamp", "")
        seen_urls[url] = entry   # 같은 URL이면 마지막 항목으로 덮어쓰기

    new_lines = [json.dumps(e, ensure_ascii=False) for e in seen_urls.values()]
    history_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return updated


def save_generate_to_history(song: dict[str, Any]) -> None:
    """Generate Storyboard 실행 시 song_master 분석 결과를 이력에 저장."""
    history_dir = PROJECT_ROOT / "data"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "suno_history.jsonl"

    sections = song.get("sections", [])
    style_tags = song.get("style_tags", [])

    log_entry = {
        "timestamp":      timestamp(),
        "source":         "generate_storyboard",
        "url":            "",
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
    with _generate_lock:
        return _generate_from_form_locked(form)


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

    song_parser.run(
        input_path=run_input_dir,
        output_path=PROJECT_ROOT / "input" / "song_master.json",
        apply_audio_analysis=apply_audio_analysis,
    )
    emotion_engine.run()
    scene_generator.run(style_id=style_id or None)
    image_prompt_generator.run()
    video_prompt_generator.run()

    song = read_json(PROJECT_ROOT / "input" / "song_master.json")
    save_generate_to_history(song)
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
    parser = argparse.ArgumentParser(description="Run the local web UI for the AI anime MV pipeline.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    ensure_directories()
    filled = backfill_history_patterns()
    if filled:
        print(f"History backfill: {filled}개 항목에 패턴 분석 추가 완료")
    server = ThreadingHTTPServer((args.host, args.port), WebHandler)
    print(f"Web UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
