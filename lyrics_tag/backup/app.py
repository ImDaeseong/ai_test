import os
import re
import sys
import traceback
import tempfile
import whisper
import torch
from flask import Flask, request, jsonify, render_template, send_file
from difflib import SequenceMatcher
from waitress import serve

# ── 0. PyInstaller exe 경로 처리 ───────────────────────────────────────────────
def resource_path(relative_path):
    """
    PyInstaller exe에서 실행 시, _MEIPASS 경로를 처리
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ── 1. ffmpeg 경로 설정 (PyInstaller exe 포함 시 자동 탐지) ──────────────────
if getattr(sys, 'frozen', False):
    _ffmpeg_path = os.path.join(os.path.dirname(sys.executable), 'ffmpeg.exe')
    if os.path.exists(_ffmpeg_path):
        os.environ['PATH'] = os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', '')

# ── 2. CPU 최적화 ─────────────────────────────────────────────────────────────
torch.set_num_threads(4)

# ── 2. Flask 앱 초기화 ────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static")
)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

# exe 실행 위치 옆에 uploads 폴더 생성 (쓰기 가능 경로)
if getattr(sys, 'frozen', False):
    UPLOAD_FOLDER = os.path.join(os.path.dirname(sys.executable), 'uploads')
else:
    UPLOAD_FOLDER = os.path.join(os.path.abspath('.'), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── 3. Whisper 모델 로딩 ──────────────────────────────────────────────────────
print('--- [System] Whisper 모델 로딩 시작 (Base) ---')
# exe 배포 시 assets 폴더를 포함시키고, download_root 지정
model = whisper.load_model(
    'base',
    device='cpu',
    download_root=resource_path("whisper/assets")  # PyInstaller exe용 경로
)
print('--- [System] Whisper 모델 로딩 완료 ---')

# ── 4. 유틸 함수 ─────────────────────────────────────────────────────────────
def normalize_for_similarity(text):
    if not text: return ""
    return re.sub(r"[^\w]", "", text).lower()

def get_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def align_lyrics_to_words(lyric_lines, whisper_words):
    segments = []
    w_idx = 0
    num_words = len(whisper_words)

    for idx, line in enumerate(lyric_lines):
        line = line.strip()
        if not line: continue
        
        line_words = line.split()
        if not line_words: continue

        # [Anchor Search]
        best_match_offset = 0
        search_range = min(15, num_words - w_idx)
        first_word_norm = normalize_for_similarity(line_words[0])
        for i in range(search_range):
            target_word = normalize_for_similarity(whisper_words[w_idx + i]['word'])
            if get_similarity(first_word_norm, target_word) > 0.8:
                best_match_offset = i
                break

        w_idx += best_match_offset
        start_time = whisper_words[w_idx]['start'] if w_idx < num_words else 0.0
        
        consumed = min(len(line_words), num_words - w_idx)
        w_idx_end = min(w_idx + consumed - 1, num_words - 1)
        end_time = whisper_words[w_idx_end]['end'] if w_idx_end >= 0 else start_time
        
        segments.append({
            'id': idx,
            'start': round(start_time, 3),
            'end': round(end_time, 3),
            'text': line
        })
        
        w_idx += consumed

    # 후처리: 겹침 및 간격 보정
    for i in range(len(segments) - 1):
        if segments[i]['end'] > segments[i + 1]['start']:
            segments[i]['end'] = segments[i + 1]['start']
        elif segments[i + 1]['start'] - segments[i]['end'] < 0.1:
            segments[i]['end'] = segments[i + 1]['start']
            
    return segments

# ── 5. Flask 라우트 ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': '오디오 파일이 없습니다.'}), 400

    audio_file = request.files['audio']
    lyrics_text = request.form.get('lyrics', '').strip()
    lyric_lines = [l for l in lyrics_text.splitlines() if l.strip()] if lyrics_text else []

    ext = os.path.splitext(audio_file.filename)[1].lower()
    fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=UPLOAD_FOLDER)
    
    try:
        with os.fdopen(fd, 'wb') as tmp:
            audio_file.save(tmp)

        result = model.transcribe(
            tmp_path,
            word_timestamps=True,
            condition_on_previous_text=False,
            fp16=False,
            beam_size=5
        )

        whisper_words = []
        for seg in result.get('segments', []):
            for w in seg.get('words', []):
                w_text = w.get('word', '').strip()
                if w_text:
                    whisper_words.append({
                        'word': w_text,
                        'start': w.get('start', 0.0),
                        'end': w.get('end', 0.0),
                    })

        if lyric_lines and whisper_words:
            segments = align_lyrics_to_words(lyric_lines, whisper_words)
        else:
            segments = [{'id': i,
                         'start': round(s.get('start'), 3),
                         'end': round(s.get('end'), 3),
                         'text': s.get('text').strip()} 
                        for i, s in enumerate(result.get('segments', []))]

        return jsonify({'segments': segments, 'mode': 'aligned' if lyric_lines else 'auto'})

    except Exception as e:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

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

# ── 6. 앱 실행 ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # 서버 실행 python app.py
    # http://localhost:5000 접속
    serve(app, host='0.0.0.0', port=5000, threads=8)