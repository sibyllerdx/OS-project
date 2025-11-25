# source/park/arrival.py
import threading
import random
import numpy as np


class ArrivalGenerator(threading.Thread):
    """
    Generates visitors minute by minute using a Poisson process.

    - curve_points: list of {'minute': int, 'mean': float}
    - visitor_mix:  dict like {'Child': 0.3, 'Tourist': 0.5, ...}
    - jitter:       optional noise added to the mean arrivals per minute
    """
    def __init__(self, clock, park, ids, metrics, curve_points, visitor_mix, jitter: float = 0.0):
        super().__init__(daemon=True)
        self.clock = clock
        self.park = park
        self.ids = ids
        self.metrics = metrics

        # Store (minute, mean) pairs sorted by minute
        self.points = sorted(
            [(int(p["minute"]), float(p["mean"])) for p in curve_points],
            key=lambda x: x[0]
        )

        # Normalize visitor mix
        total = sum(visitor_mix.values())
        self.vtypes = list(visitor_mix.keys())
        self.vweights = [v / total for v in visitor_mix.values()]

        self.jitter = float(jitter or 0.0)

    # ---- curve evaluation ----
    def _mean_at(self, minute: int) -> float:
        """Linear interpolation between control points; clamp at ends."""
        pts = self.points

        if minute <= pts[0][0]:
            return pts[0][1]
        if minute >= pts[-1][0]:
            return pts[-1][1]

        for (m1, y1), (m2, y2) in zip(pts, pts[1:]):
            if m1 <= minute <= m2:
                span = m2 - m1
                t = 0.0 if span == 0 else (minute - m1) / span
                return y1 + t * (y2 - y1)

        return pts[-1][1]

    def _sample_count(self, base_mean: float) -> int:
        """Poisson(base_mean + jitter), clamped to non-negative."""
        if base_mean <= 0:
            return 0

        if self.jitter:
            base_mean = base_mean + random.uniform(-self.jitter, self.jitter)

        lam = max(0.0, base_mean)
        if lam == 0:
            return 0

        # numpy handles the Poisson sampling for us
        return int(np.random.poisson(lam))

    # ---- thread loop ----
    def run(self):
        while not self.clock.should_stop():
            minute = self.clock.now()

            mean_rate = self._mean_at(minute)
            n_new = self._sample_count(mean_rate)
            v = self.park.create_visitor(vtype, self.ids)
            if not v:
                break  

            for _ in range(n_new):
                vtype = random.choices(self.vtypes, weights=self.vweights, k=1)[0]
                v = self.park.create_visitor(vtype, self.ids)
                v.start()

                if self.metrics:
                    try:
                        self.metrics.record_arrival(v.vid, vtype, minute)
                    except Exception:
                        # keep the simulation running even if metrics fail
                        pass

            # one simulated minute
            self.clock.sleep_minutes(1)
