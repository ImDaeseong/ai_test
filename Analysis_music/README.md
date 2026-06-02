# Analysis_music — Suno AI 음악 프롬프트 분석기

Suno AI 음악 프롬프트를 분석하여 BPM/Key/섹션/가사를 파싱하고  
LilyPond 악보·음악 분석 보고서·시각 콘텐츠 프롬프트를 자동 생성하는 Flask 웹앱.

## 실행

```bat
run_web.bat
```

또는

```bash
pip install -r requirements.txt
python web/app.py
```

## 개선 이력 (2026-06-02)

### 테스트
- `tests/test_core.py` 신규 작성 — 67개 테스트 전원 통과
- 대상: 키 정규화, 박자 파싱, 코드 추출, 기본 진행, 스타일 디스크립터, 메타데이터 파싱, 섹션 파싱, 가사 처리, 프롬프트 데이터, 헬퍼 함수
