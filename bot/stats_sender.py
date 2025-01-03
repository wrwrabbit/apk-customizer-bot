import asyncio
import logging
from datetime import datetime
from typing import Callable, Awaitable, Any

import config
from bot.stats import period_stats


class StatsSender:
    def __init__(self):
        self.last_send_time = datetime.now()

    async def run(self, send_stats: Callable[[int], Awaitable[Any]]):
        logging.info("Starting StatsSender")

        while True:
            if (datetime.now() - self.last_send_time).seconds >= config.STATS_PERIOD:
                await send_stats(config.STATS_CHAT_ID)
                period_stats.clear()
                self.last_send_time = datetime.now()
            await asyncio.sleep(10)
