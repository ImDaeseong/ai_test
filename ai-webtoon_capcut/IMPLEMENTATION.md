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

## 남은 구현·검수 범위 (HOLD)

- 실제 곡 1080p 사람 검수: Python CLI→Remotion 30초 합성 fixture는 PASS지만 실제 음원·라이선스 미디어 입력이 없음
- WhisperX/Demucs 자막 정렬: CLI `align` 명령 없음
- CapCut 전용 프로젝트 생성: 비공개 포맷에 의존하지 않으므로 미구현. 범용 편집기 handoff 생성·무결성 검증은 구현됨
- `scripts/install-alignment.ps1`는 정렬 기능의 의존성 설치 준비만 제공한다

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

Python CLI→Remotion 30초 1080p fixture 렌더, 원자적 출력·임시 미디어 정리, 경로 안전한 범용 편집기 handoff 생성과 전달 후 무결성 검증은 PASS다. 실제 곡 검수, WhisperX/Demucs 정렬, CapCut 실제 import는 HOLD다.
