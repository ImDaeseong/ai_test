from typing import Optional

import discord
from discord import app_commands
from loguru import logger
from notification_store import NotificationStore
from weather_client import WeatherClient, WeatherData


def build_weather_embed(data: WeatherData) -> discord.Embed:
    date_str = f"{data.base_date[:4]}-{data.base_date[4:6]}-{data.base_date[6:]}"
    time_str = f"{data.base_time[:2]}:{data.base_time[2:]}"

    embed = discord.Embed(
        title=f"{data.precipitation_type_emoji} 서울 가산동 현재 날씨",
        description=f"{date_str} {time_str} 기준",
        color=discord.Color.blue(),
    )
    embed.add_field(name="🌡️ 기온", value=data.temperature, inline=True)
    embed.add_field(name="💧 습도", value=data.humidity, inline=True)
    embed.add_field(name="🌧️ 강수형태", value=data.precipitation_type, inline=True)
    embed.add_field(name="🌂 1시간 강수량", value=data.precipitation, inline=True)
    embed.add_field(name="💨 풍향", value=data.wind_direction, inline=True)
    embed.add_field(name="💨 풍속", value=data.wind_speed, inline=True)
    embed.set_footer(text="데이터 출처: 기상청 초단기실황 API")
    return embed


class DiscordWeatherBot(discord.Client):
    def __init__(
        self,
        weather_client: WeatherClient,
        channel_id: int = 0,
        store: Optional[NotificationStore] = None,
    ):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.weather_client = weather_client
        self.channel_id = channel_id
        self.store = store
        self._register_commands()

    def _register_commands(self):
        @self.tree.command(name="가산날씨", description="서울 가산동 현재 날씨를 조회합니다")
        async def _gasanweather(interaction: discord.Interaction):
            await interaction.response.defer()
            data: Optional[WeatherData] = await self.weather_client.fetch()

            if data is None:
                await interaction.followup.send(
                    "❌ 날씨 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해주세요."
                )
                return

            await interaction.followup.send(embed=build_weather_embed(data))
            logger.info(
                f"Discord 전달 완료 | 요청자={interaction.user} | "
                f"기온={data.temperature} | 습도={data.humidity} | "
                f"강수형태={data.precipitation_type} | 강수량={data.precipitation} | "
                f"풍향/풍속={data.wind_direction} / {data.wind_speed}"
            )

        @self.tree.command(name="날씨구독", description="현재 채널에서 날씨 알림을 구독합니다")
        async def _subscribe(interaction: discord.Interaction):
            if self.store is None:
                await interaction.response.send_message("구독 저장소가 초기화되지 않았습니다.", ephemeral=True)
                return
            channel_id = str(interaction.channel_id)
            self.store.add_subscriber("discord", channel_id, str(interaction.channel))
            await interaction.response.send_message("이 채널에 날씨 알림을 보내도록 구독했습니다.", ephemeral=True)
            logger.info(f"Discord 구독 등록: channel_id={channel_id}, user={interaction.user}")

        @self.tree.command(name="날씨구독해제", description="현재 채널의 날씨 알림 구독을 해제합니다")
        async def _unsubscribe(interaction: discord.Interaction):
            if self.store is None:
                await interaction.response.send_message("구독 저장소가 초기화되지 않았습니다.", ephemeral=True)
                return
            channel_id = str(interaction.channel_id)
            self.store.remove_subscriber("discord", channel_id)
            await interaction.response.send_message("이 채널의 날씨 알림 구독을 해제했습니다.", ephemeral=True)
            logger.info(f"Discord 구독 해제: channel_id={channel_id}, user={interaction.user}")

    async def setup_hook(self):
        # 전역 커맨드 동기화 (반영까지 최대 1시간 소요, 테스트 시 guild sync 권장)
        try:
            await self.tree.sync()
            logger.info("Discord 슬래시 커맨드 전역 동기화 완료")
        except Exception as e:
            logger.error(f"Discord 슬래시 커맨드 동기화 실패: {e}")
            raise

    async def on_ready(self):
        logger.info(f"Discord 봇 연결됨: {self.user} (ID: {self.user.id})")


if __name__ == "__main__":
    import asyncio
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
    logger.add("logs/discord_bot.log", mode="w", level="DEBUG", encoding="utf-8")

    from notification_store import NotificationStore
    from weather_client import WeatherClient

    async def main():
        token = os.getenv("DISCORD_TOKEN", "")
        channel_id = int(os.getenv("DISCORD_CHANNEL_ID", "0") or "0")
        postgres_dsn = os.getenv("POSTGRES_DSN", "")
        weather_key = os.getenv("WEATHER_SERVICE_KEY", "")
        if not token:
            logger.error("DISCORD_TOKEN이 설정되지 않았습니다")
            sys.exit(1)
        store = NotificationStore(postgres_dsn)
        async with WeatherClient(weather_key) as weather_client:
            bot = DiscordWeatherBot(weather_client, channel_id, store)
            try:
                await bot.start(token)
            except discord.LoginFailure:
                logger.error("Discord 토큰이 유효하지 않습니다")
                raise
            finally:
                if not bot.is_closed():
                    await bot.close()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("사용자 요청으로 Discord 봇을 종료합니다")
