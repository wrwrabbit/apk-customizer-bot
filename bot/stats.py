from functools import wraps
from typing import Callable


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
        self.screens: dict[str, int] = {"calculator": 0, "note": 0, "loading": 0}

    @staticmethod
    def _get_default_screens() -> dict[str, int]:
        return {"calculator": 0, "note": 0, "loading": 0}

    def format(self) -> str:
        main_text = "\n".join([f"{k}: {v}" for k, v in self.__dict__.items() if k != "screens"])
        screen_text = "\n".join([f"• {k}: {v}" for k, v in self.screens.items()])
        return "\n".join([main_text, screen_text])

    def clear(self):
        for key in self.__dict__.keys():
            if key == "screens":
                self.screens = self._get_default_screens()
            else:
                self.__dict__[key] = 0


period_stats = Stats()
uptime_stats = Stats()


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
def increase_screen_stats(stats: Stats, screen: str):
    stats.screens[screen] += 1
