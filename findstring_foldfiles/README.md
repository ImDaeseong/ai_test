# Folder String Finder

폴더 또는 드라이브 전체를 멀티스레드로 빠르게 문자열 검색하는 Python 데스크톱 GUI 앱입니다.

## 요구 사항

- Python 3.10 이상 (표준 라이브러리만 사용, 별도 패키지 설치 불필요)
- Windows / macOS / Linux

## 실행 방법

```powershell
python find_string_app.py
```

Windows에서는 `run.bat`을 더블클릭해도 실행됩니다.

## 주요 기능

| 기능 | 설명 |
|------|------|
| 폴더 검색 | Browse 버튼으로 폴더를 선택하고 그 하위 전체를 검색 |
| 드라이브 검색 | 드롭다운에서 드라이브를 선택해 드라이브 전체 검색 |
| 전체 드라이브 검색 | "Search all drives" 체크 시 감지된 모든 드라이브를 동시 검색 |
| 대소문자 구분 | "Case sensitive" 체크로 전환 |
| 바이너리 파일 포함 | "Include binary-like files" 체크 시 모든 파일 검색 |
| 확장자 필터 | Extensions 란에 `.h .cpp` 등 직접 입력하거나 프리셋 선택 (비워두면 기본 49종 텍스트 목록 사용) |
| 결과 목록 | 파일 경로 / 줄 번호 / 미리보기 표시 |
| 파일 열기 | 결과 더블클릭 또는 "Open selected file" 버튼으로 기본 앱에서 파일 열기 |
| 검색 중단 | Stop 버튼으로 언제든 검색 취소 |

## 아키텍처

```
FindStringApp (tkinter 메인 스레드)
│
├── _drain_outbox()  ── 100ms마다 queue를 폴링해 UI 업데이트
│
└── SearchWorker (threading.Thread, 검색 루트당 1개)
    ├── _iter_files()     ── os.walk로 파일 열거, SKIP_DIRS 제외
    ├── _should_read()    ── TEXT_EXTENSIONS 또는 UTF-8 휴리스틱으로 파일 판별
    └── _find_in_file()   ── 라인 단위 키워드 탐색, Match 객체를 queue에 PUT
```

### 텍스트 파일 판별 로직

1. 확장자가 `TEXT_EXTENSIONS` 49종 목록에 있으면 텍스트로 처리
2. 목록에 없으면 앞 2 KB를 읽어 null 바이트(`\x00`) 없으면 텍스트로 처리
3. `--include-binary-like` 옵션(체크박스)이면 모든 파일을 강제 포함

### 스킵 디렉토리

`.git` · `.hg` · `.svn` · `__pycache__` · `node_modules` · `$Recycle.Bin` · `System Volume Information`

## 파일 구성

```
findstring_foldfiles/
├── find_string_app.py   # 전체 소스 (SearchWorker + FindStringApp)
├── run.bat              # Windows 실행 배치
└── README.md
```

## 주의 사항

- 드라이브 전체 검색은 파일 수에 따라 수 분이 소요될 수 있습니다.
- 검색 결과가 매우 많을 경우(수만 건 이상) UI 응답이 느려질 수 있습니다.
- 파일은 UTF-8(errors=ignore)로 읽으며, 다른 인코딩 파일은 일부 문자가 깨질 수 있습니다.

## 개선 이력 (버그 수정)

| # | 파일 | 내용 |
|---|------|------|
| 1 | `find_string_app.py` | `_drain_outbox`: `while True` → `for _ in range(200)` 로 제한해 대량 결과 시 UI 동결 방지 |
| 2 | `find_string_app.py` | `_open_selected`: `AttributeError` 캐치 방식 → `os.name == "nt"` 명시적 분기로 교체해 예외 마스킹 제거 |
| 3 | `find_string_app.py` | Extensions 필터 추가 — 확장자 직접 입력 또는 프리셋(C/C++·Java·Kotlin·Swift·Web) 선택으로 탐색 대상 파일 범위를 축소 |
