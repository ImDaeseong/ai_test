# check_FileEncoding — 파일 인코딩 검사 도구

Go 기반 웹 UI. 폴더/파일 경로를 입력하면 UTF-8 BOM / UTF-16 LE / UTF-16 BE / EUC-KR(CP949) / Empty를 판별한다.

## 실행

```bash
go run .
# 브라우저: http://localhost:8765
```

## 지원 인코딩

| 레이블 | 조건 |
|---|---|
| `UTF-8 BOM` | BOM `EF BB BF` |
| `UTF-16 LE` | BOM `FF FE` |
| `UTF-16 BE` | BOM `FE FF` |
| `UTF-8 (No BOM)` | BOM 없음 + UTF-8 유효 |
| `EUC-KR (CP949)` | UTF-8 아님 |
| `Empty` | 0바이트 파일 |

## 개선 이력 (2026-06-02)

### 기능 개선
| 파일 | 내용 |
|---|---|
| `main.go:detectEncoding` | 0바이트 파일을 `"Empty"` 레이블로 명시적 분류 추가 |
| `main.go:scanHandler` | 스캔 시간 초과 시 `408 Request Timeout` 응답 추가 (기존: 응답 없이 종료) |

### 테스트
- go test 3/3 통과
