# security_scanning — DefenseScan 보안 스캐너

OWASP 기반 수동 보안 스캔 도구. 웹/시스템 취약점을 분석하고 JSON 보고서를 생성한다.

## 실행

```bash
pip install -r requirements.txt
python main.py --url https://target.example.com
python main.py --system   # Windows 시스템 스캔 (관리자 권한 필요)
```

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `modules/system_scanner.py:1236` | icacls ACL 파싱 정규식 구조 오류 수정 — `\)*` (`)` 0회 이상 반복)가 실제 권한 플래그 대신 상속 플래그를 캡처하던 버그 → `(?:\([A-Z,IO]+\))*` 비캡처 그룹으로 교체 |

### 테스트
- `tests/test_core.py` 신규 작성 — 53개 테스트 전원 통과
- 대상: URL 정규화/검증, Windows 감지, 출력 경로, 리포터 유틸리티, 발견 항목 직렬화, 인자 검증
