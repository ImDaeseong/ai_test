# run_game — 게임 런처

Steam / Epic Games / Netmarble 플랫폼에서 설치된 게임을 자동 탐지하고 실행하는  
Windows MFC 다이얼로그 애플리케이션 (C++, Visual Studio).

## 빌드

Visual Studio에서 `run_game.sln` 열기 → Release x64 빌드

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `run_game/EpicLauncherSearch.cpp:44` | `FindFirstFile`로 열린 HANDLE이 `ReadTextFile` 예외 발생 시 `FindClose` 호출 없이 누출되던 문제 수정 — `TRY/CATCH_ALL/END_CATCH_ALL`로 do-while 루프 감싸 예외 시에도 `FindClose` 보장 |
