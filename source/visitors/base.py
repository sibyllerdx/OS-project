# source/visitors/base.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from park.strategies import RandomStrategy, PreferenceStrategy, PopularityWaitTradeoff
import threading
import random

class Visitor(threading.Thread):
    def __init__(self, vid, park, clock, metrics):
        super().__init__(daemon=True)
        self.vid = vid
        self.park = park
        self.clock = clock
        self.metrics = metrics
        
        # Profile
        self.profile = {
            "kind": "Generic",
            "id": vid,
        }
        
        # Default preferences and behavior
        self.ride_prefs = {}
        self.strategy = RandomStrategy()  # default; subclasses can override
        self.time_budget = random.randint(180, 480)  # 3-8 hours in simulated minutes
        self.arrival_time = None  # Will be set when visitor starts
        self.departure_time = None  # Will be calculated from arrival_time + time_budget
        self.patience = random.randint(15, 45)  # minutes willing to wait
        self.has_fastpass = random.random() < 0.2  # 20% chance of having fastpass
        
        # Hunger mechanics
        self.hunger_level = 0  # 0-100 scale
        self.hunger_rate = 1.0  # how fast hunger increases per minute
        self.hunger_threshold = 40  # when to seek food (lowered for testing)
        self.is_eating = False
        self.food_preferences = []  # list of preferred food facilities
        
        # State tracking
        self._current_ride = None
        self._ride_event = threading.Event()

    def choose_and_queue(self):
        ride = self.strategy.pick_ride(self, self.park)
        if ride:
            self.park.join_ride_queue(self, ride)
        else:
            # fallback: rest/eat/wander
            self.clock.sleep_minutes(random.randint(1, 5))

    def on_ride_finished(self, ride_name, sim_minute):
        """Called by the ride when this visitor's cycle completes."""
        self._current_ride = None
        self._ride_event.set()

    def on_food_served(self, facility_name, sim_minute):
        """Called by food facility when order is complete."""
        self.hunger_level = 0  # Reset hunger
        self.is_eating = False

    def update_hunger(self):
        """Increase hunger over time."""
        if not self.is_eating:
            self.hunger_level = min(100, self.hunger_level + self.hunger_rate)

    def should_eat(self) -> bool:
        """Determine if visitor should seek food."""
        return self.hunger_level >= self.hunger_threshold and not self.is_eating

    def seek_food(self):
        """Try to join a food facility queue."""
        facilities = self.park.get_food_facilities()
        if not facilities:
            return False

        # Prefer certain facilities if specified
        if self.food_preferences:
            preferred = [f for f in facilities if f.name in self.food_preferences]
            if preferred:
                facilities = preferred

        # Pick randomly from available facilities
        facility = random.choice(facilities)
        self.is_eating = True
        success = self.park.join_food_queue(self, facility)
        if not success:
            self.is_eating = False
        return success

    def run(self):
        # Set arrival and planned departure time
        self.arrival_time = self.clock.now()
        self.departure_time = self.arrival_time + self.time_budget
        
        last_hunger_update = self.clock.now()
        while not self.clock.should_stop():
            current_time = self.clock.now()
            
            # Check if it's time to leave
            if current_time >= self.departure_time:
                break
            
            # Update hunger based on time elapsed
            minutes_elapsed = current_time - last_hunger_update
            if minutes_elapsed > 0 and not self.is_eating:
                self.hunger_level = min(100, self.hunger_level + (self.hunger_rate * minutes_elapsed))
                last_hunger_update = current_time

            # Decide action: eat or ride
            if self.should_eat():
                self.seek_food()
                # Rest while eating/waiting for food
                self.clock.sleep_minutes(random.randint(2, 5))
            else:
                # Go on rides
                self.choose_and_queue()
                self.clock.sleep_minutes(random.randint(1, 3))
        
        # Exit park
        if self.metrics:
            try:
                self.metrics.record_exit(self.vid, self.clock.now(), reason="time_up")
            except Exception:
                pass

class Child(Visitor):
    def __init__(self, vid, park, clock, metrics):
        super().__init__(vid, park, clock, metrics)
        self.profile["kind"] = "Child"
        self.ride_prefs = {"Carousel": 1.6, "ThunderCoaster": 0.8, "SkyDrop": 0.5, "HauntedMansion": 0.7}
        self.strategy = PreferenceStrategy()
        self.patience = random.randint(10, 25)  # Kids are less patient
        
        # Children stay for shorter periods (2-4 hours)
        self.time_budget = random.randint(120, 240)  # 2-4 hours max
        
        # Children get hungrier faster and prefer ice cream
        self.hunger_rate = 1.5  # Very hungry kids!
        self.hunger_threshold = 30  # Get hungry sooner
        self.food_preferences = ["IceCreamStand"]  # Kids love ice cream!

class Tourist(Visitor):
    def __init__(self, vid, park, clock, metrics):
        super().__init__(vid, park, clock, metrics)
        self.profile["kind"] = "Tourist"
        self.ride_prefs = {"Carousel": 1.0, "ThunderCoaster": 1.0, "SkyDrop": 1.0, "HauntedMansion": 1.0}
        self.strategy = RandomStrategy()
        
        # Tourists stay moderate to long periods (4-7 hours)
        self.time_budget = random.randint(240, 420)  # 4-7 hours
        
        # Tourists have moderate hunger and like full meals
        self.hunger_rate = 1.0
        self.hunger_threshold = 65
        self.food_preferences = ["BurgerTruck"]  # Prefer substantial meals

class AdrenalineAddict(Visitor):
    def __init__(self, vid, park, clock, metrics):
        super().__init__(vid, park, clock, metrics)
        self.profile["kind"] = "AdrenalineAddict"
        self.ride_prefs = {"Carousel": 0.4, "ThunderCoaster": 1.8, "SkyDrop": 1.6, "HauntedMansion": 0.8}
        self.strategy = PopularityWaitTradeoff(wait_penalty_after=8)
        self.has_fastpass = random.random() < 0.4  # Higher chance of fastpass (40%)
        
        # Adrenaline addicts stay until park closing (8-10 hours, essentially until close)
        self.time_budget = random.randint(480, 600)  # 8-10 hours (stays until closing)
        
        # Adrenaline junkies ignore hunger longer, quick snacks only
        self.hunger_rate = 0.3  # Get hungry slower (focused on rides)
        self.hunger_threshold = 75  # Only eat when very hungry
        self.food_preferences = ["IceCreamStand"]  # Quick snacks, back to rides!
