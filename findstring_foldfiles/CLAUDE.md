# Claude Code Instructions — findstring_foldfiles

## 프로젝트 목적

폴더 또는 드라이브 전체를 멀티스레드로 빠르게 문자열 검색하는 Python 데스크톱 GUI 앱.
표준 라이브러리만 사용 (외부 패키지 없음).

## 구조

```
find_string_app.py   # 진입점 + tkinter GUI + 멀티스레드 검색
tests/               # pytest 테스트 (5개)
run.bat              # Windows 실행 단축키
```

## 실행

```bash
python find_string_app.py
```

## 테스트

```bash
pytest tests/ -v
```

## 주의사항

- 외부 패키지 의존성 추가 금지 — 표준 라이브러리 유지가 배포 단순성의 핵심
- GUI 코드와 검색 로직을 분리하여 테스트 가능성 유지
- 멀티스레드 검색 시 UI 프리징 방지 로직 확인 필수
