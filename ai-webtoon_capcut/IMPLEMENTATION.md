# 구현 상태

## 현재 구현

- `inspect`: 한 곡의 스토리보드, 이미지, WAV, LRC/SRT 검사
- `discover`: output 루트의 곡 상태 일괄 분류
- `normalize`: 정규화 자막과 분석 산출물 생성
- `plan`: 섹션 및 동적 타임라인 생성
- `build`: inspect부터 CapCut handoff까지 실행
- `build-all`: 준비된 곡을 실패 격리 방식으로 일괄 처리
- `render`: Remotion으로 이미지 모션·원본 음원을 합성한 MP4 생성
- `align`: 선택적으로 Demucs 보컬 분리 후 WhisperX 가사 시간 보정
- WAV와 PNG/JPEG/일부 WebP를 외부 Python 패키지 없이 분석
- Suno 대괄호 metadata 분리
- 장기 cue 상대 통계 탐지와 정렬 라우팅
- 패널 섹션 provenance와 충돌 기록
- Intro/Outro 가장자리 구간 복원
- 혼합 해상도 fit 정책
- timeline JSON/CSV, cleaned SRT, QA 보고서
- stderr JSON Lines 구조화 로그
- Hermes 문서·하드코딩·비밀값·절대 경로 자동 검사
- 기본 무자막 MP4와 선택적 `--burn-subtitles` 검토 영상
- ffprobe 기반 영상·음성 스트림과 1프레임 길이 검증
- CapCut용 원본/자동보정 SRT 분리

## 아직 구현되지 않거나 추가 검증이 필요한 범위

- ffmpeg/ffprobe 기반 MP3/FLAC/M4A 분석
- CapCut 비공개 초안 포맷 작성
- Remotion full 1080p 실제 곡 검증
- 전체 곡 Demucs+WhisperX 결합 회귀

## 실행

프로젝트 루트에서:

```powershell
.\scripts\install-renderer.ps1
.\scripts\install-alignment.ps1
$env:PYTHONPATH="$PWD\src"
python -m webtoon_capcut inspect --song "곡명"
python -m webtoon_capcut build --song "곡명"
python -m webtoon_capcut render --song "곡명"
python -m webtoon_capcut align --song "곡명"
python -m webtoon_capcut build-all --ready-only
```

또는 실행 스크립트를 사용한다.

```powershell
.\scripts\webtoon-capcut.ps1 inspect --song "곡명"
.\scripts\webtoon-capcut.ps1 build --song "곡명"
.\scripts\webtoon-capcut.ps1 render --song "곡명"
.\scripts\webtoon-capcut.ps1 align --song "곡명"
.\scripts\webtoon-capcut.ps1 build-all --ready-only
```

Windows 배치 메뉴 또는 명령 전달:

```bat
webtoon-capcut.bat
webtoon-capcut.bat build --song "곡명"
webtoon-capcut.bat render --song "곡명"
webtoon-capcut.bat build-all --ready-only
```

기본 입력은 `input/{곡명}`이며 결과는 `output/{곡명}/{run_id}`에 생성된다.
기존 외부 폴더를 직접 처리할 때는 `--song-dir`을 사용할 수 있다.

## 테스트

```powershell
$env:PYTHONPATH="$PWD\src"
python -m unittest discover -s tests -v
```

또는:

```powershell
.\scripts\test.ps1
.\scripts\validate-project.ps1
```

Remotion preview와 WhisperX 정렬은 실제 곡에서 검증됐다. 자동 정렬은 초안이며
CapCut 체감 싱크, 영상 품질과 공개 적합성은 사람 검수 전이므로 전체 프로젝트
상태는 `HOLD`다.
