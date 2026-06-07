# 개발 계획과 코딩 규칙

## 1. 기술 방향

### 권장 스택

| 영역 | 기술 | 이유 |
|---|---|---|
| 오케스트레이션/파싱 | Python 3.11 | 기존 `ai-webtoon`과 친화적, 파일·오디오 도구 연동 용이 |
| 데이터 검증 | Pydantic 또는 dataclass + 명시 검증 | JSON 계약과 오류 메시지 일관성 |
| 미디어 정보 | ffprobe | 실제 음악 길이와 코덱 확인 |
| 영상 합성 | Node.js LTS + TypeScript + Remotion | 데이터 기반 영상 구성과 반복 렌더링 |
| 테스트 | pytest, Vitest | Python과 TypeScript 경계별 테스트 |
| 선택 자막 정렬 | 보컬 분리기 + WhisperX 계열 | 최종 음원 기준 재정렬 |

정확한 버전은 구현 시작 시 공식 문서, Windows 호환성, 라이선스, 최근 유지보수 상태를 확인한 뒤 고정한다. 검증하지 않은 버전 번호를 설계 문서에서 확정하지 않는다.

## 2. 모듈 구조

```text
src/webtoon_capcut/
├── cli.py
├── config.py
├── models.py
├── errors.py
├── logging_setup.py
├── input_resolver.py
├── validators.py
├── storyboard_parser.py
├── subtitle_parser.py
├── audio_probe.py
├── alignment/
│   ├── base.py
│   ├── basic.py
│   └── forced.py
├── timeline/
│   ├── normalizer.py
│   ├── section_allocator.py
│   └── frame_rounding.py
├── remotion_bridge.py
├── package_builder.py
└── reports.py
```

```text
remotion/src/
├── Root.tsx
├── compositions/WebtoonMv.tsx
├── components/PanelClip.tsx
├── components/SubtitleLayer.tsx
├── motion/presets.ts
├── schema/timeline.ts
└── tests/
```

## 3. 코딩 규칙

1. 하나의 함수나 클래스는 하나의 역할만 맡는다.
2. CLI, 파싱, 타임라인 계산, 렌더 호출을 한 파일에 몰아넣지 않는다.
3. 하드코딩된 절대 경로를 금지한다.
4. Windows 한글 파일명, 공백 경로를 기본 테스트 조건으로 본다.
5. subprocess는 인자 배열과 명시적 timeout을 사용한다.
6. 모든 외부 도구 실행 결과는 종료 코드와 stderr를 검사한다.
7. 광범위한 `except Exception: pass`를 금지한다.
8. 설정 기본값은 `config/`에 두고 코드 상수는 포맷·스키마 불변값으로 제한한다.
9. Markdown 파싱은 정규식 한 줄에 의존하지 않고 표 헤더와 행 구조를 검증한다.
10. 시간 계산에는 float 초를 누적하지 않고 정수 밀리초 또는 프레임을 사용한다.
11. 원본 파일에 쓰지 않는다. 모든 출력은 실행별 작업 폴더에 만든다.
12. 로그와 사용자 보고서를 분리한다.
13. 임시 파일은 성공 시 정리하되 실패 분석에 필요한 파일은 실행 ID 아래 보존한다.
14. 공개 함수에는 타입 힌트와 짧은 docstring을 작성한다.
15. 주석은 이유와 제약을 설명할 때만 사용한다.

## 4. CLI 초안

```powershell
# 입력 검사
python -m webtoon_capcut inspect --song "100 Seconds" --source-root "..\ai-webtoon"

# 타임라인 생성
python -m webtoon_capcut plan --manifest "workspace\100-seconds\project.json"

# 자막 재정렬 포함
python -m webtoon_capcut align --manifest "workspace\100-seconds\project.json" --strategy forced

# 미리보기 렌더
python -m webtoon_capcut render --manifest "workspace\100-seconds\project.json" --profile preview

# CapCut 전달 패키지 생성
python -m webtoon_capcut package --manifest "workspace\100-seconds\project.json"

# 전체 흐름
python -m webtoon_capcut build --manifest "workspace\100-seconds\project.json"
```

각 명령은 `--dry-run`을 지원해야 한다. `--force` 없이 기존 완료 산출물을 덮어쓰지 않는다.

## 5. 구현 Task

