# HANDOFF - ai-webtoon_capcut

## 현재 목표

곡별 하드코딩 없이 웹툰 이미지·음악·Suno 자막을 분석하고 편집 타임라인을
생성하는 재사용 CLI를 완성한다.

## 먼저 읽을 파일

1. `CLAUDE.md`
2. `README.md`
3. `IMPLEMENTATION.md`
4. `docs/16_THREE_SONG_DESIGN_IMPROVEMENTS_V3.md`
5. `TESTING_DONE_CRITERIA.md`
6. `AI_CODING_REVIEW.md`
7. `HERMES_REVIEW.md`

## 완료

- Python 분석/계획 CLI
- WAV·이미지·스토리보드·LRC/SRT 분석
- 자막 품질 라우팅
- 동적 섹션·타임라인
- CapCut handoff
- 3곡 회귀와 214곡 discover
- Hermes 필수 문서와 자동 검증
- Suno 밀집 섹션 태그 연쇄의 일반화된 경계 재분배
- 기본 경로 `input/{노래명}` → `output/{노래명}/{run_id}`
- 더블클릭 메뉴와 명령 전달을 지원하는 `webtoon-capcut.bat`
- Remotion 기본 무자막 preview MP4와 선택적 자막 검토 영상
- WhisperX 실제 30 cue 정렬 및 CapCut용 원본/보정 SRT 분리
- Demucs 8초 샘플 보컬/반주 분리 검증
- MP3/FLAC/M4A ffprobe 지원 (Remotion 번들 ffprobe 자동 탐색, PATH fallback)
- Remotion 클립 간 크로스페이드 전환 (기본 300ms, config `canvas.transition_ms`로 조정)
- 추가 2곡 end-to-end 검증: SRT_WIDE_TEST(18패널·120s·SRT전용), LRC_PORTRAIT_TEST(24패널·90s·LRC전용)
- CapCut 핸드오프 자동 검증 스크립트 (`scripts/validate-capcut-handoff.ps1`), 전 곡 PASS
- 5곡 전체 재빌드 및 handoff 구조 통일
- full 1080p 렌더 PASS: UPGRADE 1920×1080 H.264/AAC 30fps 242.97s (468 MB)
- 통합 테스트 15개 추가 (`tests/test_fixture_integration.py`), 전체 45 passed

## 미완료

- 사람 CapCut import Q3/Q4 체감 싱크 검수
  - 자동 검증: `scripts/validate-capcut-handoff.ps1` (전 곡 PASS)
  - 남은 것: CapCut 앱에서 SRT import 후 귀로 싱크 확인 (자동화 불가)

## 검증 명령

```powershell
.\scripts\test.ps1
.\scripts\validate-project.ps1
.\scripts\webtoon-capcut.ps1 build --song "곡명"
.\scripts\webtoon-capcut.ps1 render --song "곡명"
.\scripts\webtoon-capcut.ps1 align --song "곡명"
```

## 다음 단계

1. 네 번째·다섯 번째 곡 fixture 추가
2. CapCut에서 자동 보정 SRT 체감 싱크 검수
3. full 1080p 실제 곡 렌더
4. 추가 곡 정렬 회귀

## 알려진 판정

- 분석/계획 및 preview 렌더: PASS WITH LIMITATIONS
- 전체 영상 자동화: HOLD
- 공개/배포: HOLD

2026-06-06 실제 검증:

- 무자막 preview MP4: H.264/AAC, 960x540, 30fps, 목표 길이 1프레임 이내
- WhisperX: 디저트 30 cue 정렬, invalid 0
- Demucs: 8초 샘플 vocals/no_vocals 생성
- full 1080p MP4 (UPGRADE): 1920×1080, H.264/AAC, 30fps, 242.97s, 468MB — PASS
- SRT_WIDE_TEST (18패널·120s·SRT): BUILD_READY → PASS, gap 0, 21 clips
- LRC_PORTRAIT_TEST (24패널·90s·LRC·세로형): BUILD_READY → PASS, gap 0, 24 clips
- 전체 테스트: 45 passed (기존 30 + 통합 15)
