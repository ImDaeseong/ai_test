# lyrics_tag — 가사 세그먼트 편집기

LRC / SRT 형식의 가사 타임스탬프를 생성·편집하는 Flask 웹앱.  
waitress 프로덕션 서버로 실행.

## 실행

```bash
pip install -r requirements.txt
python app.py
# 브라우저: http://127.0.0.1:5000
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `LRC_HOST` | `127.0.0.1` | 서버 바인드 주소 |
| `LRC_PORT` | `5000` | 포트 |
| `LRC_THREADS` | `8` | waitress 스레드 수 |
| `LRC_MAX_REQUEST_BYTES` | `1048576` | 최대 요청 크기 |

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `app.py:22` | `resource_path`에서 `os.path.abspath(".")` 사용 시 실행 디렉토리에 따라 templates/static 탐색 실패하던 문제 수정 → `os.path.dirname(os.path.abspath(__file__))` 사용 |
| `app.py:83` | LRC 타임스탬프 생성 시 float 반올림으로 `60.00`초 오버플로우 발생하던 문제 수정 → 정수 센티초 변환 방식으로 교체, 표준 2자리 소수점 형식으로 변경 |

### 테스트
- `tests/test_core.py` 신규 작성 — 18개 테스트 전원 통과
- 대상: LRC 타임스탬프 변환, Flask 엔드포인트 정상/오류 케이스
