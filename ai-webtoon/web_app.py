from __future__ import annotations

import json
import re
import sys
import threading
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from flask import Flask, jsonify, request, render_template_string
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "flask", "-q"], check=True)
    from flask import Flask, jsonify, request, render_template_string

OUTPUT_DIR = Path(__file__).parent / "output"
PORT = 5350

app = Flask(__name__)


def _panel_done(song_dir: Path, panel_stem: str) -> bool:
    sf = song_dir / "panels" / f"{panel_stem}.status.json"
    if not sf.exists():
        return False
    try:
        return json.loads(sf.read_text(encoding="utf-8")).get("done", False)
    except Exception:
        return False


def list_songs() -> list[dict]:
    if not OUTPUT_DIR.exists():
        return []
    result = []
    for d in sorted(OUTPUT_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        panels_dir = d / "panels"
        if not panels_dir.exists():
            continue
        panel_files = sorted(panels_dir.glob("panel_*.md"))
        if not panel_files:
            continue
        done = sum(1 for pf in panel_files if _panel_done(d, pf.stem))
        result.append({"name": d.name, "done": done, "total": len(panel_files)})
    return result


def get_song_detail(song_name: str) -> dict | None:
    song_dir = OUTPUT_DIR / song_name
    if not song_dir.exists():
        return None
    panels_dir = song_dir / "panels"
    if not panels_dir.exists():
        return None

    panels = []
    for pf in sorted(panels_dir.glob("panel_*.md")):
        content = pf.read_text(encoding="utf-8")
        m = re.match(r"panel_(\d+)_(.*?)_([^_]+)$", pf.stem)
        num    = int(m.group(1)) if m else 0
        sec    = m.group(2) if m else "unknown"
        ptype  = m.group(3) if m else "unknown"
        panels.append({
            "key": pf.stem,
            "num": num,
            "section": sec,
            "type": ptype,
            "done": _panel_done(song_dir, pf.stem),
            "content": content,
        })

    storyboard = ""
    style_ref  = ""
    sp = song_dir / "01_storyboard.md"
    if sp.exists():
        storyboard = sp.read_text(encoding="utf-8")
    rp = song_dir / "00_style_reference.md"
    if rp.exists():
        style_ref = rp.read_text(encoding="utf-8")

    return {"name": song_name, "panels": panels, "storyboard": storyboard, "style_reference": style_ref}


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/songs")
def api_songs():
    return jsonify(list_songs())


@app.route("/api/song/<song_name>")
def api_song(song_name: str):
    data = get_song_detail(song_name)
    if data is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)


@app.route("/api/song/<song_name>/panel/<panel_key>/done", methods=["POST"])
def api_panel_done(song_name: str, panel_key: str):
    panels_dir = OUTPUT_DIR / song_name / "panels"
    if not panels_dir.exists():
        return jsonify({"error": "not found"}), 404
    done = bool((request.json or {}).get("done", True))
    sf = panels_dir / f"{panel_key}.status.json"
    sf.write_text(json.dumps({"done": done}), encoding="utf-8")
    return jsonify({"ok": True, "done": done})


HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ai-webtoon 패널 뷰어</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0a0a0f;color:#e0e0e0;min-height:100vh}
.sidebar{position:fixed;left:0;top:0;width:260px;height:100vh;overflow-y:auto;background:#12121a;border-right:1px solid #2a2a3a;padding:16px}
.sidebar h1{font-size:13px;color:#ff4db8;margin-bottom:4px;font-weight:700;letter-spacing:1px}
.sidebar small{font-size:10px;color:#555;display:block;margin-bottom:16px}
.song-item{padding:10px 12px;border-radius:8px;cursor:pointer;margin-bottom:6px;border:1px solid transparent}
.song-item:hover{background:#1a1a2e;border-color:#2a2a4a}
.song-item.active{background:#1a0a2e;border-color:#ff4db8}
.song-name{font-size:12px;font-weight:600;word-break:break-all}
.song-prog{font-size:10px;color:#888;margin-top:3px}
.prog-bar{height:3px;background:#222;border-radius:2px;margin-top:5px}
.prog-fill{height:100%;background:#ff4db8;border-radius:2px;transition:width .3s}
.main{margin-left:260px;padding:24px;min-height:100vh}
.main-header{display:flex;align-items:center;gap:12px;margin-bottom:20px;flex-wrap:wrap}
.main-header h2{font-size:18px;color:#ff4db8;font-weight:700}
.btn{padding:7px 14px;border-radius:6px;border:1px solid #2a2a4a;background:#12121a;color:#aaa;font-size:12px;cursor:pointer}
.btn:hover{border-color:#ff4db8;color:#ff4db8}
.btn.pink{background:#ff4db8;border-color:#ff4db8;color:#fff}
.panel-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.card{background:#12121a;border:1px solid #2a2a3a;border-radius:10px;padding:14px;cursor:pointer;transition:border-color .2s}
.card:hover{border-color:#ff4db8}
.card.done{border-color:#3a6a4a;opacity:.65}
.card-num{font-size:10px;color:#ff4db8;font-weight:700}
.card-type{font-size:13px;font-weight:600;margin-top:4px;text-transform:capitalize}
.card-sec{font-size:11px;color:#888;margin-top:2px}
.card-dur{font-size:10px;color:#555;margin-top:2px}
.badge{display:inline-block;background:#1a3a2a;color:#4db86c;font-size:9px;padding:2px 7px;border-radius:10px;margin-top:6px}
.empty{color:#555;font-size:14px;padding:60px;text-align:center}
/* Modal */
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:200;overflow-y:auto;padding:30px 16px;align-items:flex-start;justify-content:center}
.overlay.open{display:flex}
.modal{background:#12121a;border:1px solid #2a2a3a;border-radius:12px;padding:24px;max-width:860px;width:100%;position:relative}
.modal-close{position:absolute;top:14px;right:14px;background:none;border:none;color:#666;font-size:18px;cursor:pointer;line-height:1}
.modal-close:hover{color:#ff4db8}
.modal-title{font-size:15px;font-weight:700;color:#ff4db8;margin-bottom:14px}
.tabs{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.tab{padding:5px 13px;border-radius:20px;border:1px solid #2a2a3a;background:none;color:#888;font-size:11px;cursor:pointer}
.tab.active{background:#ff4db8;border-color:#ff4db8;color:#fff}
.pbox{background:#060608;border:1px solid #1e1e2e;border-radius:8px;padding:14px;font-family:monospace;font-size:12px;line-height:1.7;white-space:pre-wrap;word-break:break-word;max-height:420px;overflow-y:auto;color:#b8e0b8}
.actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.act-copy{padding:7px 16px;background:#1a0a2e;border:1px solid #ff4db8;color:#ff4db8;border-radius:6px;cursor:pointer;font-size:12px}
.act-copy:hover{background:#ff4db8;color:#fff}
.act-done{padding:7px 16px;background:#0a1a10;border:1px solid #4db86c;color:#4db86c;border-radius:6px;cursor:pointer;font-size:12px}
.act-done:hover{background:#4db86c;color:#fff}
</style>
</head>
<body>
<div class="sidebar">
  <h1>🎨 ai-webtoon</h1>
  <small>웹툰 패널 프롬프트 뷰어</small>
  <div id="song-list"><div class="empty" style="padding:20px;font-size:12px">로딩 중...</div></div>
</div>
<div class="main" id="main">
  <div class="empty">← 왼쪽에서 곡을 선택하세요</div>
</div>

<div class="overlay" id="overlay">
  <div class="modal">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="modal-title" id="mtitle"></div>
    <div class="tabs" id="mtabs"></div>
    <div class="pbox" id="mcontent"></div>
    <div class="actions">
      <button class="act-copy" onclick="copyPrompt()">📋 프롬프트 복사</button>
      <button class="act-done" id="done-btn" onclick="toggleDone()">✅ 완료 표시</button>
    </div>
  </div>
</div>

<script>
let currentSong = null;
let currentPanel = null;
let currentPlatform = 'gpt';
let allPanels = [];

async function loadSongs() {
  const res = await fetch('/api/songs');
  const songs = await res.json();
  const el = document.getElementById('song-list');
  if (!songs.length) { el.innerHTML = '<div style="color:#555;font-size:12px;padding:20px">output/ 폴더에 곡이 없습니다.<br>python main.py create-all --input-dir input --force</div>'; return; }
  el.innerHTML = songs.map(s => `
    <div class="song-item" onclick="loadSong('${esc(s.name)}')" id="si-${esc(s.name)}">
      <div class="song-name">${esc(s.name)}</div>
      <div class="song-prog">${s.done}/${s.total} 완료</div>
      <div class="prog-bar"><div class="prog-fill" style="width:${s.total>0?Math.round(s.done/s.total*100):0}%"></div></div>
    </div>`).join('');
}

async function loadSong(name) {
  currentSong = name;
  document.querySelectorAll('.song-item').forEach(e=>e.classList.remove('active'));
  const si = document.getElementById('si-'+name);
  if(si) si.classList.add('active');

  document.getElementById('main').innerHTML = '<div class="empty">로딩 중...</div>';
  const res = await fetch('/api/song/'+encodeURIComponent(name));
  const data = await res.json();
  allPanels = data.panels || [];
  window._storyboard = data.storyboard || '';
  window._styleRef   = data.style_reference || '';

  document.getElementById('main').innerHTML = `
    <div class="main-header">
      <h2>${esc(name)}</h2>
      <button class="btn" onclick="showDoc('storyboard')">📋 스토리보드</button>
      <button class="btn" onclick="showDoc('style')">🎨 스타일 기준</button>
    </div>
    <div class="panel-grid" id="pgrid"></div>`;

  renderPanels(allPanels);
}

function renderPanels(panels) {
  const grid = document.getElementById('pgrid');
  if (!panels.length) { grid.innerHTML = '<div class="empty">패널 없음</div>'; return; }
  grid.innerHTML = panels.map(p => {
    const dur = (p.content.match(/지속 시간: (\\d+)초/) || [])[1];
    return `<div class="card ${p.done?'done':''}" onclick="openPanel('${esc(p.key)}')" id="card-${esc(p.key)}">
      <div class="card-num">Panel ${String(p.num).padStart(3,'0')}</div>
      <div class="card-type">${esc(p.type)}</div>
      <div class="card-sec">${esc(p.section)}${dur?' · '+dur+'초':''}</div>
      ${p.done?'<div class="badge">✓ 완료</div>':''}
    </div>`;
  }).join('');
}

function openPanel(key) {
  currentPanel = allPanels.find(p=>p.key===key);
  if (!currentPanel) return;
  document.getElementById('mtitle').textContent =
    `Panel ${String(currentPanel.num).padStart(3,'0')} — ${currentPanel.section} / ${currentPanel.type}`;

  const platforms = [
    {id:'gpt',   label:'GPT Image'},
    {id:'niji',  label:'Nijijourney'},
    {id:'flux',  label:'FLUX.1'},
    {id:'gemini',label:'Gemini'},
    {id:'full',  label:'전체 보기'},
  ];
  document.getElementById('mtabs').innerHTML = platforms.map(pl =>
    `<button class="tab ${pl.id===currentPlatform?'active':''}" onclick="switchPlatform(event,'${pl.id}')">${pl.label}</button>`
  ).join('');

  showPlatform(currentPlatform);
  document.getElementById('done-btn').textContent = currentPanel.done ? '↩ 완료 취소' : '✅ 완료 표시';
  document.getElementById('overlay').classList.add('open');
}

function switchPlatform(e, id) {
  currentPlatform = id;
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  e.target.classList.add('active');
  showPlatform(id);
}

function showPlatform(id) {
  const content = currentPanel.content;
  let out = '';
  if (id === 'full') {
    out = content;
  } else {
    const hdr = {gpt:'## GPT Image', niji:'## Nijijourney', flux:'## FLUX.1', gemini:'## Gemini'}[id];
    if (hdr) {
      const s = content.indexOf(hdr);
      if (s >= 0) {
        const nxt = content.indexOf('\\n## ', s + hdr.length);
        const sec = nxt >= 0 ? content.slice(s, nxt) : content.slice(s);
        const m = sec.match(/```[\\s\\S]*?\\n([\\s\\S]*?)\\n```/);
        out = m ? m[1].trim() : sec;
      }
    }
  }
  document.getElementById('mcontent').textContent = out || '내용 없음';
}

function copyPrompt() {
  const text = document.getElementById('mcontent').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.act-copy');
    btn.textContent = '✓ 복사됨!';
    setTimeout(()=>btn.textContent='📋 프롬프트 복사', 1500);
  });
}

async function toggleDone() {
  if (!currentPanel || !currentSong) return;
  const newDone = !currentPanel.done;
  await fetch(`/api/song/${encodeURIComponent(currentSong)}/panel/${currentPanel.key}/done`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({done: newDone}),
  });
  currentPanel.done = newDone;
  document.getElementById('done-btn').textContent = newDone ? '↩ 완료 취소' : '✅ 완료 표시';
  const card = document.getElementById('card-'+currentPanel.key);
  if (card) {
    card.classList.toggle('done', newDone);
    const b = card.querySelector('.badge');
    if (newDone && !b) card.insertAdjacentHTML('beforeend','<div class="badge">✓ 완료</div>');
    else if (!newDone && b) b.remove();
  }
  loadSongs();
}

function showDoc(type) {
  const content = type==='storyboard' ? window._storyboard : window._styleRef;
  document.getElementById('mtitle').textContent = type==='storyboard' ? '스토리보드' : '스타일 기준';
  document.getElementById('mtabs').innerHTML = '';
  document.getElementById('mcontent').textContent = content || '파일 없음';
  document.getElementById('overlay').classList.add('open');
}

function closeModal() { document.getElementById('overlay').classList.remove('open'); }
document.getElementById('overlay').addEventListener('click', e=>{ if(e.target===e.currentTarget) closeModal(); });

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

loadSongs();
</script>
</body>
</html>"""


def _open_browser() -> None:
    import time
    time.sleep(1.0)
    webbrowser.open(f"http://127.0.0.1:{PORT}")


def main() -> None:
    threading.Thread(target=_open_browser, daemon=True).start()
    print(f"ai-webtoon 패널 뷰어 → http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)


if __name__ == "__main__":
    main()
