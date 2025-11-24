# source/facilities/ride_states.py

#USES STATE DESIGN PATTERN 

from __future__ import annotations
from abc import ABC, abstractmethod

class RideState(ABC):
    """Base interface for all ride states."""

    # The Ride context will set this when we transition_into(...)
    ride: "Ride" = None  # type: ignore

    # optional hooks
    def on_enter(self): ...
    def on_exit(self): ...

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def can_enqueue(self) -> bool:
        """Can visitors join the queue while in this state?"""
        ...

    @abstractmethod
    def tick(self):
        """
        Called by the Ride thread once per simulated minute.
        This is where the state performs its work and may transition.
        """
        ...


class OpenState(RideState):
    def name(self) -> str: return "OPEN"
    def can_enqueue(self) -> bool: return True

    def tick(self):
        # If there are people, consider starting a boarding window
        if self.ride.queue.size() > 0:
            # Move to Boarding to collect a batch
            self.ride.transition_to(self.ride.boarding)


class BoardingState(RideState):
    def name(self) -> str: return "BOARDING"
    def can_enqueue(self) -> bool: return True

    def on_enter(self):
        # (optional) you could mark the beginning of a boarding window
        self._minutes_in_window = 0

    def tick(self):
        # Give the queue a short window to fill seats
        self._minutes_in_window += 1
        # Pull a batch (fairness rule handled by the queue)
        batch = self.ride.queue.get_batch_for_boarding(self.ride.capacity)

        if batch:
            # Run the ride cycle (this sleeps run_duration sim minutes and notifies visitors)
            self.ride._run_cycle(batch)
            # After a cycle, go back OPEN (unless something else forces a change)
            self.ride.transition_to(self.ride.open)
        else:
            # No one to board; if window exceeds board_window, go back OPEN
            if self._minutes_in_window >= self.ride.board_window:
                self.ride.transition_to(self.ride.open)
            else:
                # stay in boarding a bit longer (maybe more people arrive)
                pass


class BrokenState(RideState):
    def __init__(self, repair_minutes: int = 0):
        self._remaining = max(0, repair_minutes)

    def name(self) -> str: return "BROKEN"
    def can_enqueue(self) -> bool: return False

    def on_enter(self):
        # if none provided externally, default to a small fix time
        if self._remaining == 0:
            self._remaining = 15

    def tick(self):
        # Count down; when repaired, reopen
        if self._remaining > 0:
            self._remaining -= 1
        if self._remaining <= 0:
            self.ride.transition_to(self.ride.open)


class MaintenanceState(RideState):
    def __init__(self, minutes: int):
        self._remaining = max(1, minutes)

    def name(self) -> str: return "MAINTENANCE"
    def can_enqueue(self) -> bool: return False

    def tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self.ride.transition_to(self.ride.open)
