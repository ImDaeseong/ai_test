# Claude Code Instructions — security_scanning

## 프로젝트 목적

OWASP 기반 수동 보안 스캔 도구. 웹/Windows 시스템 취약점을 분석하고 JSON 보고서를 생성한다.

## 구조

```
main.py           # CLI 진입점 (--url / --system 모드)
modules/          # 스캐너 모듈 (web_scanner.py, system_scanner.py 등)
tests/            # pytest 테스트 (53개)
```

## 실행

```bash
pip install -r requirements.txt
python main.py --url https://target.example.com
python main.py --system    # Windows 시스템 스캔 (관리자 권한 필요)
```

## 테스트

```bash
pytest tests/ -v
```

## 주의사항

- `modules/system_scanner.py` icacls ACL 파싱: `(?:\([A-Z,IO]+\))*` 비캡처 그룹 유지 — 이전 `\)*` 패턴은 상속 플래그를 잘못 캡처하는 버그 있음
- `--system` 모드는 관리자 권한 없으면 일부 스캔 항목 스킵됨 (오류 아님)
- 외부 타깃 스캔 시 반드시 허가된 환경에서만 실행
- JSON 보고서 출력 경로는 `--output` 인자로 지정
