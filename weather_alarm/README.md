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

## 개선 이력 (2026-06-02)

### 테스트
- `tests/test_core.py` 신규 작성 — 55개 테스트 전원 통과
- 대상: 구독자 관리, 전송 큐, 날씨 클라이언트 헬퍼, API 응답 파싱, 텍스트 포맷, 캐시, 브로드캐스트 재시도 로직, 속도 제한, 설정 검증
