# Claude Code Instructions — check_FileEncoding

## 프로젝트 목적

Go 기반 웹 UI. 폴더/파일 경로를 입력하면 인코딩을 판별한다.
지원: UTF-8 BOM / UTF-16 LE / UTF-16 BE / UTF-8 (No BOM) / EUC-KR(CP949) / Empty

## 구조

```
main.go        # 웹 서버 + 인코딩 판별 로직
main_test.go   # Go 테스트
index.html     # 프론트엔드 (단일 파일)
```

## 실행

```bash
go run .
# 브라우저: http://localhost:8765
```

## 테스트

```bash
go test ./...
```

## 주의사항

- 인코딩 판별 순서: BOM 우선 확인 → UTF-8 유효성 → EUC-KR 폴백
- BOM 바이트 시퀀스를 변경하면 판별 우선순위가 무너지므로 주의
- 포트 8765 고정값 — 변경 시 `index.html` fetch URL도 함께 수정
