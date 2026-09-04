import threading


class ConsecutiveFailureTracker:
    def __init__(self, max_failures: int):
        self.max_failures = max_failures
        self._lock = threading.Lock()
        self._failure_count = 0

    def register_result(self, successful: bool) -> bool:
        with self._lock:
            if successful:
                self._failure_count = 0
            else:
                self._failure_count += 1
            return 0 < self.max_failures <= self._failure_count

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count
