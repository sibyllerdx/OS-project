import threading, random

class MaintenanceDaemon(threading.Thread):
    def __init__(self, rides, clock, mean_uptime=120, mean_repair=15, daemon=True):
        super().__init__(daemon=daemon)
        self.rides = list(rides)
        self.clock = clock
        self.mean_uptime = max(1, int(mean_uptime))
        self.mean_repair = max(1, int(mean_repair))
        self._uptime_left = {r.name: self._sample_uptime() for r in self.rides}

    def _sample_uptime(self):  return max(1, int(random.expovariate(1.0 / self.mean_uptime)))
    def _sample_repair(self):  return max(1, int(random.expovariate(1.0 / self.mean_repair)))

    def _is_broken(self, ride):
        # Prefer ride.is_broken(); fallback: status() contains "broken"
        f = getattr(ride, "is_broken", None)
        if callable(f): return bool(f())
        status = getattr(ride, "status", lambda: "open")()
        return isinstance(status, str) and "broken" in status.lower()

    def run(self):
        while not self.clock.should_stop():
            for ride in self.rides:
                # --- new guard: do nothing while the ride is down ---
                is_broken = getattr(ride, "is_broken", None)
                if callable(is_broken) and is_broken():
                    continue

                name = ride.name
                self._uptime_left[name] -= 1
                if self._uptime_left[name] <= 0:
                    repair_minutes = self._sample_repair()
                    try:
                        ride.break_for(repair_minutes)
                    except Exception:
                        pass
                    self._uptime_left[name] = self._sample_uptime()
            self.clock.sleep_minutes(1)
