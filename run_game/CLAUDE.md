# Claude Code Instructions — run_game

## 프로젝트 목적

Steam / Epic Games / Netmarble 플랫폼에서 설치된 게임을 자동 탐지하고 실행하는
Windows MFC 다이얼로그 애플리케이션 (C++, Visual Studio).

## 구조

```
run_game/
  run_game.sln          # Visual Studio 솔루션
  EpicLauncherSearch.*  # Epic Games 탐지 로직
  GameConfig.json       # 게임 목록 설정
```

## 빌드

Visual Studio에서 `run_game.sln` 열기 → Release x64 빌드

## 주의사항

- `EpicLauncherSearch.cpp:44`: `FindFirstFile` 핸들은 예외 발생 시에도 반드시 `FindClose` 호출 — `TRY/CATCH_ALL/END_CATCH_ALL`로 보호됨. 핸들 관련 코드 수정 시 이 패턴 유지
- MFC 다이얼로그 앱 — Windows 전용, 크로스플랫폼 빌드 불가
- 테스트는 Visual Studio 빌드 환경 필요 — 자동화 테스트 없음 (HOLD)
- `GameConfig.json` 수정으로 게임 목록 추가 가능 (코드 수정 불필요)
