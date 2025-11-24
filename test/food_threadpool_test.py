
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from food import BurgerTruck, IceCreamStand

class DummyClock:
    def __init__(self, total_minutes=25):
        self._minute = 0
        self._stop = False
        self._limit = total_minutes
    def now(self):
        return self._minute
    def sleep_minutes(self, n):
        time.sleep(0.05 * n)
        self._minute += n
        if self._minute >= self._limit:
            self._stop = True
    def should_stop(self):
        return self._stop

class FoodQueue:
    def __init__(self, cap=1000):
        self._cap = cap
        self._q = []
        self._lock = threading.Lock()
    def enqueue(self, visitor, now_minute=0):
        with self._lock:
            if len(self._q) >= self._cap:
                return False
            self._q.append(type("Item", (), {"obj": visitor, "enq_min": now_minute})())
            return True
    def dequeue(self):
        with self._lock:
            return self._q.pop(0) if self._q else None
    def size(self):
        with self._lock:
            return len(self._q)

class Visitor:
    def __init__(self, vid):
        self.id = vid
    def on_food_served(self, facility_name, minute):
        print(f"[minute {minute}] Visitor {self.id} served at {facility_name}")

class DummyMetrics:
    def record_order(self, vid, name, minute):
        print(f"METRIC order v{vid} -> {name} at {minute}")
    def record_served(self, vid, name, minute):
        print(f"METRIC served v{vid} <- {name} at {minute}")

def main():
    clock = DummyClock(total_minutes=25)
    metrics = DummyMetrics()

    burger_q = FoodQueue()
    ice_q = FoodQueue()

    burger = BurgerTruck(name="BurgerTruck", service_time=(3,6), capacity=10,
                         order_queue=burger_q, clock=clock, metrics=metrics)
    ice = IceCreamStand(name="IceCreamStand", service_time=(2,5), capacity=8,
                        order_queue=ice_q, clock=clock, metrics=metrics)

    burger.start()
    ice.start()

    def enqueue_to(q, start_vid, count):
        for i in range(count):
            v = Visitor(start_vid + i)
            q.enqueue(v, now_minute=clock.now())
            time.sleep(0.02)

    with ThreadPoolExecutor(max_workers=4) as pool:
        pool.submit(enqueue_to, burger_q, 0, 12)
        time.sleep(0.2)
        pool.submit(enqueue_to, ice_q, 100, 15)
        time.sleep(0.2)
        pool.submit(enqueue_to, burger_q, 1000, 8)
        pool.submit(enqueue_to, ice_q, 200, 6)

    burger.join()
    ice.join()
    print("Done.")

if __name__ == "__main__":
    main()
