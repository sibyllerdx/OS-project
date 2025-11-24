# source/park/strategies.py
from __future__ import annotations
from abc import ABC, abstractmethod
import random
from typing import Optional, List

# We’ll call into these helpers; implement them in Park if you haven't yet.
# - park.open_rides() -> List[Ride]
# - park.estimated_wait_minutes(ride_name: str) -> int
# - visitor.ride_prefs: dict[str, float]  (preference weights per ride)

class RideChoiceStrategy(ABC):
    @abstractmethod
    def pick_ride(self, visitor, park) -> Optional["Ride"]:
        """Return the chosen Ride (or None if no choice)."""
        ...

# 1) Pure random among open rides
class RandomStrategy(RideChoiceStrategy):
    def pick_ride(self, visitor, park):
        rides = park.open_rides()
        return random.choice(rides) if rides else None

# 2) Preference-weighted (uses visitor.ride_prefs as weights)
class PreferenceStrategy(RideChoiceStrategy):
    def pick_ride(self, visitor, park):
        rides = park.open_rides()
        if not rides:
            return None
        items, weights = [], []
        for r in rides:
            w = visitor.ride_prefs.get(r.name, 1.0)
            if w > 0:
                items.append(r); weights.append(w)
        if not items:
            return None
        # lightweight weighted pick
        total = sum(weights)
        x = random.random() * total
        acc = 0.0
        for item, w in zip(items, weights):
            acc += w
            if x <= acc:
                return item
        return items[-1]

# 3) Tradeoff: preference * popularity, penalize long waits
class PopularityWaitTradeoff(RideChoiceStrategy):
    def __init__(self, wait_penalty_after: int = 10):
        self.wait_penalty_after = wait_penalty_after

    def pick_ride(self, visitor, park):
        rides = park.open_rides()
        best, best_score = None, -1e9
        for r in rides:
            pref = visitor.ride_prefs.get(r.name, 1.0)
            pop  = getattr(r, "popularity", 1.0)
            eta  = max(0, park.estimated_wait_minutes(r.name) or 0)
            # penalize waits longer than threshold
            penalty = 1.0 / (1.0 + max(0, eta - self.wait_penalty_after))
            score = pref * pop * penalty
            if score > best_score:
                best, best_score = r, score
        return best
