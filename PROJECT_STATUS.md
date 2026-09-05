# 프로젝트 현황 — ai_test

> 마지막 업데이트: 2026-09-06 (아래 "업데이트 기록"의 최신 행 날짜와 항상 동일해야 함)
> 새 프로젝트 추가 또는 주요 변경 시 이 파일을 업데이트한다.

---

## 검증 루프 게이트 현황

**현재: 100%** ✅

| 게이트 | 상태 | 근거 |
|--------|------|------|
| 20% | ✅ | 목적·보안 경계·검증 명령·HOLD 조건 정의됨 |
| 40% | ✅ | 18개 프로젝트 구조 파악, 위험 요소 파악 완료 |
| 60% | ✅ | 구현 완료, README·설계 문서 체계화 |
| 80% | ✅ | CLAUDE.md 18개 완료, 테스트 완료 (ai-webtoon 52, imagevideo 33, lyricvideo 16 포함), HOLD 3개 (extensions/run_game/ai_anime_production — 특수 환경 필요) |
| 90% | ✅ | ai_anime_production 22개·extensions 26개 순수함수 단위 테스트 PASS, run_game은 명시적 검증 범위 예외 |
| 100% | ✅ | run_game MFC 빌드는 기존 검증 데이터로 인정하고 로컬 PASS/HOLD 판정에서 제외 — 나머지 17개 프로젝트 전량 완성 |

---

## 테스트 실행 결과 (2026-06-26)

### ✅ 검증 완료

| 프로젝트 | 언어 | 테스트 수 | 상태 |
|---------|------|---------|------|
| Analysis_music | Python | 67 | PASS |
| weather_alarm | Python | 55 | PASS |
| security_scanning | Python | 53 | PASS |
| mp4_tag | Python | 50 | PASS |
| lyrics_tag | Python | 18 | PASS |
| ai-webtoon_capcut | Python | 14 | PASS |
| findstring_foldfiles | Python | 5 | PASS |
| mp3_daw | Go | ok | PASS |
| check_FileEncoding | Go | ok | PASS |
| Pexels | Python | 23 | PASS |
| master_tag | Python | 18 | PASS |
| windows-port-monitor | Python | 7 | PASS |

> 과거 "부분 검증(pytest 임시 디렉토리 권한 차단)" 항목은 해소되어 전량 PASS로 통합함 (2026-07-20 재검증).

### ⚪ 검증 범위 예외

| 프로젝트 | 예외와 재검토 조건 |
|---------|------------------|
| run_game | 2026-05-28 Debug/Release 빌드 검증 데이터 인정. 로컬 MFC 설치·빌드는 판정에서 제외하며, C++ 소스·프로젝트·솔루션·번들 라이브러리 변경 시 사람 검토 재개 |

> ai_anime_production·extensions: 순수 함수 단위 테스트로 전환 완료 (2026-06-28)

---

## 의존성 설치 이력 (2026-06-26)

테스트 실행 중 누락된 패키지 발견 및 설치:

| 패키지 | 사용 프로젝트 |
|--------|-------------|
| aiohttp | weather_alarm |
| loguru | weather_alarm |
| discord.py | weather_alarm |
| python-telegram-bot | weather_alarm |
| pytest-asyncio | weather_alarm |
| psutil | windows-port-monitor |
| PyYAML | windows-port-monitor |
| pywin32 | windows-port-monitor |
| ai-webtoon_capcut (editable) | ai-webtoon_capcut |

---

## 프로젝트 목록

| 프로젝트 | 목적 | 언어 | CLAUDE.md | 테스트 | 상태 |
|---------|------|------|-----------|--------|------|
| Analysis_music | 음악 분석 자동화 | Python | ✅ | ✅ 67 | ✅ 완성 |
| ai-webtoon | 웹툰 생성 Flask 앱 | Python | ✅ | ✅ 52 | ✅ 완성 |
| ai-webtoon_capcut | 웹툰 CapCut 타임라인 생성 | Python | ✅ | ✅ 14 | 🟡 부분완성 (CLI 완료, Remotion 렌더러·CapCut 패키징 미구현 HOLD — README.md 참고) |
| ai_anime_production | 애니메이션 영상 제작 | Node.js | ✅ | ✅ 22 | ✅ 완성 (순수함수) |
| check_FileEncoding | 파일 인코딩 검사 | Go | ✅ | ✅ ok | ✅ 완성 |
| extensions | Chrome 확장 (Suno 자동화) | JS | ✅ | ✅ 26 | ✅ 완성 (순수함수) |
| findstring_foldfiles | 폴더 내 문자열 검색 | Python | ✅ | ✅ 5 | ✅ 완성 |
| imagevideo | 이미지→영상 변환 | Node.js | ✅ | ✅ 33 | ✅ 완성 |
| lyrics_tag | 가사 태그 관리 | Python | ✅ | ✅ 18 | ✅ 완성 |
| lyricvideo | 가사 영상 생성 | Node.js | ✅ | ✅ 16 | ✅ 완성 |
| master_tag | 마스터 오디오 태그 | Python | ✅ | ✅ 18 | ✅ 완성 |
| mp3_daw | MP3 DAW 연동 | Go | ✅ | ✅ ok | ✅ 완성 |
| mp4_tag | MP4 메타태그 관리 | Python | ✅ | ✅ 50 | ✅ 완성 |
| Pexels | Pexels API 이미지 수집 | Python | ✅ | ✅ 23 | ✅ 완성 |
| run_game | 게임 런처 | C++/MFC | ✅ | 범위 제외 | 기존 빌드 검증 데이터 인정; 관련 파일 변경 시 재검토 |
| security_scanning | 보안 취약점 스캔 | Python | ✅ | ✅ 53 | ✅ 완성 |
| weather_alarm | 날씨 알림 봇 | Python | ✅ | ✅ 55 | ✅ 완성 |
| windows-port-monitor | 포트 모니터링 | Python | ✅ | ✅ 7 | ✅ 완성 |

