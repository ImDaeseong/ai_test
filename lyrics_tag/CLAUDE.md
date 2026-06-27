# Claude Code Instructions — lyrics_tag

## 프로젝트 목적

LRC / SRT 형식의 가사 타임스탬프를 생성·편집하는 Flask 웹앱.
waitress 프로덕션 서버로 실행.

## 구조

```
app.py           # Flask 앱 진입점 (waitress 서버 포함)
static/          # 프론트엔드 에셋
templates/       # Jinja2 HTML 템플릿
tests/           # pytest 테스트 (18개)
```

## 실행

```bash
pip install -r requirements.txt
python app.py
# 브라우저: http://127.0.0.1:5000
```

## 테스트

```bash
pytest tests/ -v
```

## 환경 변수

| 변수 | 기본값 |
|------|--------|
| `LRC_HOST` | `127.0.0.1` |
| `LRC_PORT` | `5000` |
| `LRC_THREADS` | `8` |
| `LRC_MAX_REQUEST_BYTES` | `1048576` |

## 주의사항

- waitress 서버 설정은 환경 변수로만 조정 — 코드 내 하드코딩 금지
- LRC/SRT 타임스탬프 파싱 로직 수정 시 `tests/` 동시 확인
