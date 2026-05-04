import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from loguru import logger
from notification_store import NotificationStore
from weather_client import WeatherClient


class TelegramWeatherBot:
    def __init__(
        self,
        token: str,
        chat_id: str,
        weather_client: WeatherClient,
        store: Optional[NotificationStore] = None,
    ):
        self.token = token
        self.chat_id = chat_id
        self.weather_client = weather_client
        self.store = store
        self.app = Application.builder().token(token).build()
        self.app.add_handler(CommandHandler("weather", self._weather_command))
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CommandHandler("subscribe", self._subscribe_command))
        self.app.add_handler(CommandHandler("unsubscribe", self._unsubscribe_command))

    async def _start_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        if update.message is None:
            return
        await update.message.reply_text(
            "안녕하세요! 서울 가산동 날씨 알리미입니다.\n\n"
            "/weather — 현재 날씨 조회\n"
            "/subscribe — 날씨 알림 구독\n"
            "/unsubscribe — 날씨 알림 구독 해제"
        )

    async def _weather_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        if update.message is None:
            return
        data = await self.weather_client.fetch()
        if data is None:
            await update.message.reply_text(
                "❌ 날씨 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해주세요."
            )
            return
        await update.message.reply_text(data.format_text())
        logger.info(
            f"Telegram 전달 완료 | 요청자={getattr(update.effective_user, 'username', None)} | "
            f"기온={data.temperature} | 습도={data.humidity} | "
            f"강수형태={data.precipitation_type} | 강수량={data.precipitation} | "
            f"풍향/풍속={data.wind_direction} / {data.wind_speed}"
        )

    async def _subscribe_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        if update.message is None or update.effective_chat is None:
            return
        if self.store is None:
            await update.message.reply_text("구독 저장소가 초기화되지 않았습니다.")
            return
        display_name = getattr(update.effective_user, "username", None) or ""
        self.store.add_subscriber("telegram", str(update.effective_chat.id), display_name)
        await update.message.reply_text("날씨 알림 구독이 완료되었습니다.")
        logger.info(f"Telegram 구독 등록: chat_id={update.effective_chat.id}, user={display_name}")

    async def _unsubscribe_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        if update.message is None or update.effective_chat is None:
            return
        if self.store is None:
            await update.message.reply_text("구독 저장소가 초기화되지 않았습니다.")
            return
        self.store.remove_subscriber("telegram", str(update.effective_chat.id))
        await update.message.reply_text("날씨 알림 구독을 해제했습니다.")
        logger.info(f"Telegram 구독 해제: chat_id={update.effective_chat.id}")

    async def run(self, stop_event: Optional[asyncio.Event] = None):
        stop_event = stop_event or asyncio.Event()
        async with self.app:
            await self.app.start()
            logger.info("Telegram 봇 폴링 시작")
            if self.app.updater is None:
                raise RuntimeError("Telegram updater가 초기화되지 않았습니다.")
            await self.app.updater.start_polling(drop_pending_updates=True)
            try:
                await stop_event.wait()
            finally:
                if self.app.updater.running:
                    await self.app.updater.stop()
                if self.app.running:
                    await self.app.stop()


if __name__ == "__main__":
    import io
    import os
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add("logs/telegram_bot.log", mode="w", level="DEBUG", encoding="utf-8")

    from notification_store import NotificationStore
    from weather_client import WeatherClient

    async def main():
        token = os.getenv("TELEGRAM_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        postgres_dsn = os.getenv("POSTGRES_DSN", "")
        weather_key = os.getenv("WEATHER_SERVICE_KEY", "")
        if not token:
            logger.error("TELEGRAM_TOKEN이 설정되지 않았습니다")
            sys.exit(1)
        store = NotificationStore(postgres_dsn)
        async with WeatherClient(weather_key) as weather_client:
            bot = TelegramWeatherBot(token, chat_id, weather_client, store)
            await bot.run()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("사용자 요청으로 Telegram 봇을 종료합니다")
