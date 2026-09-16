import asyncio
import logging
import traceback
from datetime import datetime
from typing import Callable, Awaitable, Any, Optional

import config
import db
import utils
from crud.error_logs_crud import ErrorLogsCRUD
from crud.orders_crud import OrdersCRUD
from crud.workers_crud import WorkersCRUD
from schemas.order_status import OrderStatus, STATUSES_BUILDING
from .stats import build_time_stats

CHECK_PERIOD_SEC = 60


class DangerObserver:
    def __init__(self, orders: OrdersCRUD, workers: WorkersCRUD):
        self.orders = orders
        self.workers = workers
        self.long_queue_notified = False
        self.no_workers_notified = False
        self.notified_long_build_order_ids: set[int] = set()

    async def run(self, send_alert: Callable[[str], Awaitable[Any]]):
        logging.info("Starting DangerObserver")
        while True:
            await self.check(send_alert)
            await asyncio.sleep(CHECK_PERIOD_SEC)

    async def check(self, send_alert: Callable[[str], Awaitable[Any]]):
        checks = [self.check_queue_length, self.check_online_workers, self.check_long_builds]
        for check in checks:
            try:
                await check(send_alert)
            except Exception:
                self.log_exception()

    @staticmethod
    def log_exception():
        exception_text = traceback.format_exc()
        logging.exception("During DangerObserver the following exception occurred")
        try:
            ErrorLogsCRUD(db.engine).add_log(
                f"During DangerObserver the following exception occurred:\n\n{exception_text}")
        except Exception:
            logging.exception("DangerObserver failed to save the error log to the database")

    async def check_queue_length(self, send_alert: Callable[[str], Awaitable[Any]]):
        queue_length = self.orders.get_count_of_orders_by_status([OrderStatus.queued, OrderStatus.update_queued])
        if queue_length > config.MAX_QUEUE_LENGTH:
            if not self.long_queue_notified:
                await send_alert(f"The queue is too long: {queue_length} orders "
                                 f"(max {config.MAX_QUEUE_LENGTH}).")
                self.long_queue_notified = True
        else:
            self.long_queue_notified = False

    async def check_online_workers(self, send_alert: Callable[[str], Awaitable[Any]]):
        online_count = self.workers.get_online_workers_count(config.CONSIDER_WORKER_OFFLINE_AFTER_SEC)
        if online_count == 0:
            if not self.no_workers_notified:
                await send_alert(self.make_no_workers_alert())
                self.no_workers_notified = True
        else:
            self.no_workers_notified = False

    def make_no_workers_alert(self) -> str:
        all_workers = self.workers.get_all_workers()
        if not all_workers:
            return "There are no active build workers: no workers are registered."
        last_online_date = max(worker.last_online_date for worker in all_workers)
        offline_duration = max((datetime.now() - last_online_date).total_seconds(), 0)
        return (f"There are no active build workers: 0 of {len(all_workers)} workers are online. "
                f"The last worker was online {utils.format_duration(offline_duration)} ago.")

    async def check_long_builds(self, send_alert: Callable[[str], Awaitable[Any]]):
        build_time_stats.prune_build_start_times(self.orders.get_order_ids_by_status(STATUSES_BUILDING))
        long_running_builds = build_time_stats.get_long_running_builds(config.CONSIDER_BUILD_STUCK_AFTER_SEC)
        stuck_order_ids = set()
        for order_id, elapsed in long_running_builds:
            order = self.orders.get_order(order_id)
            if order is None or order.status not in STATUSES_BUILDING:
                continue
            stuck_order_ids.add(order_id)
            if order_id not in self.notified_long_build_order_ids:
                await send_alert(self.make_long_build_alert(order, elapsed))
                self.notified_long_build_order_ids.add(order_id)
        self.notified_long_build_order_ids &= stuck_order_ids

    def make_long_build_alert(self, order, elapsed: float) -> str:
        worker_name = self.get_worker_name(order.worker_id)
        if worker_name is None:
            worker_text = f"There is no worker assigned to the order (status: {order.status})."
        else:
            worker_text = f"Worker: {worker_name}."
        return (f"The build of the order #{order.id} takes too long: {utils.format_duration(elapsed)} "
                f"(threshold {utils.format_duration(config.CONSIDER_BUILD_STUCK_AFTER_SEC)}). {worker_text}")

    def get_worker_name(self, worker_id: Optional[int]) -> Optional[str]:
        if worker_id is None:
            return None
        worker = self.workers.get_worker(worker_id)
        return worker.name if worker is not None else None
