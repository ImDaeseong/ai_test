import aiohttp
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from loguru import logger

WEATHER_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
NX, NY = 58, 125  # 서울 가산동 격자 좌표

PTY_MAP = {
    "0": "없음", "1": "비", "2": "비/눈", "3": "눈",
    "5": "빗방울", "6": "빗방울눈날림", "7": "눈날림",
}

PTY_EMOJI = {
    "0": "☀️", "1": "🌧️", "2": "🌨️", "3": "❄️",
    "5": "🌦️", "6": "🌨️", "7": "🌨️",
}

WIND_DIRECTIONS = [
    "북", "북북동", "북동", "동북동", "동", "동남동", "남동", "남남동",
    "남", "남남서", "남서", "서남서", "서", "서북서", "북서", "북북서",
]


@dataclass
class WeatherData:
    temperature: str
    humidity: str
    precipitation_type: str
    precipitation_type_emoji: str
    precipitation: str
    wind_direction: str
    wind_speed: str
    base_date: str
    base_time: str

    def format_text(self) -> str:
        date_str = f"{self.base_date[:4]}-{self.base_date[4:6]}-{self.base_date[6:]}"
        time_str = f"{self.base_time[:2]}:{self.base_time[2:]}"
        return (
            f"{self.precipitation_type_emoji} 서울 가산동 현재 날씨\n"
            f"📅 {date_str} {time_str} 기준\n\n"
            f"🌡️ 기온: {self.temperature}\n"
            f"💧 습도: {self.humidity}\n"
            f"🌧️ 강수형태: {self.precipitation_type}\n"
            f"🌂 1시간 강수량: {self.precipitation}\n"
            f"💨 풍향/풍속: {self.wind_direction} / {self.wind_speed}"
        )


class WeatherClient:
    def __init__(self, service_key: str):
        self.service_key = service_key

    @staticmethod
    def _get_base_datetime() -> tuple[str, str]:
        # 기상청 데이터는 약 10분 지연 제공 — 현재 시각에서 10분 빼고 10분 단위 내림
        now = datetime.now() - timedelta(minutes=10)
        minutes = (now.minute // 10) * 10
        base = now.replace(minute=minutes, second=0, microsecond=0)
        return base.strftime("%Y%m%d"), base.strftime("%H%M")

    @staticmethod
    def _deg_to_direction(deg: str) -> str:
        idx = int((float(deg) + 11.25) / 22.5) % 16
        return WIND_DIRECTIONS[idx]

    async def fetch(self) -> Optional[WeatherData]:
        base_date, base_time = self._get_base_datetime()
        params = {
            "serviceKey": self.service_key,
            "numOfRows": "10",
            "pageNo": "1",
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": str(NX),
            "ny": str(NY),
        }
        logger.info(f"기상청 API 요청: base_date={base_date}, base_time={base_time}")
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(WEATHER_API_URL, params=params) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
            logger.debug(f"기상청 API 응답 원본: {data}")

            result_code = data.get("response", {}).get("header", {}).get("resultCode")
            if result_code != "00":
                result_msg = data.get("response", {}).get("header", {}).get("resultMsg", "알 수 없는 오류")
                logger.error(f"기상청 API 오류 응답: resultCode={result_code}, resultMsg={result_msg}")
                return None

            items = data["response"]["body"]["items"]["item"]
            obs = {item["category"]: item["obsrValue"] for item in items}
            logger.info(f"기상청 API 파싱 성공: 항목 수={len(obs)}")

            pty = obs.get("PTY", "0")
            rn1 = obs.get("RN1", "0")
            vec = obs.get("VEC", "0")
            wsd = obs.get("WSD", "0")

            # 기상청은 강수 없으면 "0" 반환. 0이면 "강수없음" 표시, 수치면 mm 부여
            try:
                precip_str = "강수없음" if float(rn1) == 0 else f"{rn1}mm"
            except ValueError:
                precip_str = rn1

            logger.info(
                f"날씨 조회 성공 | "
                f"기온={obs.get('T1H')}°C | "
                f"습도={obs.get('REH')}% | "
                f"강수형태={PTY_MAP.get(pty, pty)} | "
                f"1h강수량={precip_str} | "
                f"풍향={WeatherClient._deg_to_direction(vec)}({float(vec):.0f}°) | "
                f"풍속={float(wsd):.1f}m/s | "
                f"기준시각={base_date} {base_time[:2]}:{base_time[2:]}"
            )
            return WeatherData(
                temperature=f"{obs.get('T1H', 'N/A')}°C",
                humidity=f"{obs.get('REH', 'N/A')}%",
                precipitation_type=PTY_MAP.get(pty, pty),
                precipitation_type_emoji=PTY_EMOJI.get(pty, "🌤️"),
                precipitation=precip_str,
                wind_direction=f"{WeatherClient._deg_to_direction(vec)} ({float(vec):.0f}°)",
                wind_speed=f"{float(wsd):.1f}m/s",
                base_date=base_date,
                base_time=base_time,
            )
        except aiohttp.ClientError as e:
            logger.error(f"기상청 API 네트워크 오류: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"기상청 API 응답 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"날씨 데이터 조회 실패: {e}")
        return None
