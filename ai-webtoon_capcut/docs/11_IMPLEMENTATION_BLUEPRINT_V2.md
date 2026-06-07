# 구현 청사진 V2

## 1. 구현 범위 확정

### MVP에 포함

- Windows 로컬 CLI
- 한 곡 inspect, normalize, plan
- output 루트 discover
- 여러 이미지 수와 음악 길이 처리
- LRC/SRT 비교와 Suno 메타데이터 정리
- 스토리보드 및 원본 TXT 기반 섹션 정렬
- timeline JSON/CSV
- 정리 SRT와 검수 보고서
- Remotion 전체 미리보기
- CapCut 전달 패키지

### MVP에서 제외

- GUI
- CapCut 초안 내부 JSON 생성
- 유료 API
- 모든 곡 자동 강제 정렬
- 이미지 생성
- AI 영상 생성

## 2. 프로젝트 구조

```text
ai-webtoon_capcut/
├── README.md
├── pyproject.toml
├── package.json
├── package-lock.json
├── config/
│   ├── default.yaml
│   ├── section_aliases.yaml
│   ├── subtitle_tags.yaml
│   └── motion_presets.yaml
├── schemas/
│   ├── manifest.schema.json
│   ├── inventory.schema.json
│   ├── subtitles.schema.json
│   ├── sections.schema.json
│   └── timeline.schema.json
├── src/webtoon_capcut/
├── remotion/
│   ├── package.json
│   └── src/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── fixtures/
├── scripts/
├── workspace/
│   └── .gitkeep
└── docs/
```

## 3. CLI 계약

```powershell
# 곡 상태 점검
python -m webtoon_capcut inspect --song-dir "...\output\곡명"

# output 전체 준비 상태 목록
python -m webtoon_capcut discover --output-root "...\output"

# 자막과 섹션 정규화
python -m webtoon_capcut normalize --song-dir "...\output\곡명"

# 타임라인 생성
python -m webtoon_capcut plan --manifest "...\manifest.json"

# 저해상도 미리보기
python -m webtoon_capcut render --manifest "...\manifest.json" --profile preview

# CapCut 전달 패키지
python -m webtoon_capcut package --manifest "...\manifest.json"

# 전체 처리
python -m webtoon_capcut build --song-dir "...\output\곡명"

# 준비된 곡 배치
python -m webtoon_capcut build-all --output-root "...\output" --ready-only
```

공통 옵션:

```text
--workspace
--config
--dry-run
--force
--json
--log-level
```

## 4. 오류 코드

| 코드 | 의미 |
|---|---|
| `STORYBOARD_MISSING` | 스토리보드 없음 |
| `AUDIO_MISSING` | 음악 없음 |
| `AUDIO_AMBIGUOUS` | 음악 후보 여러 개 |
| `IMAGE_MISSING` | 패널 이미지 누락 |
| `IMAGE_AMBIGUOUS` | 같은 패널 이미지 여러 개 |
| `IMAGE_INVALID` | 손상 또는 지원하지 않는 이미지 |
| `SUBTITLE_INVALID` | LRC/SRT 파싱 실패 |
| `SECTION_LOW_CONFIDENCE` | 섹션 경계 신뢰도 부족 |
| `TIMELINE_INVALID` | 길이, 빈 구간, 역전 오류 |
| `RENDER_FAILED` | Remotion 실패 |
| `PATH_OUTSIDE_ROOT` | 허용 루트 밖 경로 |
| `REVIEW_HOLD` | 사람 승인 전 진행 금지 |

## 5. 구현 순서

### M1: 스키마와 도메인

작업:

- JSON schema
- Python 모델과 enum
- 설정 로더
- 오류 코드
- 경로 안전 함수

완료:

- 모든 예제 JSON이 Python과 JSON schema 양쪽에서 검증됨

### M2: Discover와 Inventory

작업:

- 곡 폴더 탐색
- 파일 후보 수집
- 패널 이미지 매칭
- WAV 및 이미지 무결성 검사
- 준비 상태 판정

완료:

