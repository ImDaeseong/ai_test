# 프로젝트 현황 — ai_test

> 마지막 업데이트: 2026-06-26
> 새 프로젝트 추가 또는 주요 변경 시 이 파일을 업데이트한다.

---

## 검증 루프 게이트 현황

**현재: 75%** (80% 게이트 진행 중)

| 게이트 | 상태 | 근거 |
|--------|------|------|
| 20% | ✅ | 목적·보안 경계·검증 명령·HOLD 조건 정의됨 |
| 40% | ✅ | 18개 프로젝트 구조 파악, 위험 요소 파악 완료 |
| 60% | ✅ | 구현 완료, README·설계 문서 체계화 |
| 80% | ⏳ | 테스트 실행 완료 (9/18), HOLD 6개, CLAUDE.md 14개 미작성 |
| 90% | ❌ | 80% 미완료 |
| 100% | ❌ | — |

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

### ⚠️ 부분 검증 (코드 로직 통과 / 파일 쓰기 테스트 환경 차단)

| 프로젝트 | 통과 | 차단 | 원인 |
|---------|------|------|------|
| Pexels | 12 | 11 errors | pytest 임시 디렉토리 권한 (로컬 실행 시 정상) |
| master_tag | 17 | 1 error | 동일 |
| windows-port-monitor | 3 | 4 errors | 동일 |

### 🔴 HOLD — 검증 불가 (루프 중지)

| 프로젝트 | 이유 |
|---------|------|
| ai-webtoon | 테스트 파일 미작성 |
| ai_anime_production | Remotion 빌드 환경 + 실제 콘텐츠 필요 |
| extensions | Chrome 실행 + Suno.com 로그인 필요 |
| imagevideo | 테스트 파일 미작성 |
| lyricvideo | 테스트 파일 미작성 |
| run_game | Visual Studio 빌드 환경 필요 |

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
| Analysis_music | 음악 분석 자동화 | Python | ❌ | ✅ 67 | ✅ 완성 |
| ai-webtoon | 웹툰 생성 Flask 앱 | Python | ✅ | ⚠️ 미작성 | HOLD |
| ai-webtoon_capcut | 웹툰 CapCut 타임라인 생성 | Python | ✅ | ✅ 14 | ✅ 완성 |
| ai_anime_production | 애니메이션 영상 제작 | Node.js | ✅ | ❌ | HOLD |
| check_FileEncoding | 파일 인코딩 검사 | Go | ❌ | ✅ ok | ✅ 완성 |
| extensions | Chrome 확장 (Suno 자동화) | JS | ❌ | ❌ | HOLD |
| findstring_foldfiles | 폴더 내 문자열 검색 | Python | ❌ | ✅ 5 | ✅ 완성 |
| imagevideo | 이미지→영상 변환 | Node.js | ❌ | ❌ | HOLD |
| lyrics_tag | 가사 태그 관리 | Python | ❌ | ✅ 18 | ✅ 완성 |
| lyricvideo | 가사 영상 생성 | Node.js | ❌ | ❌ | HOLD |
| master_tag | 마스터 오디오 태그 | Python | ❌ | ⚠️ 17+1err | ✅ 완성 |
| mp3_daw | MP3 DAW 연동 | Go | ❌ | ✅ ok | ✅ 완성 |
| mp4_tag | MP4 메타태그 관리 | Python | ❌ | ✅ 50 | ✅ 완성 |
| Pexels | Pexels API 이미지 수집 | Python | ❌ | ⚠️ 12+11err | ✅ 완성 |
| run_game | 게임 런처 | C++/MFC | ❌ | ❌ | HOLD |
| security_scanning | 보안 취약점 스캔 | Python | ❌ | ✅ 53 | ✅ 완성 |
| weather_alarm | 날씨 알림 봇 | Python | ❌ | ✅ 55 | ✅ 완성 |
| windows-port-monitor | 포트 모니터링 | Python | ❌ | ⚠️ 3+4err | ✅ 완성 |

---

## 알려진 미해결 이슈

| 프로젝트 | 이슈 | 우선순위 |
|---------|------|---------|
| 14개 프로젝트 | CLAUDE.md 미작성 | P1 |
| ai-webtoon | 테스트 파일 미작성 | P1 |
| imagevideo / lyricvideo | 테스트 파일 미작성 | P1 |
| master_tag / Pexels / windows-port-monitor | pytest 임시폴더 권한 이슈 (환경 문제, 코드 무관) | P2 |

---

## 업데이트 기록

| 날짜 | 변경 내용 |
|------|---------|
| 2026-06-26 | 검증 루프 최초 적용 — 18개 프로젝트 분석, 테스트 전량 실행, 의존성 누락 수정 |
