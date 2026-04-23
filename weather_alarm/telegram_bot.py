import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from loguru import logger
from weather_client import WeatherClient


class TelegramWeatherBot:
    def __init__(self, token: str, chat_id: str, weather_client: WeatherClient):
        self.token = token
        self.chat_id = chat_id
        self.weather_client = weather_client
        self.app = Application.builder().token(token).build()
        self.app.add_handler(CommandHandler("weather", self._weather_command))
        self.app.add_handler(CommandHandler("start", self._start_command))

    async def _start_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "안녕하세요! 서울 가산동 날씨 알리미입니다.\n\n"
            "/weather — 현재 날씨 조회"
        )

    async def _weather_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        data = await self.weather_client.fetch()
        if data is None:
            await update.message.reply_text(
                "❌ 날씨 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해주세요."
            )
            return
        await update.message.reply_text(data.format_text())
        logger.info(
            f"Telegram 전달 완료 | 요청자={update.effective_user.username} | "
            f"기온={data.temperature} | 습도={data.humidity} | "
            f"강수형태={data.precipitation_type} | 강수량={data.precipitation} | "
            f"풍향/풍속={data.wind_direction} / {data.wind_speed}"
        )

    async def send_notification(self, message: str):
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID가 없어 알림을 보낼 수 없습니다.")
            return
        try:
            await self.app.bot.send_message(chat_id=self.chat_id, text=message)
            logger.info(f"Telegram 알림 전송 완료: chat_id={self.chat_id}")
        except Exception as e:
            logger.error(f"Telegram 알림 전송 실패: {e}")

    async def run(self):
        async with self.app:
            await self.app.start()
            logger.info("Telegram 봇 폴링 시작")
            await self.app.updater.start_polling(drop_pending_updates=True)
            data = await self.weather_client.fetch()
            if data:
                await self.send_notification(data.format_text())
            else:
                logger.warning("Telegram 시작 알림: 날씨 데이터 조회 실패")
            try:
                await asyncio.Event().wait()  # 종료 신호가 올 때까지 대기
            finally:
                await self.app.updater.stop()
                await self.app.stop()
