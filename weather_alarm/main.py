import asyncio
import io
import os
import sys
from dataclasses import dataclass
from typing import Optional

import discord
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Windows cp949 콘솔에서 한글/이모지 깨짐 방지
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.makedirs("logs", exist_ok=True)
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "logs/weather_alarm.log",
    mode="w",
    level="DEBUG",
    encoding="utf-8",
)

from broadcaster import BroadcastDispatcher, build_discord_sender, build_telegram_sender
from weather_client import WeatherClient
from discord_bot import DiscordWeatherBot
from notification_store import NotificationStore
from telegram_bot import TelegramWeatherBot


@dataclass
class Settings:
    weather_key: str
    discord_token: str
    discord_channel_id: int
    telegram_token: str
    telegram_chat_id: str
    db_path: str
    telegram_rate_per_second: float
    discord_rate_per_second: float


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _parse_optional_int(value: str, name: str) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        logger.warning(f"{name} 값이 숫자가 아닙니다. 시작 알림 채널 설정을 건너뜁니다.")
        return 0


def _parse_float(value: str, name: str, default: float) -> float:
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError:
        logger.warning(f"{name} 값이 숫자가 아닙니다. 기본값 {default}를 사용합니다.")
        return default
    if parsed <= 0:
        logger.warning(f"{name} 값은 0보다 커야 합니다. 기본값 {default}를 사용합니다.")
        return default
    return parsed


def load_settings() -> Settings:
    return Settings(
        weather_key=_get_env("WEATHER_SERVICE_KEY"),
        discord_token=_get_env("DISCORD_TOKEN"),
        discord_channel_id=_parse_optional_int(_get_env("DISCORD_CHANNEL_ID"), "DISCORD_CHANNEL_ID"),
        telegram_token=_get_env("TELEGRAM_TOKEN"),
        telegram_chat_id=_get_env("TELEGRAM_CHAT_ID"),
        db_path=_get_env("BROADCAST_DB_PATH", "weather_alarm.db"),
        telegram_rate_per_second=_parse_float(
            _get_env("TELEGRAM_RATE_PER_SECOND"), "TELEGRAM_RATE_PER_SECOND", 25.0
        ),
        discord_rate_per_second=_parse_float(
            _get_env("DISCORD_RATE_PER_SECOND"), "DISCORD_RATE_PER_SECOND", 20.0
        ),
    )


