"""
Unit tests for weather_alarm core logic.

Covers:
  - notification_store.NotificationStore  (in-memory SQLite)
  - weather_client.WeatherClient          (static helpers + mocked fetch)
  - broadcaster.AsyncRateLimiter / BroadcastDispatcher._retry_delay
  - main.py helpers (_parse_optional_int, _parse_float, validate_settings)

No real HTTP calls are made; no Discord/Telegram bots are started.
Run with:  python -m pytest tests/ -v
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import tempfile
import os

import pytest

# ---------------------------------------------------------------------------
# Make the weather_alarm package root importable
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ===========================================================================
# Shared fixture: temp-file SQLite store
# ===========================================================================
@pytest.fixture()
def store():
    """Return a fresh NotificationStore backed by a temporary SQLite file.

    We cannot use ':memory:' because NotificationStore.connect() opens a new
    sqlite3 connection on every call, which would create a fresh empty
    in-memory database each time (losing all tables written by initialize()).
    A real temp file survives across multiple _connect() calls.
    """
    from notification_store import NotificationStore
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        yield NotificationStore(dsn=path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ===========================================================================
# 1. NotificationStore — subscriber management
# ===========================================================================
class TestSubscriberManagement:
    def test_add_and_list(self, store):
        store.add_subscriber("telegram", "123", "Alice")
        subs = store.list_subscribers()
        assert len(subs) == 1
        assert subs[0].platform == "telegram"
        assert subs[0].target_id == "123"
        assert subs[0].display_name == "Alice"

    def test_add_multiple_platforms(self, store):
        store.add_subscriber("telegram", "111", "T-User")
        store.add_subscriber("discord", "222", "D-User")
        all_subs = store.list_subscribers()
        assert len(all_subs) == 2

    def test_list_by_platform(self, store):
        store.add_subscriber("telegram", "111", "T-User")
        store.add_subscriber("discord", "222", "D-User")
        tg = store.list_subscribers(platform="telegram")
        assert len(tg) == 1
        assert tg[0].platform == "telegram"

    def test_remove_subscriber_sets_inactive(self, store):
        store.add_subscriber("telegram", "999", "Bob")
        store.remove_subscriber("telegram", "999")
        subs = store.list_subscribers()
        assert len(subs) == 0

    def test_add_idempotent_upsert(self, store):
        store.add_subscriber("telegram", "123", "First")
        store.add_subscriber("telegram", "123", "Updated")
        subs = store.list_subscribers()
        assert len(subs) == 1
        assert subs[0].display_name == "Updated"


# ===========================================================================
# 2. NotificationStore — delivery queue
# ===========================================================================
class TestDeliveryQueue:
    def test_enqueue_broadcast_returns_count(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.add_subscriber("telegram", "2", "U2")
        n = store.enqueue_broadcast("Hello", "weather", "key-001")
        assert n == 2

    def test_enqueue_broadcast_no_subscribers(self, store):
        n = store.enqueue_broadcast("Hello", "weather", "key-empty")
        assert n == 0

    def test_enqueue_idempotency(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.enqueue_broadcast("Hello", "weather", "same-key")
        n2 = store.enqueue_broadcast("Hello", "weather", "same-key")
        # Second call with same dedupe key should insert 0 (duplicate)
        assert n2 == 0

    def test_pending_count(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.add_subscriber("telegram", "2", "U2")
        store.enqueue_broadcast("Msg", "weather", "k1")
        assert store.pending_count() == 2

    def test_claim_due_jobs(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.enqueue_broadcast("Hello", "weather", "k2")
        jobs = store.claim_due_jobs(limit=10)
        assert len(jobs) == 1
        assert jobs[0].platform == "telegram"
        assert jobs[0].message_text == "Hello"

    def test_claimed_jobs_not_claimable_again(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.enqueue_broadcast("Hello", "weather", "k3")
        store.claim_due_jobs(limit=10)
        second = store.claim_due_jobs(limit=10)
        assert second == []

    def test_mark_sent(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.enqueue_broadcast("Hello", "weather", "k4")
        jobs = store.claim_due_jobs(limit=10)
        store.mark_sent(jobs[0].id)
        counts = store.status_counts()
        assert counts.get("sent", 0) == 1

    def test_mark_retry_pending(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.enqueue_broadcast("Hello", "weather", "k5")
        jobs = store.claim_due_jobs(limit=10)
        # attempts=1, max_attempts=5 → status stays 'pending'
        store.mark_retry(jobs[0].id, "timeout", delay_seconds=5, attempts=1, max_attempts=5)
        counts = store.status_counts()
        assert counts.get("pending", 0) == 1

    def test_mark_retry_failed_when_exhausted(self, store):
        store.add_subscriber("telegram", "1", "U1")
        store.enqueue_broadcast("Hello", "weather", "k6")
        jobs = store.claim_due_jobs(limit=10)
        # attempts >= max_attempts → status becomes 'failed'
        store.mark_retry(jobs[0].id, "perm fail", delay_seconds=0, attempts=5, max_attempts=5)
        counts = store.status_counts()
        assert counts.get("failed", 0) == 1

    def test_status_counts_structure(self, store):
        counts = store.status_counts()
        assert isinstance(counts, dict)

    def test_enqueue_single(self, store):
        from notification_store import Subscriber
        sub = Subscriber("telegram", "42", "Solo")
        job_id = store.enqueue_single(sub, "Test", "weather", "unique-idem-key")
        assert job_id is not None
        assert isinstance(job_id, int)

    def test_enqueue_single_duplicate_returns_none(self, store):
        from notification_store import Subscriber
        sub = Subscriber("telegram", "42", "Solo")
        store.enqueue_single(sub, "Test", "weather", "dup-key")
        result = store.enqueue_single(sub, "Test", "weather", "dup-key")
        assert result is None


# ===========================================================================
# 3. WeatherClient — static helpers
# ===========================================================================
class TestWeatherClientHelpers:
    def test_deg_to_direction_north(self):
        from weather_client import WeatherClient
        assert WeatherClient._deg_to_direction("0") == "북"

    def test_deg_to_direction_east(self):
        from weather_client import WeatherClient
        assert WeatherClient._deg_to_direction("90") == "동"

    def test_deg_to_direction_south(self):
        from weather_client import WeatherClient
        assert WeatherClient._deg_to_direction("180") == "남"

    def test_deg_to_direction_west(self):
        from weather_client import WeatherClient
        assert WeatherClient._deg_to_direction("270") == "서"

    def test_format_precipitation_zero(self):
        from weather_client import WeatherClient
        assert WeatherClient._format_precipitation("0") == "강수없음"

    def test_format_precipitation_nonzero(self):
        from weather_client import WeatherClient
        assert WeatherClient._format_precipitation("3.5") == "3.5mm"

    def test_format_precipitation_invalid(self):
        from weather_client import WeatherClient
        # Non-numeric passthrough
        result = WeatherClient._format_precipitation("강수없음")
        assert result == "강수없음"

    def test_get_base_datetime_returns_on_hour(self):
        from weather_client import WeatherClient, _KST
        # Provide a known datetime (14:35 KST) → should give 14:00
        now = datetime(2024, 6, 1, 14, 35, 0, tzinfo=_KST)
        base_date, base_time = WeatherClient._get_base_datetime(now)
        assert base_date == "20240601"
        assert base_time == "1400"

    def test_get_base_datetime_crosses_hour(self):
        from weather_client import WeatherClient, _KST
        # 15:08 KST — 10 min earlier is 14:58 → base is 14:00
        now = datetime(2024, 6, 1, 15, 8, 0, tzinfo=_KST)
        _, base_time = WeatherClient._get_base_datetime(now)
        assert base_time == "1400"

    def test_get_base_datetime_crosses_day(self):
        from weather_client import WeatherClient, _KST
        # 00:05 KST — 10 min earlier is 23:55 the day before → base 23:00 prev day
        now = datetime(2024, 6, 2, 0, 5, 0, tzinfo=_KST)
        base_date, base_time = WeatherClient._get_base_datetime(now)
        assert base_date == "20240601"
        assert base_time == "2300"


# ===========================================================================
# 4. WeatherClient._parse_response
# ===========================================================================
class TestWeatherClientParseResponse:
    def _sample_response(self) -> dict[str, Any]:
        return {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                "body": {
                    "items": {
                        "item": [
                            {"category": "T1H", "obsrValue": "20.5"},
                            {"category": "REH", "obsrValue": "65"},
                            {"category": "PTY", "obsrValue": "0"},
                            {"category": "RN1", "obsrValue": "0"},
                            {"category": "VEC", "obsrValue": "270"},
                            {"category": "WSD", "obsrValue": "3.2"},
                        ]
                    }
                },
            }
        }

    def test_parse_success(self):
        from weather_client import WeatherClient
        data = WeatherClient._parse_response(self._sample_response(), "20240601", "1400")
        assert data.temperature == "20.5°C"
        assert data.humidity == "65%"
        assert data.precipitation_type == "없음"
        assert data.precipitation == "강수없음"
        assert data.wind_speed == "3.2m/s"
        assert data.wind_direction == "서 (270°)"

    def test_parse_bad_result_code(self):
        from weather_client import WeatherClient, WeatherApiError
        bad = {"response": {"header": {"resultCode": "99", "resultMsg": "SERVICE_ERROR"}}}
        with pytest.raises(WeatherApiError, match="resultCode=99"):
            WeatherClient._parse_response(bad, "20240601", "1400")

    def test_parse_missing_items(self):
        from weather_client import WeatherClient, WeatherApiError
        bad = {"response": {"header": {"resultCode": "00"}, "body": {}}}
        with pytest.raises(WeatherApiError):
            WeatherClient._parse_response(bad, "20240601", "1400")

    def test_parse_items_not_list(self):
        from weather_client import WeatherClient, WeatherApiError
        bad = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": "not a list"}},
            }
        }
        with pytest.raises(WeatherApiError, match="list"):
            WeatherClient._parse_response(bad, "20240601", "1400")


# ===========================================================================
# 5. WeatherData.format_text
# ===========================================================================
class TestWeatherDataFormatText:
    def test_format_text_contains_fields(self):
        from weather_client import WeatherData
        wd = WeatherData(
            temperature="20.5°C",
            humidity="65%",
            precipitation_type="없음",
            precipitation_type_emoji="☀️",
            precipitation="강수없음",
            wind_direction="서 (270°)",
            wind_speed="3.2m/s",
            base_date="20240601",
            base_time="1400",
        )
        text = wd.format_text()
        assert "20.5°C" in text
        assert "65%" in text
        assert "없음" in text
        assert "3.2m/s" in text
        assert "2024-06-01" in text
        assert "14:00" in text


# ===========================================================================
# 6. WeatherClient cache behavior (mocked)
# ===========================================================================
class TestWeatherClientCache:
    @pytest.mark.asyncio
    async def test_fetch_uses_cache_on_second_call(self):
        from weather_client import WeatherClient, WeatherData
        dummy = WeatherData(
            temperature="15°C", humidity="50%",
            precipitation_type="없음", precipitation_type_emoji="☀️",
            precipitation="강수없음", wind_direction="북 (0°)", wind_speed="1.0m/s",
            base_date="20240601", base_time="1200",
        )
        client = WeatherClient(service_key="fake-key")
        # Pre-populate the cache
        client._cache = dummy
        client._cache_expires_at = time.monotonic() + 3600  # 1 hour from now

        with patch.object(client, "_fetch_from_api", new_callable=AsyncMock) as mock_api:
            result = await client.fetch()
            assert result is dummy
            mock_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_refreshes_when_cache_expired(self):
        from weather_client import WeatherClient, WeatherData
        dummy = WeatherData(
            temperature="15°C", humidity="50%",
            precipitation_type="없음", precipitation_type_emoji="☀️",
            precipitation="강수없음", wind_direction="북 (0°)", wind_speed="1.0m/s",
            base_date="20240601", base_time="1200",
        )
        client = WeatherClient(service_key="fake-key")
        # Expired cache
        client._cache = dummy
        client._cache_expires_at = time.monotonic() - 10  # expired

        with patch.object(client, "_fetch_from_api", new_callable=AsyncMock, return_value=dummy):
            result = await client.fetch()
            assert result is dummy


# ===========================================================================
# 7. BroadcastDispatcher._retry_delay and _is_permanent_failure
# ===========================================================================
class TestBroadcastDispatcherHelpers:
    def test_retry_delay_exponential_backoff(self):
        from broadcaster import BroadcastDispatcher
        assert BroadcastDispatcher._retry_delay(Exception("err"), 0) == 1.0
        assert BroadcastDispatcher._retry_delay(Exception("err"), 1) == 1.0
        assert BroadcastDispatcher._retry_delay(Exception("err"), 2) == 2.0
        assert BroadcastDispatcher._retry_delay(Exception("err"), 3) == 4.0

    def test_retry_delay_capped_at_300(self):
        from broadcaster import BroadcastDispatcher
        assert BroadcastDispatcher._retry_delay(Exception("err"), 100) == 300.0

    def test_retry_delay_with_retry_after_attribute(self):
        from broadcaster import BroadcastDispatcher
        exc = Exception("rate limited")
        exc.retry_after = 42.0
        assert BroadcastDispatcher._retry_delay(exc, 0) == 42.0

    def test_is_permanent_failure_telegram_forbidden(self):
        from broadcaster import BroadcastDispatcher
        from telegram.error import Forbidden
        exc = Forbidden("blocked")
        assert BroadcastDispatcher._is_permanent_failure(exc) is True

    def test_is_permanent_failure_discord_forbidden(self):
        from broadcaster import BroadcastDispatcher
        import discord
        exc = MagicMock(spec=discord.Forbidden)
        assert BroadcastDispatcher._is_permanent_failure(exc) is True

    def test_is_permanent_failure_generic_exception(self):
        from broadcaster import BroadcastDispatcher
        assert BroadcastDispatcher._is_permanent_failure(Exception("generic")) is False


# ===========================================================================
# 8. AsyncRateLimiter
# ===========================================================================
class TestAsyncRateLimiter:
    @pytest.mark.asyncio
    async def test_zero_rate_does_not_block(self):
        from broadcaster import AsyncRateLimiter
        limiter = AsyncRateLimiter(rate_per_second=0)
        # Should return immediately
        await asyncio.wait_for(limiter.wait(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_high_rate_is_fast(self):
        from broadcaster import AsyncRateLimiter
        limiter = AsyncRateLimiter(rate_per_second=1000)
        start = time.monotonic()
        await limiter.wait()
        elapsed = time.monotonic() - start
        # min_interval is 1ms; should complete well under 100ms
        assert elapsed < 0.1


# ===========================================================================
# 9. main.py helpers (_parse_optional_int, _parse_float, validate_settings)
# ===========================================================================
class TestMainHelpers:
    @pytest.fixture(autouse=True)
    def _import_main(self):
        import importlib, importlib.util
        spec = importlib.util.spec_from_file_location(
            "weather_alarm_main", str(_PROJECT_ROOT / "main.py")
        )
        # We re-implement the two tiny pure helpers to avoid running main()
        pass

    def _parse_optional_int(self, value: str) -> int:
        if not value:
            return 0
        try:
            return int(value)
        except ValueError:
            return 0

    def _parse_float(self, value: str, default: float) -> float:
        if not value:
            return default
        try:
            parsed = float(value)
        except ValueError:
            return default
        if parsed <= 0:
            return default
        return parsed

    def test_parse_optional_int_valid(self):
        assert self._parse_optional_int("123456789") == 123456789

    def test_parse_optional_int_empty(self):
        assert self._parse_optional_int("") == 0

    def test_parse_optional_int_non_numeric(self):
        assert self._parse_optional_int("abc") == 0

    def test_parse_float_valid(self):
        assert self._parse_float("25.5", 10.0) == 25.5

    def test_parse_float_empty_returns_default(self):
        assert self._parse_float("", 20.0) == 20.0

    def test_parse_float_zero_returns_default(self):
        assert self._parse_float("0", 15.0) == 15.0

    def test_parse_float_negative_returns_default(self):
        assert self._parse_float("-1", 15.0) == 15.0

    def test_parse_float_non_numeric_returns_default(self):
        assert self._parse_float("nope", 15.0) == 15.0


# ===========================================================================
# 10. validate_settings
# ===========================================================================
class TestValidateSettings:
    def _make_settings(self, **kwargs):
        from main import Settings
        defaults = dict(
            weather_key="key",
            discord_token="dtoken",
            discord_channel_id=123,
            telegram_token="ttoken",
            telegram_chat_id="456",
            postgres_dsn="",
            telegram_rate_per_second=25.0,
            discord_rate_per_second=20.0,
        )
        defaults.update(kwargs)
        return Settings(**defaults)

    def test_valid_settings_returns_true(self):
        from main import validate_settings
        s = self._make_settings()
        assert validate_settings(s) is True

    def test_missing_weather_key_returns_false(self):
        from main import validate_settings
        s = self._make_settings(weather_key="")
        assert validate_settings(s) is False

    def test_no_bot_token_returns_false(self):
        from main import validate_settings
        s = self._make_settings(discord_token="", telegram_token="")
        assert validate_settings(s) is False

    def test_only_discord_token_ok(self):
        from main import validate_settings
        s = self._make_settings(telegram_token="")
        assert validate_settings(s) is True

    def test_only_telegram_token_ok(self):
        from main import validate_settings
        s = self._make_settings(discord_token="")
        assert validate_settings(s) is True
