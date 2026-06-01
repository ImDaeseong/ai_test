import asyncio
from typing import Awaitable, Callable, Dict

import discord
from loguru import logger
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from notification_store import DeliveryJob, NotificationStore

SendFunc = Callable[[str, str], Awaitable[None]]


class AsyncRateLimiter:
    def __init__(self, rate_per_second: float):
        self.min_interval = 1.0 / rate_per_second if rate_per_second > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next_allowed_at = 0.0

    async def wait(self) -> None:
        if self.min_interval <= 0:
            return
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            if now < self._next_allowed_at:
                await asyncio.sleep(self._next_allowed_at - now)
                now = loop.time()
            self._next_allowed_at = now + self.min_interval


class BroadcastDispatcher:
    def __init__(
        self,
        store: NotificationStore,
        senders: Dict[str, SendFunc],
        batch_size: int = 100,
        idle_sleep_seconds: float = 1.0,
        max_attempts: int = 5,
        telegram_rate_per_second: float = 25.0,
        discord_rate_per_second: float = 20.0,
    ):
        self.store = store
        self.senders = senders
        self.batch_size = batch_size
        self.idle_sleep_seconds = idle_sleep_seconds
        self.max_attempts = max_attempts
        self.limiters = {
            "telegram": AsyncRateLimiter(telegram_rate_per_second),
            "discord": AsyncRateLimiter(discord_rate_per_second),
        }

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            processed = await self.process_once()
            if processed == 0:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=self.idle_sleep_seconds)
                except asyncio.TimeoutError:
                    pass

    async def process_once(self) -> int:
        jobs = self.store.claim_due_jobs(limit=self.batch_size)
        if not jobs:
            return 0
        await asyncio.gather(*(self._process_job(job) for job in jobs))
        return len(jobs)

    async def _process_job(self, job: DeliveryJob) -> None:
        sender = self.senders.get(job.platform)
        if sender is None:
            self.store.mark_retry(
                job.id,
                f"지원하지 않는 플랫폼: {job.platform}",
                delay_seconds=0,
                attempts=self.max_attempts,
                max_attempts=self.max_attempts,
            )
            return

        limiter = self.limiters.get(job.platform)
        if limiter is not None:
            await limiter.wait()

        try:
            await sender(job.target_id, job.message_text)
            self.store.mark_sent(job.id)
            logger.info(f"알림 전송 완료: platform={job.platform}, target_id={job.target_id}, job_id={job.id}")
        except Exception as exc:
            delay = self._retry_delay(exc, job.attempts)
            if self._is_permanent_failure(exc):
                self.store.remove_subscriber(job.platform, job.target_id)
                delay = 0
                attempts = self.max_attempts
            else:
                attempts = job.attempts
            self.store.mark_retry(
                job.id,
                repr(exc),
                delay_seconds=delay,
                attempts=attempts,
                max_attempts=self.max_attempts,
            )
            logger.warning(
                f"알림 전송 실패: platform={job.platform}, target_id={job.target_id}, "
                f"job_id={job.id}, retry_after={delay:.1f}s, error={exc}"
            )

    @staticmethod
    def _retry_delay(exc: Exception, attempts: int) -> float:
        if isinstance(exc, RetryAfter):
            return float(exc.retry_after)
        retry_after = getattr(exc, "retry_after", None)
        if retry_after is not None:
            return float(retry_after)
        return min(300.0, 2.0 ** max(0, attempts - 1))

    @staticmethod
    def _is_permanent_failure(exc: Exception) -> bool:
        return isinstance(exc, (Forbidden, BadRequest, discord.Forbidden, discord.NotFound))


def build_telegram_sender(bot) -> SendFunc:
    async def _send(target_id: str, message_text: str) -> None:
        await bot.send_message(chat_id=target_id, text=message_text)

    return _send


def build_discord_sender(client: discord.Client) -> SendFunc:
    async def _send(target_id: str, message_text: str) -> None:
        await client.wait_until_ready()
        channel_id = int(target_id)
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        await channel.send(message_text)

    return _send
