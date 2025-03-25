import asyncio
import logging
from datetime import datetime
from typing import Callable, Awaitable, Any

import config
from bot.stats import period_stats


class StatsSender:
    def __init__(self):
        self.last_send_time = datetime.now()
        self.force_reset = False

    def reset(self):
        self.force_reset = True

    async def run(self, send_stats: Callable[[int], Awaitable[Any]]):
        logging.info("Starting StatsSender")

        while True:
            if (datetime.now() - self.last_send_time).total_seconds() >= config.STATS_PERIOD or self.force_reset:
                await send_stats(config.STATS_CHAT_ID)
                period_stats.clear()
                self.last_send_time = datetime.now()
                self.force_reset = False
            await asyncio.sleep(10)
