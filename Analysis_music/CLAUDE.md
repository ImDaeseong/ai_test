# Claude Code Instructions — Analysis_music

## 프로젝트 목적

Suno AI 음악 프롬프트를 분석하여 BPM/Key/섹션/가사를 파싱하고
LilyPond 악보·음악 분석 보고서·시각 콘텐츠 프롬프트를 자동 생성하는 Flask 웹앱.

## 구조

```
main.py          # CLI 진입점
web/app.py       # Flask 앱 진입점
config.py        # 전역 설정
analyzer/        # 파싱 로직 (BPM, Key, 섹션, 가사)
generators/      # 출력 생성 (LilyPond, 분석 보고서, 프롬프트)
tests/           # pytest 테스트 (67개)
```

## 실행

```bat
run_web.bat          # Flask 웹 UI
python web/app.py    # 직접 실행
```

## 테스트

```bash
pytest tests/ -v
```

67개 테스트 전원 통과 기준. 키 정규화·박자 파싱·코드 추출·섹션 파싱·가사 처리 커버.

## 주의사항

- 파싱 로직 수정 시 `analyzer/` 내 해당 모듈과 `tests/test_core.py` 동시 확인
- LilyPond 생성 로직은 `generators/` 내 위치
- `config.py`에 하드코딩된 값 추가 금지 — 환경 변수 또는 파라미터로 처리
