# source/visitors/base.py (snippets)
from source.park.strategies import RandomStrategy, PreferenceStrategy, PopularityWaitTradeoff
import threading

class Visitor(threading.Thread):
    def __init__(self, vid, park, clock, metrics):
        ...
        self.strategy = RandomStrategy()  # default; subclasses can override

    def choose_and_queue(self):
        ride = self.strategy.pick_ride(self, self.park)
        if ride:
            self.park.join_ride_queue(self, ride)  # implement this in Park
        else:
            # fallback: rest/eat/wander
            pass

    def run(self):
        while not self.clock.should_stop() and self.time_budget > 0:
            self.choose_and_queue()
            self.clock.sleep_minutes(1)
            self.time_budget -= 1

class Child(Visitor):
    def __init__(self, vid, park, clock, metrics):
        super().__init__(vid, park, clock, metrics)
        self.profile["kind"] = "Child"
        self.ride_prefs = {"Carousel": 1.6, "ThunderCoaster": 0.8, "SkyDrop": 0.5, "HauntedMansion": 0.7}
        self.strategy = PreferenceStrategy()

class Tourist(Visitor):
    def __init__(self, vid, park, clock, metrics):
        super().__init__(vid, park, clock, metrics)
        self.profile["kind"] = "Tourist"
        self.ride_prefs = {"Carousel": 1.0, "ThunderCoaster": 1.0, "SkyDrop": 1.0, "HauntedMansion": 1.0}
        self.strategy = RandomStrategy()

class AdrenalineAddict(Visitor):
    def __init__(self, vid, park, clock, metrics):
        super().__init__(vid, park, clock, metrics)
        self.profile["kind"] = "AdrenalineAddict"
        self.ride_prefs = {"Carousel": 0.4, "ThunderCoaster": 1.8, "SkyDrop": 1.6, "HauntedMansion": 0.8}
        self.strategy = PopularityWaitTradeoff(wait_penalty_after=8)
