# 구현 상태

## 현재 구현

- `inspect`: 한 곡의 스토리보드, 이미지, WAV, LRC/SRT 검사
- `discover`: output 루트의 곡 상태 일괄 분류
- `normalize`: 정규화 자막과 분석 산출물 생성
- `plan`: 섹션 및 동적 타임라인 생성
- `build`: inspect부터 타임라인 생성까지 실행
- `build-all`: 준비된 곡을 실패 격리 방식으로 일괄 처리
- WAV와 PNG/JPEG/일부 WebP를 외부 Python 패키지 없이 분석
- Suno 대괄호 metadata 분리
- 장기 cue 상대 통계 탐지와 정렬 라우팅
- 패널 섹션 provenance와 충돌 기록
- Intro/Outro 가장자리 구간 복원
- 혼합 해상도 fit 정책
- timeline JSON/CSV, cleaned SRT, QA 보고서
- stderr JSON Lines 구조화 로그
- Hermes 문서·하드코딩·비밀값·절대 경로 자동 검사

## 아직 구현되지 않은 범위 (착수 전, HOLD)

- Remotion 렌더러: `remotion/`에 의존성 매니페스트만 있고 컴포지션 소스·CLI `render` 명령 없음
- WhisperX/Demucs 자막 정렬: CLI `align` 명령 없음
- CapCut 패키징: 관련 코드 없음
- `scripts/install-renderer.ps1`, `install-alignment.ps1`는 위 기능을 실제로 구현하기 시작할 때
  쓸 의존성 설치 스크립트로 미리 준비해 둔 것이며, 아직 이를 사용하는 구현은 없다

## 실행

프로젝트 루트에서:

```powershell
$env:PYTHONPATH="$PWD\src"
python -m webtoon_capcut inspect --song "곡명"
python -m webtoon_capcut build --song "곡명"
python -m webtoon_capcut build-all --ready-only
```

또는 실행 스크립트를 사용한다.

```powershell
.\scripts\webtoon-capcut.ps1 inspect --song "곡명"
.\scripts\webtoon-capcut.ps1 build --song "곡명"
.\scripts\webtoon-capcut.ps1 build-all --ready-only
```

Windows 배치 메뉴 또는 명령 전달:

```bat
webtoon-capcut.bat
webtoon-capcut.bat build --song "곡명"
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

Remotion 렌더러·WhisperX/Demucs 정렬·CapCut 패키징은 착수 전이므로 전체 프로젝트
상태는 `HOLD`다. Python 분석/타임라인 생성 CLI는 PASS.
