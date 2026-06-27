# Claude Code Instructions — weather_alarm

## 프로젝트 목적

기상청 API 기반 날씨 경보를 Discord / Telegram으로 브로드캐스트하는 멀티 플랫폼 봇.

## 구조

```
main.py                 # 진입점 (봇 실행)
weather_client.py       # 기상청 API 클라이언트
broadcaster.py          # Discord/Telegram 공통 브로드캐스터
discord_bot.py          # Discord 봇 구현
telegram_bot.py         # Telegram 봇 구현
notification_store.py   # 알림 중복 방지 저장소
tests/                  # pytest 테스트 (55개)
```

## 실행

```bash
pip install -r requirements.txt
python main.py
```

## 환경 변수 (.env)

| 변수 (실제 코드 기준) | 설명 |
|------|------|
| `WEATHER_SERVICE_KEY` | 기상청 API 키 |
| `DISCORD_TOKEN` | Discord 봇 토큰 |
| `TELEGRAM_TOKEN` | Telegram 봇 토큰 |

> README의 변수명(`WEATHER_API_KEY` 등)은 오기재 — 위 표 기준으로 `.env` 작성

## 테스트

```bash
pytest tests/ -v
```

## 주의사항

- `weather_client.py:13` API URL: 서버 배포 시 `http://` → `https://apis.data.go.kr/...` 변경 필수 (현재 평문 전송으로 API 키 노출 위험)
- 환경 변수 키 이름은 `main.py` 기준이 정확 — README와 다름
- API 키·토큰은 절대 코드에 직접 기재 금지, `.env`로만 관리
