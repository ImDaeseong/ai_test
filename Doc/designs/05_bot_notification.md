# 설계문서 05 — 알림/봇 서비스

> 프로젝트: weather_alarm

---

## 1. 프로젝트 정의

**weather_alarm**: 기상청 초단기실황 API → Discord / Telegram 날씨 알림 봇
- 서울 가산동 날씨를 주기적으로 수집하여 구독자에게 자동 발송
- PostgreSQL 기반 구독자 관리 + Celery 비동기 발송 큐

---

## 2. 기술 스택

| 레이어 | 기술 |
|--------|------|
| 날씨 수집 | 기상청 초단기실황 API (httpx, 캐싱) |
| 봇 프레임워크 | Discord.py (슬래시 커맨드), python-telegram-bot |
| 비동기 큐 | Celery 5 (broker=Redis) |
| DB | PostgreSQL 16 (psycopg2) |
| 컨테이너 | Docker Compose (6서비스) |
| 발송 방식 | httpx 직접 HTTP (봇 세션 불필요) |

---

## 3. 아키텍처

### Docker Compose 서비스 구성

```
[기상청 API]
     ↓
collector.py  (주기적 fetch → Celery 태스크 등록)
     ↓
redis:7       (Celery broker)
     ↓
worker        (celery -A celery_app worker)
  → httpx로 Discord/Telegram HTTP API 직접 호출
     ↓
[구독자]

[구독자 등록/해제]
     ↓
discord_bot.py  (슬래시 커맨드)
telegram_bot.py (커맨드)
     ↓
postgres:16  (구독자 테이블 + 발송 큐)
```

### 서비스 상세

| 서비스 | 이미지/커맨드 | 역할 |
|--------|-------------|------|
| db | postgres:16-alpine | 구독자/발송 큐 영속 저장 |
| redis | redis:7-alpine | Celery 브로커 |
| collector | python collector.py | 기상청 API 주기 수집 → Celery 등록 |
| discord_bot | python discord_bot.py | 슬래시 커맨드 처리 |
| telegram_bot | python telegram_bot.py | 커맨드 처리 |
| worker | celery -A celery_app worker | 실제 메시지 발송 (scale 가능) |

---

## 4. 파일 구조

```
weather_alarm/
├── main.py               # 단일 프로세스 로컬 실행 진입점 (PostgreSQL)
├── weather_client.py     # 기상청 초단기실황 API 클라이언트 (캐싱 포함)
├── broadcaster.py        # BroadcastDispatcher (main.py 단일 실행 모드 전용)
├── notification_store.py # PostgreSQL 기반 구독자/발송 큐 관리
├── discord_bot.py        # Discord 슬래시 커맨드 봇 (독립 실행 가능)
├── telegram_bot.py       # Telegram 커맨드 봇 (독립 실행 가능)
├── celery_app.py         # Celery 앱 설정 (broker=Redis)
├── tasks.py              # Celery deliver_notification 태스크
├── collector.py          # 독립 날씨 수집 서비스
├── db/init.sql           # PostgreSQL 스키마 (Docker 초기화용)
├── Dockerfile            # 단일 이미지 (모든 Python 서비스 공통)
├── docker-compose.yml    # 6개 서비스 구성
└── .env.example          # 환경변수 템플릿
```

---

## 5. 핵심 설계 결정

### PostgreSQL 동시성 제어
```sql
-- notification_store.py: 다중 worker 충돌 방지
SELECT * FROM delivery_queue
WHERE status = 'pending'
LIMIT 100
FOR UPDATE SKIP LOCKED;

-- 중복 등록 방지
INSERT INTO delivery_queue (...)
ON CONFLICT DO NOTHING RETURNING id;
```

### Celery 설정 (tasks.py)
```python
# worker 재시작 안전 설정
task_acks_late = True              # 완료 후 ACK
worker_prefetch_multiplier = 1     # 한 번에 1개씩 처리
```

### httpx 직접 발송 (봇 세션 불필요)
```python
# tasks.py — Discord/Telegram HTTP API 직접 호출
async with httpx.AsyncClient() as client:
    await client.post(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {token}"},
        json={"content": message}
    )
```

---

## 6. worker 수평 확장

```bash
# worker 3개로 확장 (수십만 명 규모 발송 대응)
docker compose up --scale worker=3
```

- `FOR UPDATE SKIP LOCKED`: 여러 worker가 동일 행 중복 처리 방지
- `task_acks_late`: worker 재시작 시 미처리 태스크 재실행 보장

---

## 7. 환경변수 (.env)

```
# 기상청
KMA_API_KEY=...
KMA_STATION_ID=...     # 가산동 AWS 관측소

# Discord
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...

# Telegram
TELEGRAM_BOT_TOKEN=...

# DB
POSTGRES_HOST=db
POSTGRES_DB=weather_alarm
POSTGRES_USER=...
POSTGRES_PASSWORD=...

# Redis
REDIS_URL=redis://redis:6379/0
```

---

## 8. 실행

```bash
# 전체 서비스 시작
docker compose up -d

# worker 확장
docker compose up --scale worker=3

# 로컬 단일 프로세스 (개발용)
python main.py
```

---

## 9. 다음 작업 후보

- Celery Flower (모니터링 UI) 서비스 추가
- 구독자별 알림 시각 설정 (매시 정각 외 추가 시간대)
- 실패한 (`failed`) delivery_queue 행 정리 배치 태스크
