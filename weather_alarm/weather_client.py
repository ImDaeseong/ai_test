from dataclasses import dataclass
from datetime import datetime, timedelta
import time
from typing import Any, Optional

import aiohttp
from loguru import logger

WEATHER_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
NX, NY = 58, 125  # 서울 가산동 격자 좌표
DEFAULT_CACHE_TTL_SECONDS = 300

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


class WeatherApiError(Exception):
    """기상청 API 응답이 정상 형식이 아닐 때 사용합니다."""


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
    def __init__(
        self,
        service_key: str,
        nx: int = NX,
        ny: int = NY,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.service_key = service_key
        self.nx = nx
        self.ny = ny
        self.cache_ttl_seconds = cache_ttl_seconds
        self._session = session
        self._owns_session = session is None
        self._cache: Optional[WeatherData] = None
        self._cache_expires_at = 0.0
        self._fetch_lock = None

    async def __aenter__(self) -> "WeatherClient":
        await self._get_session()
        return self

    async def __aexit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        await self.close()

    @staticmethod
    def _get_base_datetime(now: Optional[datetime] = None) -> tuple[str, str]:
        # 초단기실황 API의 발표시각은 정시 단위입니다. 지연을 고려해 10분 전 정시를 조회합니다.
        target = (now or datetime.now()) - timedelta(minutes=10)
        base = target.replace(minute=0, second=0, microsecond=0)
        return base.strftime("%Y%m%d"), base.strftime("%H%M")

    @staticmethod
    def _deg_to_direction(deg: str) -> str:
        idx = int((float(deg) + 11.25) / 22.5) % 16
        return WIND_DIRECTIONS[idx]

    @staticmethod
    def _format_precipitation(value: str) -> str:
        try:
            return "강수없음" if float(value) == 0 else f"{value}mm"
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _parse_response(data: dict[str, Any], base_date: str, base_time: str) -> WeatherData:
        header = data.get("response", {}).get("header", {})
        result_code = header.get("resultCode")
        if result_code != "00":
            result_msg = header.get("resultMsg", "알 수 없는 오류")
            raise WeatherApiError(f"resultCode={result_code}, resultMsg={result_msg}")

        try:
            items = data["response"]["body"]["items"]["item"]
        except KeyError as exc:
            raise WeatherApiError(f"필수 응답 필드 누락: {exc}") from exc

        if not isinstance(items, list):
            raise WeatherApiError("응답 item 형식이 list가 아닙니다.")

        obs = {
            item["category"]: item["obsrValue"]
            for item in items
            if "category" in item and "obsrValue" in item
        }
        logger.info(f"기상청 API 파싱 성공: 항목 수={len(obs)}")

        pty = obs.get("PTY", "0")
        rn1 = obs.get("RN1", "0")
        vec = obs.get("VEC", "0")
        wsd = obs.get("WSD", "0")
        precip_str = WeatherClient._format_precipitation(rn1)

        wind_direction = WeatherClient._deg_to_direction(vec)
        wind_degree = float(vec)
        wind_speed = float(wsd)

        logger.info(
            f"날씨 조회 성공 | "
            f"기온={obs.get('T1H')}°C | "
            f"습도={obs.get('REH')}% | "
            f"강수형태={PTY_MAP.get(pty, pty)} | "
            f"1h강수량={precip_str} | "
            f"풍향={wind_direction}({wind_degree:.0f}°) | "
            f"풍속={wind_speed:.1f}m/s | "
            f"기준시각={base_date} {base_time[:2]}:{base_time[2:]}"
        )

        return WeatherData(
            temperature=f"{obs.get('T1H', 'N/A')}°C",
            humidity=f"{obs.get('REH', 'N/A')}%",
            precipitation_type=PTY_MAP.get(pty, pty),
            precipitation_type_emoji=PTY_EMOJI.get(pty, "🌤️"),
            precipitation=precip_str,
            wind_direction=f"{wind_direction} ({wind_degree:.0f}°)",
            wind_speed=f"{wind_speed:.1f}m/s",
            base_date=base_date,
            base_time=base_time,
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session is not None and not self._session.closed:
            await self._session.close()

    async def fetch(self, force_refresh: bool = False) -> Optional[WeatherData]:
        if self._fetch_lock is None:
            import asyncio

            self._fetch_lock = asyncio.Lock()

        if not force_refresh and self._cache and time.monotonic() < self._cache_expires_at:
            logger.debug("날씨 캐시 사용")
            return self._cache

        async with self._fetch_lock:
            if not force_refresh and self._cache and time.monotonic() < self._cache_expires_at:
                logger.debug("날씨 캐시 사용")
                return self._cache

            data = await self._fetch_from_api()
            if data is not None:
                self._cache = data
                self._cache_expires_at = time.monotonic() + self.cache_ttl_seconds
            return data

    async def _fetch_from_api(self) -> Optional[WeatherData]:
        base_date, base_time = self._get_base_datetime()
        params = {
            "serviceKey": self.service_key,
            "numOfRows": "10",
            "pageNo": "1",
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": str(self.nx),
            "ny": str(self.ny),
        }
        logger.info(f"기상청 API 요청: base_date={base_date}, base_time={base_time}")
        try:
            session = await self._get_session()
            async with session.get(WEATHER_API_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
            logger.debug(f"기상청 API 응답 원본: {data}")
            return self._parse_response(data, base_date, base_time)
        except aiohttp.ClientError as e:
            logger.error(f"기상청 API 네트워크 오류: {e}")
        except (WeatherApiError, ValueError) as e:
            logger.error(f"기상청 API 응답 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"날씨 데이터 조회 실패: {e}")
        return None
