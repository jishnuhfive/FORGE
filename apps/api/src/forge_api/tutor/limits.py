"""A conservative per-user tutor cap, in memory only.

In addition to the one-in-flight guard and cooldown shared with the other AI
routes, a user may send a bounded number of tutor questions per hour. Nothing is
stored beyond timestamps in process memory; restarting resets it.
"""

from collections import deque
from threading import Lock
from time import monotonic

MAX_PER_HOUR = 30
WINDOW_SECONDS = 3600
MAX_USERS = 1024


class HourlyCap:
    def __init__(self, limit: int = MAX_PER_HOUR, window: int = WINDOW_SECONDS) -> None:
        self._limit = limit
        self._window = window
        self._lock = Lock()
        self._sent: dict[str, deque[float]] = {}

    def acquire(self, user_id: str) -> int | None:
        """Record a request; return None if allowed, else seconds until it is."""
        now = monotonic()
        with self._lock:
            if user_id not in self._sent and len(self._sent) >= MAX_USERS:
                # Fail closed rather than grow without bound.
                self._sent = {
                    k: v for k, v in self._sent.items() if v and v[-1] > now - 60
                }
                if len(self._sent) >= MAX_USERS:
                    return self._window
            history = self._sent.setdefault(user_id, deque())
            while history and history[0] <= now - self._window:
                history.popleft()
            if len(history) >= self._limit:
                return max(1, int(history[0] + self._window - now) + 1)
            history.append(now)
            return None
