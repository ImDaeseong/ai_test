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
