
import threading
import time
import random
from enum import Enum


# ---------- Clock (controls simulated time) ----------
class Clock:
    """
    Simulated clock for the park.
    - speed_factor: how fast simulated minutes pass (in real seconds)
    - open_minutes: total simulation duration in simulated minutes
    """

    def __init__(self, speed_factor: float = 0.3, open_minutes: int = 600):
        self._speed = max(speed_factor, 0.001)  # prevent zero or negative
        self._open_minutes = open_minutes
        self._now = 0
        self._stop = threading.Event()

    def now(self) -> int:
        """Return the current simulated minute."""
        return self._now

    def sleep_minutes(self, minutes: int):
        """Sleep for a number of simulated minutes (scaled by speed)."""
        for _ in range(minutes):
            if self._stop.is_set(): #check if someone has asked the simulation to stop
                return
            time.sleep(self._speed)
            self._now += 1

    def run_until_close(self):
        """Run until closing time."""
        while self._now < self._open_minutes and not self._stop.is_set():
            time.sleep(self._speed)
            self._now += 1

    def stop(self):
        """Stop the simulation clock."""
        self._stop.set()

    def should_stop(self) -> bool:
        """Check if the clock or simulation should stop."""
        return self._stop.is_set() or self._now >= self._open_minutes

    def seconds_per_minute(self) -> float:
        """Return how many real seconds equal one simulated minute."""
        return self._speed


# ---------- Status Enum ----------
class Status(Enum):
    OPEN = "open"
    BOARDING = "boarding"
    BROKEN = "broken"
    CLOSED = "closed"


# ---------- Helper: Weighted random choice ----------
def pick_weighted(items, weights):
    """
    Pick a random item from a list with weighted probabilities.
    Example:
        pick_weighted(['A', 'B', 'C'], [0.6, 0.3, 0.1])
    """
    total = sum(weights)
    r = random.random() * total
    upto = 0
    for item, w in zip(items, weights):
        upto += w
        if r <= upto:
            return item
    return items[-1]


