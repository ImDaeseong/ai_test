import os
import sys
import tempfile
from flask import Flask, request, render_template, send_file
from waitress import serve

# ── 0. PyInstaller exe 경로 처리 ─────────────────────────────
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ── 1. ffmpeg 경로 설정 ─────────────────────────────────────
if getattr(sys, 'frozen', False):
    _ffmpeg_path = os.path.join(os.path.dirname(sys.executable), 'ffmpeg.exe')
    if os.path.exists(_ffmpeg_path):
        os.environ['PATH'] = os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', '')

# ── 2. Flask 초기화 ─────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static")
)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

# ── 3. 라우트 ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download_lrc', methods=['POST'])
def download_lrc():
    data = request.get_json()
    segments = data.get('segments', [])

    lines = []
    for seg in segments:
        t = seg.get('start', 0)
        tag = f"[{int(t//60):02d}:{t%60:06.3f}]"
        lines.append(f"{tag}{seg['text']}")

    fd, path = tempfile.mkstemp(suffix='.lrc')
    with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
        tmp.write('\n'.join(lines))

    return send_file(path, as_attachment=True, download_name='lyrics.lrc')

# ── 4. 실행 ───────────────────────────────────────────────
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000, threads=4)
