# weather_alarm — 날씨 경보 알림 봇

기상청 API 기반 날씨 경보를 Discord / Telegram으로 브로드캐스트하는 멀티 플랫폼 봇.

## 실행

```bash
pip install -r requirements.txt
python main.py
```

## 환경 변수

`.env` 파일 또는 시스템 환경변수로 설정:

| 변수 | 설명 |
|---|---|
| `WEATHER_API_KEY` | 기상청 API 키 |
| `DISCORD_BOT_TOKEN` | Discord 봇 토큰 |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 토큰 |

## 외부 노출 전 필수 수정 항목

> 개인 로컬 환경에서는 무관하나, 서버 배포·공개·공유 시 반드시 수정할 것.

| # | 파일 | 문제 | 수정 방법 |
|---|------|------|---------|
| 1 | `weather_client.py:13` | 기상청 API URL이 `http://`로 평문 전송 — 쿼리 파라미터에 포함된 서비스 키가 네트워크 구간에 노출됨 | URL을 `https://apis.data.go.kr/...`로 변경 |
| 2 | `README.md` 환경변수 표 | 변수명 오기재 — `WEATHER_API_KEY` → 실제 코드는 `WEATHER_SERVICE_KEY`, `DISCORD_BOT_TOKEN` → `DISCORD_TOKEN`, `TELEGRAM_BOT_TOKEN` → `TELEGRAM_TOKEN` | 아래 환경변수 표 참고하여 `.env` 작성 |

**실제 환경변수명 (main.py 기준):**

| 변수 | 설명 |
|---|---|
| `WEATHER_SERVICE_KEY` | 기상청 API 키 |
| `DISCORD_TOKEN` | Discord 봇 토큰 |
| `TELEGRAM_TOKEN` | Telegram 봇 토큰 |

---

## 개선 이력 (2026-06-02)

### 테스트
- `tests/test_core.py` 신규 작성 — 55개 테스트 전원 통과
- 대상: 구독자 관리, 전송 큐, 날씨 클라이언트 헬퍼, API 응답 파싱, 텍스트 포맷, 캐시, 브로드캐스트 재시도 로직, 속도 제한, 설정 검증
