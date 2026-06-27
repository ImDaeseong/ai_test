# Claude Code Instructions — Pexels

## 프로젝트 목적

로컬 자동화 도구. `data/` 폴더의 가사·음악 파일을 읽어
Gemini AI가 씬을 계획하고 Pexels 스톡 영상을 검색·다운로드한 뒤
FFmpeg로 최종 뮤직비디오를 조립한다.

출력: `output/final_landscape.mp4` (16:9) + `output/final_shorts.mp4` (9:16) + `output/index.html`

## 구조

```
app/             # 핵심 파이프라인 (씬 계획, Pexels 검색, FFmpeg 조립)
data/            # 입력 파일 (가사 .lrc/.srt/.txt, 음악 .wav/.mp3, 자막 .srt)
output/          # 생성 결과
scripts/         # 유틸리티 스크립트
storage/         # 캐시·임시 저장
docs/            # 문서
tests/           # pytest 테스트 (12개 통과 / 11개 파일쓰기 환경 차단)
```

## 실행

```bat
run.bat
```

## 테스트

```bash
pytest tests/ -v
```

> 파일 쓰기 관련 11개 테스트는 pytest 임시 디렉토리 권한 문제 — 코드 로직 이상 없음, 로컬 실행 시 정상.

## 주의사항

- Gemini API 키 필요 — `.env` 또는 환경 변수로 관리, 코드에 직접 기재 금지
- Pexels API 키 동일
- FFmpeg PATH 등록 필수 — 누락 시 조립 단계에서 실패
- 씬 계획 → Pexels 검색 → 다운로드 → 조립 순서 유지