- 214곡을 수정 없이 스캔
- 현재 UPGRADE는 `BUILD_READY`
- 미디어 없는 곡은 `PROMPTS_ONLY`

### M3: Storyboard와 Song TXT

작업:

- Markdown 표 파서
- 섹션 alias 정규화
- `input/{곡명}.txt` 파서
- 반복 섹션 occurrence 계산

완료:

- 214개 스토리보드 파싱
- 발견된 모든 섹션 라벨을 손실 없이 처리

### M4: Subtitle Normalization

작업:

- LRC/SRT 파서
- 후보 품질 점수
- Suno 대괄호 분류
- 초반 프롬프트 블록 탐지
- 중복과 장기 cue 이슈 생성

완료:

- UPGRADE 회귀 fixture 통과
- 원본을 변경하지 않고 normalized 결과 생성

### M5: Section Boundary Resolver

작업:

- 명시 sidecar
- trusted section cue
- 원본 TXT와 cue 시퀀스 매칭
- storyboard weight 폴백
- 신뢰도 계산

완료:

- 전략별 source와 confidence 기록
- 경계가 불명확하면 자동 확정하지 않음

### M6: Timeline Planner

작업:

- 동적 컷 길이
- 이미지 부족·과다 정책
- 자동 반복 횟수
- 모션 프리셋
- 프레임 반올림

완료:

- 이미지 20~63장 fixture 처리
- 임의 음악 길이에서 마지막 프레임 일치

### M7: Remotion

작업:

- timeline schema 검증
- 이미지와 오디오 로딩
- 모션, 전환, 자막
- preview/full 프로필

완료:

- 30초 fixture 렌더
- UPGRADE 전체 preview 렌더

### M8: Package와 Batch

작업:

- CapCut handoff
- 곡별 QA 보고서
- batch summary
- 실패 곡 재실행

완료:

- 최소 5곡 end-to-end
- 한 곡 실패가 다른 곡에 영향 없음

## 6. 함수 수준 계약

```text
discover_songs(output_root) -> list[SongCandidate]
resolve_assets(song_dir, config) -> AssetInventory
parse_storyboard(path) -> Storyboard
parse_song_source(path) -> SongStructure
parse_subtitles(paths) -> list[SubtitleDocument]
normalize_subtitles(documents, audio, config) -> NormalizedSubtitles
resolve_sections(storyboard, song_structure, subtitles, audio) -> SectionTimeline
plan_timeline(storyboard, inventory, sections, audio, policy) -> EditTimeline
validate_timeline(timeline) -> ValidationReport
render_timeline(manifest, profile) -> RenderResult
build_handoff(run) -> HandoffPackage
```

모든 함수는 전역 경로와 전역 곡 상태에 의존하지 않는다.

## 7. 코딩 규칙 보강

- 곡명 문자열 비교로 로직을 분기하지 않는다.
- `if title == "UPGRADE"` 같은 코드는 테스트에서도 금지한다.
- 숫자 42, 242952 같은 샘플 값은 fixture 안에서만 사용한다.
- 파서 출력과 정책 입력을 구분한다.
- 재사용 정책은 순수 함수로 구현한다.
- subprocess는 timeout, 종료 코드, stderr를 검사한다.
- 입력 후보 충돌은 조용히 선택하지 않는다.
- 파일 삭제는 workspace run 폴더 안에서만 허용한다.
- batch 처리에서 곡별 예외를 구조화해 기록한다.

## 8. 구현 완료 조건

다음이 모두 충족되어야 “재사용 프로그램”으로 판정한다.

- UPGRADE 외 최소 4곡에 이미지·음악·자막을 준비해 처리
- 총 5곡 이상의 panel 수와 길이가 서로 다름
- 최소 1곡은 LRC만, 1곡은 SRT만, 1곡은 둘 다 존재
- 최소 1곡은 Remix/Extend 또는 긴 연주 구간
- 곡별 소스 코드 수정 없이 동일 명령 사용
- timeline 종료와 오디오 종료가 1프레임 이내
- 원본 해시 불변
- `HOLD` 항목을 사람이 승인하기 전 최종 상태 PASS 금지