---

## 알려진 미해결 이슈

| 프로젝트 | 이슈 | 우선순위 |
|---------|------|---------|
| run_game | 로컬 MFC 빌드는 검증 범위 제외; C++ 소스·프로젝트 설정 변경 시 사람 검토 재개 | P3 예외 |
| ai-webtoon_capcut | Remotion 렌더러·CapCut 패키징 미구현 (HOLD, 설계 범위 밖 대형 기능 — README.md 참고) | HOLD |

---

## 업데이트 기록

| 날짜 | 변경 내용 |
|------|---------|
| 2026-06-26 | 검증 루프 최초 적용 — 18개 프로젝트 분석, 테스트 전량 실행, 의존성 누락 수정 |
| 2026-06-28 | CLAUDE.md 15개 작성 완료 (weather_alarm 포함 전체), ai-webtoon 52개·imagevideo 33개·lyricvideo 16개 테스트 작성 및 전량 PASS, 80% 게이트 달성 |
| 2026-06-28 | ai_anime_production parsers.mjs 추출 22개·extensions lyricUtils.js 추출 26개 테스트 전량 PASS, run_game 영구 HOLD 문서화, 90% 게이트 달성 |
| 2026-06-28 | run_game 영구 HOLD 정식 처리 (Visual Studio 빌드 환경 의존), 검증 루프 100% 완료 |
| 2026-06-29 | 헤르메스 감시 재검증. ai-webtoon_capcut: editable 미설치로 3 ImportError → pip install -e . 후 14 passed 복구. P1 이슈 등재. |
| 2026-07-20 | 전체 재검증. ai-webtoon: `pytest.ini` 누락으로 bare `pytest -q`가 0개 수집하던 결함 수정(52 passed 확인). Pexels(23)·master_tag(18)·windows-port-monitor(7) "부분 검증(pytest 임시폴더 권한 차단)" 상태 재확인 결과 전량 PASS로 해소되어 P2 이슈 제거. root README.md의 ai-webtoon 스테일 테스트 수(41→52) 정정. |
| 2026-07-29 | 사용자 결정으로 `run_game` MFC 빌드를 로컬 전체 검증의 PASS/HOLD 판정에서 제외. 2026-05-28 검증 데이터를 인정하되 C++ 소스·프로젝트·솔루션·번들 라이브러리 변경 시 예외를 해제하고 사람 검토를 재개. |
| 2026-08-17 | 전체 재검증 루프. 17개 프로젝트(run_game 제외) 테스트 전량 재실행 — Python 11개(Analysis_music 67·ai-webtoon 52·ai-webtoon_capcut 14·findstring_foldfiles 5·lyrics_tag 18·master_tag 18·mp4_tag 50·Pexels 23·security_scanning 53·weather_alarm 55·windows-port-monitor 7) 전량 PASS, Go 2개(check_FileEncoding·mp3_daw) 전량 PASS, Node 4개(ai_anime_production 22·extensions 26·imagevideo 33·lyricvideo 16) 전량 PASS. 18개 CLAUDE.md 전량 존재 확인, `git status` 클린 확인(사이드이펙트 없음). 이전 100% 게이트 대비 회귀 없음. |
| 2026-08-17 | ai-webtoon_capcut 문서-스크립트 불일치 결함 수정. README.md·IMPLEMENTATION.md가 참조하던 `scripts/install-renderer.ps1`(remotion npm install)·`scripts/install-alignment.ps1`(WhisperX/Demucs pip install)이 실제로 존재하지 않아 문서대로 따라가면 실패하던 결함 발견 및 두 스크립트 신설. 동시에 `test.ps1`에만 있던 editable-install 자동 감지·복구 로직을 `webtoon-capcut.ps1`(실사용 CLI 래퍼)에도 동일 적용해 신규 환경에서 ModuleNotFoundError로 실패하던 P1 이슈 해소. pytest 14 passed 재확인, `webtoon-capcut.ps1` 실행 exit 0 확인. |
| 2026-08-17 | ai-webtoon_capcut 문서 허위 완료 표시 정정. `HANDOFF.md`·`HERMES_REVIEW.md`·`TESTING_DONE_CRITERIA.md`가 Remotion 렌더(full 1080p PASS)·WhisperX/Demucs 정렬·CapCut handoff 자동 검증 스크립트·테스트 45개를 "완료"로 기록하고 있었으나, 코드 확인 결과 `remotion/`에 컴포지션 소스가 없고 CLI에 `render`/`align` 명령이 없고 검증 스크립트가 없고 테스트는 14개임을 확인(`git log`상 이 문서들은 2026-06-07 단일 import 커밋 이후 미변경 — 다른 환경 작업 기록이 코드 없이 문서만 넘어온 것으로 추정). 4개 문서와 `README.md`의 실행 예제(`render`/`align` 명령)를 코드 기준으로 정정, 원문은 삭제 대신 스테일 표시로 보존. |
| 2026-09-06 | 로컬 자동 검증 대상 17개 하위 프로젝트 PASS. weather_alarm import 시 로그 쓰기·stdout 교체 부작용을 시작 시 초기화로 변경하고 subprocess 회귀 검사 추가: 56 PASS. Python 나머지 10개·Go 2개·Node 4개 통과, anime/lyricvideo 타입 검사 및 확장 빌드 통과. 실제 API·전체 렌더·사람 검토는 기존 범위 유지. |
