import asyncio
import io
import os
import sys

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

from weather_client import WeatherClient
from discord_bot import DiscordWeatherBot
from telegram_bot import TelegramWeatherBot

WEATHER_KEY = os.getenv("WEATHER_SERVICE_KEY", "")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


async def run_discord(weather_client: WeatherClient):
    bot = DiscordWeatherBot(weather_client, DISCORD_CHANNEL_ID)
    try:
        logger.info("Discord 봇 시작 중...")
        await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("Discord 토큰이 유효하지 않습니다. DISCORD_TOKEN을 확인하세요.")
    except Exception as e:
        logger.error(f"Discord 봇 오류: {e}")


async def run_telegram(weather_client: WeatherClient):
    bot = TelegramWeatherBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, weather_client)
    try:
        logger.info("Telegram 봇 시작 중...")
        await bot.run()
    except Exception as e:
        logger.error(f"Telegram 봇 오류: {e}")


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


async def main():
    if not WEATHER_KEY:
        logger.error("WEATHER_SERVICE_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        sys.exit(1)

    weather_client = WeatherClient(WEATHER_KEY)
    await fetch_and_print_weather(weather_client)
    tasks = []

    if DISCORD_TOKEN:
        tasks.append(run_discord(weather_client))
    else:
        logger.warning("DISCORD_TOKEN이 없습니다. Discord 봇을 건너뜁니다.")

    if TELEGRAM_TOKEN:
        tasks.append(run_telegram(weather_client))
    else:
        logger.warning("TELEGRAM_TOKEN이 없습니다. Telegram 봇을 건너뜁니다.")

    if not tasks:
        logger.error("실행할 봇이 없습니다. DISCORD_TOKEN 또는 TELEGRAM_TOKEN을 .env에 설정하세요.")
        sys.exit(1)

    logger.info(f"{len(tasks)}개 봇 동시 실행 시작 (Ctrl+C로 종료)")
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
