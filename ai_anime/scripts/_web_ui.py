"""HTML rendering and UI state helpers for web_app.py.

Separated from web_app.py so the HTTP handler and business logic
remain independent of HTML/CSS generation details.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, load_config, read_json


# ─── UI state persistence ──────────────────────────────────────────────────────

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


# ─── HTML rendering ────────────────────────────────────────────────────────────

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

    // ── SSE 진행률 표시 ───────────────────────────────────────────────────────
    let _sseSource = null;

    function startProgressSSE() {{
      if (_sseSource) {{ _sseSource.close(); }}
      showMsg('파이프라인 시작 중…', 'warn');
      _sseSource = new EventSource('/api/progress');
      _sseSource.onmessage = function(e) {{
        try {{
          const data = JSON.parse(e.data);
          showMsg(esc(data.message || e.data), 'warn');
        }} catch (_) {{
          showMsg(esc(e.data), 'warn');
        }}
      }};
      _sseSource.addEventListener('done', function() {{
        _sseSource.close();
        _sseSource = null;
        clearMsg();
      }});
      _sseSource.onerror = function() {{
        _sseSource.close();
        _sseSource = null;
      }};
    }}

    // Generate 버튼 submit 시 SSE 연결 먼저 시작
    document.addEventListener('DOMContentLoaded', function() {{
      document.querySelectorAll('form[action="/generate"]').forEach(function(form) {{
        form.addEventListener('submit', function() {{
          startProgressSSE();
        }});
      }});
    }});
  </script>
</body>
</html>"""
    return document.encode("utf-8")


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
