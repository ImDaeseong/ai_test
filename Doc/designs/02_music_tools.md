# 설계문서 02 — 음악 도구

> 프로젝트: Analysis_music, mp3_daw, master_tag, lyrics_tag

---

## 1. 프로젝트별 한줄 정의

| 프로젝트 | 정의 |
|---------|------|
| **Analysis_music** | Suno AI 프롬프트 분석 → 악보(LilyPond) + 리포트 + 비주얼 프롬프트 |
| **mp3_daw** | Go 파일 감시 + Python 음성처리 = 로컬 DAW (BPM/Key/LUFS + 마스터링) |
| **master_tag** | Pedalboard 기반 마스터링 체인 (EQ→컴프→M/S→LUFS→리미터) |
| **lyrics_tag** | LRC/SRT 가사 타임스탬프 생성·편집 Flask 웹앱 |

---

## 2. Analysis_music

### 기술 스택
- **Python** 3.9+, **Flask** 3.0 (웹 UI)
- **librosa** 0.10 (BPM·키·에너지 분석)
- **numpy**, **scipy** (수치 연산)
- **markdown2** + **bleach** (MD → HTML, XSS 방어)
- **LilyPond** (악보 PDF 생성, 선택)

### 아키텍처 (4-모듈)
```
[입력: Suno 프롬프트 텍스트 + 선택 오디오]
  ↓
analyzer/suno_parser.py     → SunoPromptData
analyzer/audio_analyzer.py  → AudioAnalysisResult (librosa)
  ↓
generators/report_gen.py    → report.md
generators/lilypond_gen.py  → sheet.ly (악보)
generators/visual_gen.py    → visual_prompts.md
  ↓
[출력: 마크다운 + LilyPond + 비주얼 프롬프트]
```

### SunoParser 파싱 대상
```
[Genre: K-Pop]          → genre
[BPM: 128]              → bpm
[Key: Am]               → key
[Mood: melancholic]     → mood
[Instruments: guitar, piano] → instruments

[Verse 1]              → section (대괄호)
(Chorus)               → section (소괄호)
Intro:                 → section (Bare)

가사 (Am) 코드 (F) 인라인 → chord_progression
Am – F – C – G         → chord_progression (패턴)
```

### 오디오 분석 (audio_analyzer.py)
```python
# BPM 감지
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

# 키 추정 (Krumhansl-Schmuckler)
chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
# 24개 (12 장조 + 12 단조) 상관계수 → 최고 점수 선택

# 에너지 분석 (섹션별)
rms = librosa.feature.rms(y=section_audio)
# High/Medium/Low 분류 → ASCII 차트 생성
```

### 비주얼 테마 선택 (41개 규칙)
```python
frozenset({'EDM', 'Rave', 'Drop'})    → "Cyberpunk Neon"
frozenset({'K-Pop', 'Idol'})          → "Cyberpunk Neon"
frozenset({'Dark', '808', 'Trap'})    → "Cyberpunk Dark"
frozenset({'Ballad', 'Sad'})          → "Emotional Cinematic"
frozenset({'Hip-Hop', 'Urban'})       → "Urban Cinematic"
```

### 웹 UI (Flask SSE)
```python
# SSE 실시간 진행률
@app.route('/api/progress/<job_id>')
def progress_stream(job_id):
    def generate():
        while True:
            event = job_queue.get()
            yield f"data: {json.dumps(event)}\n\n"
    return Response(generate(), content_type='text/event-stream')
```

### LilyPond 동적 악보 생성 원칙
- 장르 룩업 테이블 사용 금지
- 음악 속성(BPM, Key, 무드, 박자, 섹션 역할) 기반으로 멜로디 패턴 합성
- 코드 변환: `Cmaj7 → c:maj7`, `C/G → c1/g` (on-bass)
- longest-first 매칭으로 부분 매치 방지

### CLI 실행
```bash
python main.py --prompt sample.txt [--audio song.mp3]
python main.py --prompt sample.txt --render-pdf  # LilyPond PDF 생성
```

### 테스트 (67개)
```
- 키 정규화 5개
- 박자 파싱 5개
- 코드 추출 5개
- 기본 진행 5개
- 스타일 디스크립터 구분
- 메타데이터·섹션·가사 파싱
```

---

## 3. mp3_daw

### 기술 스택
- **Go** 1.21 (웹 서버 + 파일 감시)
  - `fsnotify`: 파일 시스템 이벤트 감시
  - `gin`: HTTP 웹 프레임워크
- **Python** 3.8+ (음성처리)
  - `librosa`: 음악 분석
  - `pedalboard`: DSP (Spotify 오픈소스)
  - `Demucs`: Stem 분리

### 아키텍처 (Go + Python 혼합)
```
Go main.go
├── fsnotify → inbox/ 폴더 감시
├── gin → HTTP API + 정적 UI
├── 파일 추가 이벤트 감지
│   └── engine.py 서브프로세스 실행
│       ├── librosa BPM/Key 분석
│       ├── pedalboard 마스터링
│       └── Demucs Stem 분리
└── 결과 JSON → 웹 UI 업데이트
```

### 환경 변수
```
WATCH_DIR=./inbox          # 감시 폴더
OUT_DIR=./output           # 출력 폴더
MAX_PYTHON_PROCS=2         # 동시 Python 프로세스
PYTHON_TIMEOUT_MINUTES=90  # 타임아웃
```

### Go 핵심 설계 (버그 수정 반영)
```go
// graceful shutdown
c := make(chan os.Signal, 1)
signal.Notify(c, syscall.SIGINT, syscall.SIGTERM)
<-c
// 최대 30초 대기 후 종료

// recentEvents 메모리 누수 방지
// 5분 주기 cleanup goroutine
go func() {
    ticker := time.NewTicker(5 * time.Minute)
    for range ticker.C {
        cleanOldEvents()
    }
}()
```

