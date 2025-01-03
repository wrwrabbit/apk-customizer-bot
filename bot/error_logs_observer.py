import asyncio
import logging
from typing import Callable, Awaitable, Any

from crud.error_logs_crud import ErrorLogsCRUD
from db import engine


class ErrorLogsObserver:
    @staticmethod
    async def run(send_error: Callable[[str], Awaitable[Any]]):
        logging.info("Starting ErrorLogsObserver")
        error_logs = ErrorLogsCRUD(engine)
        while True:
            error_log = error_logs.pop_log()
            while error_log is not None:
                await send_error(error_log.text)
                error_log = error_logs.pop_log()
            await asyncio.sleep(1)