def validate_settings(settings: Settings) -> bool:
    is_valid = True
    if not settings.weather_key:
        logger.error("WEATHER_SERVICE_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        is_valid = False
    if not settings.discord_token and not settings.telegram_token:
        logger.error("실행할 봇이 없습니다. DISCORD_TOKEN 또는 TELEGRAM_TOKEN을 .env에 설정하세요.")
        is_valid = False
    if settings.telegram_token and not settings.telegram_chat_id:
        logger.warning("TELEGRAM_CHAT_ID가 없어 Telegram 시작 알림은 건너뜁니다. /weather 명령은 동작합니다.")
    return is_valid


async def run_discord(bot: DiscordWeatherBot, token: str):
    try:
        logger.info("Discord 봇 시작 중...")
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Discord 토큰이 유효하지 않습니다. DISCORD_TOKEN을 확인하세요.")
        raise
    except asyncio.CancelledError:
        logger.info("Discord 봇 종료 중...")
        await bot.close()
        raise
    except Exception as e:
        logger.error(f"Discord 봇 오류: {e}")
        raise
    finally:
        if not bot.is_closed():
            await bot.close()


async def run_telegram(
    bot: TelegramWeatherBot,
    stop_event: asyncio.Event,
):
    try:
        logger.info("Telegram 봇 시작 중...")
        await bot.run(stop_event)
    except asyncio.CancelledError:
        logger.info("Telegram 봇 종료 중...")
        stop_event.set()
        raise
    except Exception as e:
        logger.error(f"Telegram 봇 오류: {e}")
        raise


async def fetch_and_print_weather(weather_client: WeatherClient):
    logger.info("봇 시작 전 날씨 데이터 확인 중...")
    data = await weather_client.fetch()
    if data:
        logger.info("=== 현재 날씨 데이터 확인 ===")
        for line in data.format_text().splitlines():
            logger.info(line)
        logger.info("==============================")
    else:
        logger.warning("날씨 데이터 조회 실패 — API 키 또는 네트워크를 확인하세요.")
    return data


def seed_env_subscribers(settings: Settings, store: NotificationStore) -> None:
    if settings.telegram_token and settings.telegram_chat_id:
        store.add_subscriber("telegram", settings.telegram_chat_id, "env:TELEGRAM_CHAT_ID")
    if settings.discord_token and settings.discord_channel_id:
        store.add_subscriber("discord", str(settings.discord_channel_id), "env:DISCORD_CHANNEL_ID")


async def enqueue_startup_weather(
    weather_client: WeatherClient,
    store: NotificationStore,
    enabled_platforms: list,
) -> None:
    data = await fetch_and_print_weather(weather_client)
    if data is None:
        return
    dedupe_key = f"{data.base_date}{data.base_time}"
    inserted = store.enqueue_broadcast(
        data.format_text(),
        message_type="weather",
        dedupe_key=dedupe_key,
        platforms=enabled_platforms,
    )
    logger.info(f"날씨 브로드캐스트 작업 적재: 신규 작업={inserted}, 대기 작업={store.pending_count()}")


async def run_bots(
    settings: Settings,
    weather_client: WeatherClient,
    store: NotificationStore,
) -> None:
    stop_event = asyncio.Event()
    tasks = []
    senders = {}

    if settings.discord_token:
        discord_bot = DiscordWeatherBot(weather_client, settings.discord_channel_id, store)
        senders["discord"] = build_discord_sender(discord_bot)
        tasks.append(
            asyncio.create_task(
                run_discord(discord_bot, settings.discord_token),
                name="discord",
            )
        )
    else:
        logger.warning("DISCORD_TOKEN이 없습니다. Discord 봇을 건너뜁니다.")

    if settings.telegram_token:
        telegram_bot = TelegramWeatherBot(
            settings.telegram_token,
            settings.telegram_chat_id,
            weather_client,
            store,
        )
        senders["telegram"] = build_telegram_sender(telegram_bot.app.bot)
        tasks.append(
            asyncio.create_task(
                run_telegram(telegram_bot, stop_event),
                name="telegram",
            )
        )
    else:
        logger.warning("TELEGRAM_TOKEN이 없습니다. Telegram 봇을 건너뜁니다.")

    dispatcher = BroadcastDispatcher(
        store,
        senders,
        telegram_rate_per_second=settings.telegram_rate_per_second,
        discord_rate_per_second=settings.discord_rate_per_second,
    )
    tasks.append(
        asyncio.create_task(
            dispatcher.run(stop_event),
            name="broadcast-dispatcher",
        )
    )

    logger.info(f"{len(tasks)}개 봇 병렬 실행 시작 (Ctrl+C로 종료)")
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

    for task in done:
        if task.cancelled():
            logger.info(f"{task.get_name()} 태스크가 취소되었습니다.")
            continue
        exc: Optional[BaseException] = task.exception()
        if exc is not None:
            logger.error(f"{task.get_name()} 태스크가 예외로 종료되었습니다: {exc}")

    if pending:
        logger.info("남은 봇 태스크를 정리합니다.")
        stop_event.set()
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


async def main():
    settings = load_settings()
    if not validate_settings(settings):
        sys.exit(1)

    store = NotificationStore(settings.db_path)
    seed_env_subscribers(settings, store)
    enabled_platforms = []
    if settings.discord_token:
        enabled_platforms.append("discord")
    if settings.telegram_token:
        enabled_platforms.append("telegram")
    async with WeatherClient(settings.weather_key) as weather_client:
        await enqueue_startup_weather(weather_client, store, enabled_platforms)
        await run_bots(settings, weather_client, store)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("사용자 요청으로 종료합니다.")
