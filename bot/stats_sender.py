import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Awaitable, Any, Optional

import config
from bot.stats import clear_period_stats

RETRY_PERIOD = 300


class StatsSender:
    def __init__(self):
        self.last_send_time = datetime.now()
        self.force_reset = False
        self.next_retry_time: Optional[datetime] = None

    def reset(self):
        self.force_reset = True
        self.next_retry_time = None

    def need_to_send(self) -> bool:
        if self.next_retry_time is not None and datetime.now() < self.next_retry_time:
            return False
        if self.force_reset:
            return True
        return (datetime.now() - self.last_send_time).total_seconds() >= config.STATS_PERIOD

    async def run(self, send_stats: Callable[[int], Awaitable[Any]]):
        logging.info("Starting StatsSender")

        while True:
            if self.need_to_send():
                try:
                    await send_stats(config.STATS_CHAT_ID)
                    clear_period_stats()
                    self.last_send_time = datetime.now()
                    self.force_reset = False
                    self.next_retry_time = None
                except Exception:
                    logging.exception("StatsSender failed to send stats")
                    self.next_retry_time = datetime.now() + timedelta(seconds=RETRY_PERIOD)
            await asyncio.sleep(10)