### Python 오류 처리 패턴
```go
// Python 서브프로세스 오류 시 JSON message 추출
if err != nil {
    var pyErr struct{ Message string }
    json.Unmarshal([]byte(stderr), &pyErr)
    // message 없으면 raw stderr 사용
}
```

---

## 4. master_tag

### 기술 스택
- **Python** 3.8+, **Flask** (웹 서버)
- **pedalboard** (Spotify DSP 라이브러리)
- **librosa** (스펙트럼 분석)
- **pyloudnorm** (LUFS 측정)

### 마스터링 체인 (순서 중요)
```
1. 적응형 EQ
   → librosa 스펙트럼 분석 → 주파수 밸런스 교정

2. 글루 컴프레서
   → pedalboard.Compressor
   → threshold=-18dB, ratio=2:1, attack=30ms, release=150ms

3. M/S 스테레오 처리
   → Mid = (L+R)/2, Side = (L-R)/2
   → Side 레벨 조정 → 다시 L/R 변환

4. LUFS 정규화
   → pyloudnorm.Meter → 측정
   → 목표: -14 LUFS (Spotify/YouTube 표준)

5. 브릭월 리미터
   → pedalboard.Limiter
   → threshold=-0.3dBFS (클리핑 방지)
```

### Flask SSE 이벤트 (버그 수정 포함)
```python
# 중복 이벤트 방지
def process_audio(job_id, filepath):
    yield_event(job_id, 'started')    # ← 여기만 발행
    # 'queued' 이벤트 중복 제거됨 (버그 수정)
    for step in MASTERING_CHAIN:
        step.process()
        yield_event(job_id, 'progress', step.name)
    yield_event(job_id, 'completed')
```

---

## 5. lyrics_tag

### 기술 스택
- **Python** 3.8+, **Flask**, **waitress** (프로덕션 WSGI)
- HTML5/CSS/JavaScript (프론트엔드)

### 환경 변수
```
LRC_HOST=127.0.0.1
LRC_PORT=5000
LRC_THREADS=8
LRC_MAX_REQUEST_BYTES=1048576  # 1MB
```

### 타임스탬프 처리 (버그 수정 반영)
```python
# 잘못된 방식 (float 반올림 오버플로우)
timestamp = round(seconds, 2)  # 60.995 → 61.00 오류

# 올바른 방식 (정수 센티초)
centiseconds = int(seconds * 100)
mm = centiseconds // 6000
ss = (centiseconds % 6000) // 100
cs = centiseconds % 100
lrc_timestamp = f"[{mm:02d}:{ss:02d}.{cs:02d}]"
```

### Flask 경로 설정 (버그 수정 반영)
```python
# 잘못된 방식 (상대경로 - 실행 위치에 의존)
app = Flask(__name__)

# 올바른 방식 (절대경로 기준)
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, 'static'))
```

### waitress 실행 패턴
```python
from waitress import serve

if __name__ == '__main__':
    host = os.getenv('LRC_HOST', '127.0.0.1')
    port = int(os.getenv('LRC_PORT', 5000))
    threads = int(os.getenv('LRC_THREADS', 8))
    serve(app, host=host, port=port, threads=threads)
```

---

## 6. 공통 패턴 (음악 도구)

### librosa 오디오 로드 패턴
```python
import librosa

y, sr = librosa.load(filepath, sr=None, mono=True)
duration = librosa.get_duration(y=y, sr=sr)

# BPM
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

# 스펙트럼 분석
chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
rms = librosa.feature.rms(y=y)
```

### pedalboard 마스터링 패턴
```python
from pedalboard import Pedalboard, Compressor, Limiter, HighpassFilter
import soundfile as sf

audio, sr = sf.read(filepath)
board = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=80),
    Compressor(threshold_db=-18, ratio=2.0),
    Limiter(threshold_db=-0.3),
])
processed = board(audio, sr)
sf.write(output_path, processed, sr)
```

### Flask + SSE 실시간 진행률 패턴
```python
from flask import Response
import queue, json

job_queues = {}  # job_id → queue.Queue

@app.route('/api/progress/<job_id>')
def progress(job_id):
    q = job_queues.get(job_id, queue.Queue())
    def generate():
        while True:
            msg = q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg.get('type') == 'completed':
                break
    return Response(generate(), content_type='text/event-stream')
```

### LUFS 정규화 패턴
```python
import pyloudnorm as pyln
import numpy as np

meter = pyln.Meter(sr)
loudness = meter.integrated_loudness(audio)
target_loudness = -14.0  # Spotify/YouTube 표준
gain_db = target_loudness - loudness
gain_linear = 10 ** (gain_db / 20)
normalized = audio * gain_linear
```

### 음악 분석 결과 표준 스키마
```python
@dataclass
class AudioAnalysisResult:
    available: bool
    file_path: str
    duration: float         # 초
    bpm: float
    estimated_key: str      # "C", "Am" 등
    rms_mean: float
    dynamic_range_db: float
    spectral_centroid_mean: float
```

### LRC 형식 표준
```
[mm:ss.cs]가사 텍스트    # cs = 센티초 (2자리)
[00:01.23]첫 번째 가사
[00:05.67]두 번째 가사
[99:59.99]               # 빈 줄 = 공백
```

### SRT 형식 표준
```
1
00:00:01,000 --> 00:00:04,500
첫 번째 가사

2
00:00:05,000 --> 00:00:08,000
두 번째 가사
```
