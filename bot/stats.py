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
        self.sources_count = 0
        self.update_start_count = 0
        self.selected_screens: dict[str, int] = self._get_default_screens()
        self.screens: dict[str, int] = self._get_default_screens()

    @staticmethod
    def _get_default_screens() -> dict[str, int]:
        return {"calculator": 0, "note": 0, "loading": 0}

    def clear(self):
        for key in self.__dict__.keys():
            if self.is_screen_field(key):
                self.__dict__[key] = self._get_default_screens()
            else:
                self.__dict__[key] = 0

    @staticmethod
    def is_screen_field(field_name: str) -> bool:
        return field_name in Stats.get_screen_field_names()

    @staticmethod
    def get_screen_field_names() -> list[str]:
        return ["selected_screens", "screens"]


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
        if Stats.is_screen_field(key):
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
def increase_sources_count(stats: Stats):
    stats.sources_count += 1


@do_for_every_stats
def increase_update_start_count(stats: Stats):
    stats.update_start_count += 1


@do_for_every_stats
def increase_selected_screen_stats(stats: Stats, screen: str):
    stats.selected_screens[screen] += 1


@do_for_every_stats
def increase_screen_stats(stats: Stats, screen: str):
    stats.screens[screen] += 1
