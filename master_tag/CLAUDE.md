# Claude Code Instructions — master_tag

## 프로젝트 목적

Pedalboard + Librosa + pyloudnorm 기반 오디오 마스터링 도구.
파이프라인: 적응형 EQ → 글루 컴프레서 → M/S 스테레오 처리 → LUFS 정규화 → 브릭월 리미터.

## 구조

```
server.py        # Flask SSE 서버 (작업 큐 + 이벤트 스트림)
main.py          # CLI 진입점
outputs/         # 마스터링 결과 파일
tests/           # pytest 테스트 (18개)
```

## 실행

```bash
pip install -r requirements.txt
python server.py
# 브라우저: http://127.0.0.1:5000
```

## 테스트

```bash
pytest tests/ -v
```

## 주의사항

- `/master` 엔드포인트에서 "queued" 이벤트 발행 — `_run_job`에서 중복 발행 금지
- LUFS 목표값은 설정으로 노출 — 하드코딩 금지
- SSE 이벤트 순서: queued → processing → done/error
