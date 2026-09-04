from datetime import datetime
from functools import wraps
from typing import Callable, Optional


class Stats:
    def __init__(self):
        self.bot_start_count = 0
        self.configuration_start_count = 0
        self.cancel_count = 0
        self.queued_count = 0
        self.queued_low_priority_count = 0
        self.build_start_count = 0
        self.successful_build_count = 0
        self.failed_build_count = 0
        self.retried_build_count = 0
        self.sources_count = 0
        self.update_start_count = 0
        self.update_finished_count = 0
        self.update_cancel_count = 0
        self.update_customize_count = 0
        self.selected_screens: dict[str, int] = self._get_default_screens()
        self.screens: dict[str, int] = self._get_default_screens()
        self.update_screens: dict[str, int] = self._get_default_screens()
        self.worker_successful_builds: dict[int, int] = {}
        self.worker_failed_builds: dict[int, int] = {}

    @staticmethod
    def _get_default_screens() -> dict[str, int]:
        return {"calculator": 0, "note": 0, "loading": 0}

    def clear(self):
        for key in self.__dict__.keys():
            if self.is_screen_field(key):
                self.__dict__[key] = self._get_default_screens()
            elif self.is_worker_field(key):
                self.__dict__[key] = {}
            else:
                self.__dict__[key] = 0

    @staticmethod
    def is_screen_field(field_name: str) -> bool:
        return field_name in Stats.get_screen_field_names()

    @staticmethod
    def get_screen_field_names() -> list[str]:
        return ["selected_screens", "screens", "update_screens"]

    @staticmethod
    def is_worker_field(field_name: str) -> bool:
        return field_name in Stats.get_worker_field_names()

    @staticmethod
    def get_worker_field_names() -> list[str]:
        return ["worker_successful_builds", "worker_failed_builds"]


period_stats = Stats()
uptime_stats = Stats()


def append_format_line(text: str, key: str, sub_key: Optional[str]) -> str:
    value = uptime_stats.__dict__[key]
    period_value = period_stats.__dict__[key]
    if sub_key:
        value = value[sub_key]
        period_value = period_value[sub_key]
    if text:
        text += "\n"
    text += f"{'• ' + sub_key if sub_key else key}: {value}"
    if period_value:
        text += f" (+{period_value})"
    return text


def format_stats() -> str:
    text = ""
    for key in uptime_stats.__dict__.keys():
        if Stats.is_screen_field(key) or Stats.is_worker_field(key):
            continue
        text = append_format_line(text, key, None)
    for key in Stats.get_screen_field_names():
        sum_count = sum(uptime_stats.__dict__[key].values())
        text += f"\n<u>{key} ({sum_count})</u>:"
        for screen_key in uptime_stats.__dict__[key].keys():
            text = append_format_line(text, key, screen_key)
    return text


def do_for_every_stats(fun: Callable[[Stats, ...], None]):
    @wraps(fun)
    def wrapper(*args):
        fun(period_stats, *args)
        fun(uptime_stats, *args)
    return wrapper


@do_for_every_stats
def increase_start_count(stats: Stats):
    stats.bot_start_count += 1


@do_for_every_stats
def increase_configuration_start_count(stats: Stats):
    stats.configuration_start_count += 1


@do_for_every_stats
def increase_cancel_count(stats: Stats):
    stats.cancel_count += 1


@do_for_every_stats
def increase_queued_count(stats: Stats):
    stats.queued_count += 1


@do_for_every_stats
def increase_queued_low_priority_count(stats: Stats):
    stats.queued_low_priority_count += 1


@do_for_every_stats
def increase_build_start_count(stats: Stats):
    stats.build_start_count += 1


@do_for_every_stats
def increase_successful_build_count(stats: Stats):
    stats.successful_build_count += 1


@do_for_every_stats
def increase_failed_build_count(stats: Stats):
    stats.failed_build_count += 1


@do_for_every_stats
def increase_retried_build_count(stats: Stats):
    stats.retried_build_count += 1


@do_for_every_stats
def increase_sources_count(stats: Stats):
    stats.sources_count += 1


@do_for_every_stats
def increase_update_start_count(stats: Stats):
    stats.update_start_count += 1


@do_for_every_stats
def increase_update_finished_count(stats: Stats):
    stats.update_finished_count += 1


@do_for_every_stats
def increase_update_cancel_count(stats: Stats):
    stats.update_cancel_count += 1


@do_for_every_stats
def increase_update_customize_count(stats: Stats):
    stats.update_customize_count += 1


@do_for_every_stats
def increase_selected_screen_stats(stats: Stats, screen: str):
    stats.selected_screens[screen] += 1


@do_for_every_stats
def increase_screen_stats(stats: Stats, screen: str):
    stats.screens[screen] += 1


@do_for_every_stats
def increase_update_screen_stats(stats: Stats, screen: str):
    stats.update_screens[screen] += 1


@do_for_every_stats
def increase_worker_successful_builds(stats: Stats, worker_id: int):
    stats.worker_successful_builds[worker_id] = stats.worker_successful_builds.get(worker_id, 0) + 1


@do_for_every_stats
def increase_worker_failed_builds(stats: Stats, worker_id: int):
    stats.worker_failed_builds[worker_id] = stats.worker_failed_builds.get(worker_id, 0) + 1


_order_workers: dict[int, int] = {}


def remember_order_worker(order_id: int, worker_id: Optional[int]):
    if worker_id is not None:
        _order_workers[order_id] = worker_id


def increase_worker_build_stats(order_id: int, successful: bool):
    worker_id = _order_workers.pop(order_id, None)
    if worker_id is None:
        return
    if successful:
        increase_worker_successful_builds(worker_id)
    else:
        increase_worker_failed_builds(worker_id)


def prune_order_workers(attributable_order_ids: list[int]):
    attributable_ids = set(attributable_order_ids)
    for order_id in list(_order_workers.keys()):
        if order_id not in attributable_ids:
            _order_workers.pop(order_id, None)


class BuildTimeStats:
    def __init__(self):
        self._build_start_times: dict[int, datetime] = {}
        self.total_build_seconds: float = 0
        self.completed_build_count: int = 0

    def on_build_started(self, order_id: int):
        self._build_start_times[order_id] = datetime.now()

    def on_build_finished(self, order_id: int):
        start = self._build_start_times.pop(order_id, None)
        if start is None:
            return
        self.total_build_seconds += (datetime.now() - start).total_seconds()
        self.completed_build_count += 1

    def on_build_discarded(self, order_id: int):
        self._build_start_times.pop(order_id, None)

    def prune_build_start_times(self, building_order_ids: list[int]):
        building_ids = set(building_order_ids)
        for order_id in list(self._build_start_times.keys()):
            if order_id not in building_ids:
                self._build_start_times.pop(order_id, None)

    def get_longest_build_seconds(self) -> Optional[float]:
        if not self._build_start_times:
            return None
        now = datetime.now()
        return max((now - start).total_seconds() for start in self._build_start_times.values())

    def get_long_running_builds(self, min_seconds: float) -> list[tuple[int, float]]:
        now = datetime.now()
        result = []
        for order_id, start in self._build_start_times.items():
            elapsed = (now - start).total_seconds()
            if elapsed >= min_seconds:
                result.append((order_id, elapsed))
        return result

    def get_average_build_seconds(self) -> Optional[float]:
        if self.completed_build_count == 0:
            return None
        return self.total_build_seconds / self.completed_build_count

    def clear(self):
        self.total_build_seconds = 0
        self.completed_build_count = 0


build_time_stats = BuildTimeStats()


def clear_period_stats():
    period_stats.clear()
    build_time_stats.clear()
