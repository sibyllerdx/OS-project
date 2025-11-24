# source/park/arrival.py
import threading, random, math


def _poisson(lmbda: float) -> int:
    """Knuth Poisson sampler, number of arrival per minute."""
    if lmbda <= 0:
        return 0
    L = math.exp(-lmbda)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

class ArrivalGenerator(threading.Thread):
    """
    Spawns visitor threads minute-by-minute following a skewed arrival curve.
    Expects:
      - clock:      core.Clock
      - park:       object with create_visitor(vtype, ids) -> Visitor
      - ids:        id generator (e.g., core.Ids)
      - metrics:    metrics recorder (can be None)
      - curve_pts:  list of dicts: {'minute': int, 'mean': float}
      - visitor_mix: dict: {'Child': 0.3, 'Tourist': 0.5, ...}
      - jitter:     optional float; added noise in arrivals/minute
    """
    def __init__(self, clock, park, ids, metrics, curve_pts, visitor_mix, jitter: float = 0.0):
        super().__init__(daemon=True)
        self.clock = clock
        self.park = park
        self.ids = ids
        self.metrics = metrics
        # sanitize + sort points
        self.points = sorted(
            [{'minute': int(p['minute']), 'mean': float(p['mean'])} for p in curve_pts],
            key=lambda p: p['minute']
        )
        # normalize visitor mix to probabilities
        #Stores the names in vtypes and their relative weights in vweights.
        total = sum(visitor_mix.values())
        self.vtypes = list(visitor_mix.keys())
        self.vweights = [v / total for v in visitor_mix.values()]
        self.jitter = float(jitter or 0.0)

    # -------- curve evaluation --------
    def _mean_at(self, minute: int) -> float:
        """Linear interpolation between control points; clamp at ends."""
        pts = self.points
        if minute <= pts[0]['minute']:
            return pts[0]['mean']
        if minute >= pts[-1]['minute']:
            return pts[-1]['mean']
        
        # find segment
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            #Finds the two points surrounding the current minute.
            if a['minute'] <= minute <= b['minute']:
                span = b['minute'] - a['minute']
                t = 0.0 if span == 0 else (minute - a['minute']) / span
                return a['mean'] + t * (b['mean'] - a['mean'])
            #estimate the expected mean arrival rate between them.
        return pts[-1]['mean']  # fallback

    def _sample_count(self, base_mean: float) -> int:
        """Poisson(base_mean + jitter) with non-negative clamp."""
        # small symmetric noise
        noisy = max(0.0, base_mean + (random.uniform(-self.jitter, self.jitter) if self.jitter else 0.0))
        return _poisson(noisy)

    # -------- thread loop --------
    def run(self):
        while not self.clock.should_stop():
            minute = self.clock.now()
            mean_rate = self._mean_at(minute) #Computes the expected arrival rate for that minute.
            n_new = self._sample_count(mean_rate)
            for _ in range(n_new):
                vtype = random.choices(self.vtypes, weights=self.vweights, k=1)[0]
                v = self.park.create_visitor(vtype, self.ids)  # your Park should return a started-but-not-running visitor
                v.start()
                if self.metrics:
                    try:
                        self.metrics.record_arrival(v.vid, vtype, minute)
                    except Exception:
                        pass

            # advance one simulated minute
            self.clock.sleep_minutes(1)