| Task | 목적 | 주요 파일 | 완료 기준 | 검증 방법 |
|---|---|---|---|---|
| T01 | 프로젝트 골격과 스키마 | `pyproject.toml`, `models.py`, timeline schema | 샘플 manifest와 timeline 로드 가능 | 스키마 단위 테스트 |
| T02 | 입력 탐색과 안전 검증 | `input_resolver.py`, `validators.py` | 한글·공백 경로, 중복 음악, 누락 파일 판정 | fixture 기반 pytest |
| T03 | 스토리보드 파싱 | `storyboard_parser.py` | 실제 `01_storyboard.md`를 구조화 | 3곡 이상 회귀 테스트 |
| T04 | LRC/SRT 공통 파싱 | `subtitle_parser.py` | cue 정렬, UTF-8, 중복/역전 시간 검출 | 정상·깨진 파일 테스트 |
| T05 | 오디오 길이 측정 | `audio_probe.py` | MP3/WAV 길이를 ms로 반환 | ffprobe fixture 비교 |
| T06 | 타임라인 정규화 | `timeline/*` | 최종 종료가 음악 길이와 프레임 오차 이내 일치 | 속성 기반 테스트 |
| T07 | 이미지 부족·과다 정책 | `section_allocator.py` | 재사용·제외가 결정론적으로 기록됨 | 경계값 테스트 |
| T08 | Remotion 데이터 브리지 | `remotion_bridge.py`, TS schema | Python JSON과 TS 검증 일치 | 양쪽 schema 테스트 |
| T09 | Remotion 기본 렌더 | `WebtoonMv.tsx` 등 | 이미지, 음악, 모션, 전환 포함 MP4 생성 | 30초 fixture 렌더 |
| T10 | 전달 패키지와 보고서 | `package_builder.py`, `reports.py` | SRT, JSON, QA 보고서가 한 폴더에 생성 | 스냅샷 테스트 |
| T11 | 기본 자막 보정 | `alignment/basic.py` | 전체 오프셋·비율 오차 탐지 및 후보 생성 | 합성 cue 테스트 |
| T12 | 강제 정렬 실험 | `alignment/forced.py` | 보컬 분리·인식·원문 매칭 결과와 신뢰도 출력 | 선정 샘플 수동 비교 |
| T13 | 통합 CLI | `cli.py` | inspect→plan→render→package 실행 | end-to-end fixture |
| T14 | 문서와 검증 상태 | README, QA 문서 | 실제 명령과 상태가 문서와 일치 | 검수 체크리스트 |

## 6. 구현 순서

### Milestone 1: 데이터와 타임라인

T01 → T02 → T03 → T04 → T05 → T06 → T07

완료 조건:

- 실제 음악, 실제 스토리보드, 임시 이미지로 `timeline.json` 생성
- 영상 길이가 음악과 일치
- 렌더러 없이도 계산 결과를 검증 가능

### Milestone 2: Remotion 렌더

T08 → T09 → T10 → T13

완료 조건:

- 30초 샘플과 1곡 전체 미리보기 렌더 성공
- SRT와 CapCut 전달 패키지 생성
- 원본 파일 변경 없음

### Milestone 3: 자막 재정렬

T11 → T12

완료 조건:

- 정상 LRC/SRT는 불필요하게 재작성하지 않음
- 리믹스 샘플에서 기존 자막보다 개선되었는지 사람이 평가
- 저신뢰 cue를 자동 확정하지 않음

### Milestone 4: 회귀와 운영

T14 및 다곡 샘플 반복

완료 조건:

- 느린 곡, 빠른 곡, 리믹스 곡, 한글 제목, 영문 제목을 포함한 회귀 세트 통과
- README에 검증 명령과 실제 결과 기록

## 7. AI와 사람의 역할

### AI가 구현 가능한 작업

- 파서와 스키마 작성
- 타임라인 계산
- 테스트 fixture와 자동 테스트
- Remotion 컴포지션
- 보고서 생성
- 반복 가능한 검증 명령

### 사람이 판단해야 하는 작업

- 자막이 실제 가창과 자연스럽게 맞는지
- 반복 가사와 애드리브를 자막에 포함할지
- 이미지 재사용이 지루하거나 부자연스럽지 않은지
- 코러스와 감정 절정의 컷 전환 품질
- CapCut 최종 효과, 색보정, 음량
- 외부 도구 라이선스와 배포 범위

## 8. 수정 금지 및 보호 영역

- `ai-webtoon/output` 기존 결과물
- `ai-webtoon/input` 원본 곡 정보
- 실제 음악, LRC, SRT, 생성 이미지
- `.env`
- 사용자 승인 없는 CapCut 프로젝트 폴더

필요한 입력은 복사하거나 읽기 전용 참조한다.

## 9. 완료 규칙

기능은 다음 조건을 모두 만족해야 완료다.

- 코드가 존재한다.
- 자동 테스트가 있다.
- 실제 샘플로 실행했다.
- 명령과 결과를 문서에 기록했다.
- 실패 케이스를 확인했다.
- 사람이 출력물을 검수했다.
- 원본 파일이 변경되지 않았다.
- 알려진 한계가 기록되었다.

