# source/facilities/ride.py
import threading
from typing import List
from source.core import Clock
from source.facilities.queues import RideQueue
from source.facilities.ride_states import OpenState, BoardingState, BrokenState, MaintenanceState, RideState

class Ride(threading.Thread):
    def __init__(self, name: str, capacity: int, run_duration: int, board_window: int,
                 queue: RideQueue, clock: Clock, metrics=None, popularity: float = 0.5):
        super().__init__(daemon=True)
        self.name = name
        self.capacity = capacity
        self.run_duration = run_duration          # sim minutes the cycle takes
        self.board_window = max(1, board_window)  # how long we stay in BOARDING if empty
        self.queue = queue
        self.clock = clock
        self.metrics = metrics
        self.popularity = popularity

        # Instantiate states
        self.open = OpenState()
        self.boarding = BoardingState()

        # Current state (Context pattern)
        self._state: RideState = self.open
        self._bind(self._state)

        # external control lock
        self._lock = threading.Lock()

    # ---- Context <-> State plumbing ----
    def _bind(self, state: RideState):
        state.ride = self
        # allow states to run enter hook
        try: state.on_enter()
        except AttributeError: pass

    def transition_to(self, state: RideState):
        # exit old state
        try: self._state.on_exit()
        except Exception: pass
        # enter new state
        self._state = state
        self._bind(state)
        # optional: emit status metric/event
        # if self.metrics: self.metrics._write({"event":"ride_state","ride_name":self.name,"reason":state.name(),"sim_minute":self.clock.now()})

    @property
    def status(self) -> str:
        return self._state.name()

    def can_enqueue(self) -> bool:
        return self._state.can_enqueue()

    # ---- Ride thread loop ----
    def run(self):
        while not self.clock.should_stop():
            # Let the state do one minute worth of work
            self._state.tick()
            # advance sim time by 1 minute
            self.clock.sleep_minutes(1)

    # ---- Operations used by states ----
    def _run_cycle(self, batch: List):
        """Simulate one ride cycle for the boarded batch; notify visitors; record metrics."""
        # record boarding
        if self.metrics:
            try:
                self.metrics.record_board(self.name, len(batch), self.clock.now(), ride_popularity=self.popularity)
            except Exception:
                pass

        # “Run” the ride
        self.clock.sleep_minutes(self.run_duration)

        # signal riders that the cycle finished (you’ll have a per-visitor event in your Visitor)
        for item in batch:
            try:
                # item.obj is your Visitor; call its “on_ride_done” or set an Event on it
                item.obj.on_ride_finished(self.name, self.clock.now())
            except Exception:
                pass

    # ---- External triggers for maintenance/failures ----
    def break_for(self, repair_minutes: int):
        """Called by maintenance: ride is broken until repaired."""
        with self._lock:
            self.transition_to(BrokenState(repair_minutes))

    def take_down_for_maintenance(self, minutes: int):
        with self._lock:
            self.transition_to(MaintenanceState(minutes))
