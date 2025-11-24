
# Each facility runs as a thread, serving multiple visitors in parallel.

from __future__ import annotations
import random
import threading
from dataclasses import dataclass
from typing import Optional, List, Any


@dataclass
class InFlightOrder:
    visitor: Any
    eta_minute: int


class BaseFoodFacility(threading.Thread):
    def __init__(self, name: str, service_time: tuple[int, int], capacity: int,
                 order_queue, clock, metrics: Optional[Any] = None, daemon=True):
        super().__init__(daemon=daemon)
        self.name = name
        self.min_service, self.max_service = service_time
        self.capacity = capacity
        self.queue = order_queue
        self.clock = clock
        self.metrics = metrics
        self._lock = threading.Lock()
        self._inflight: List[InFlightOrder] = []

    def _start_order(self, visitor, now_minute):
        cook_time = random.randint(self.min_service, self.max_service)
        eta = now_minute + cook_time
        self._inflight.append(InFlightOrder(visitor=visitor, eta_minute=eta))
        if self.metrics:
            try:
                self.metrics.record_order(visitor.id, self.name, now_minute)
            except Exception:
                pass

    def _finish_orders(self, now_minute):
        finished = [o for o in self._inflight if o.eta_minute <= now_minute]
        self._inflight = [o for o in self._inflight if o.eta_minute > now_minute]
        for order in finished:
            try:
                if hasattr(order.visitor, "on_food_served"):
                    order.visitor.on_food_served(self.name, now_minute)
            except Exception:
                pass
            if self.metrics:
                try:
                    self.metrics.record_served(order.visitor.id, self.name, now_minute)
                except Exception:
                    pass

    def run(self):
        while not self.clock.should_stop():
            now = self.clock.now()
            with self._lock:
                self._finish_orders(now)
                slots = self.capacity - len(self._inflight)
                for _ in range(slots):
                    item = self.queue.dequeue()
                    if not item:
                        break
                    visitor = getattr(item, "obj", item)
                    self._start_order(visitor, now)
            self.clock.sleep_minutes(1)
        self._finish_orders(self.clock.now())


# Specific Facilities

class BurgerTruck(BaseFoodFacility):
    """BurgerTruck: 3–6 minute service time, capacity 10"""
    pass


class IceCreamStand(BaseFoodFacility):
    """IceCreamStand: 2–5 minute service time, capacity 8"""
    pass
