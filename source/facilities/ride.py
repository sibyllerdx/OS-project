# source/facilities/ride.py
import threading
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from typing import List
from core import Clock
from facilities.queues import RideQueue
from facilities.ride_states import OpenState, BoardingState, BrokenState, MaintenanceState, RideState

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
        self._broken_until = 0
        self._repair_thread = None


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
        last_queue_report = 0
        queue_report_interval = 5  # Report queue length every 5 minutes
        
        while not self.clock.should_stop():
            # Periodically report queue length for wait time tracking
            current_minute = self.clock.now()
            if current_minute - last_queue_report >= queue_report_interval:
                queue_length = self.queue.size()
                if self.metrics:
                    try:
                        self.metrics.record_queue_length(self.name, queue_length, current_minute)
                    except Exception:
                        pass
                last_queue_report = current_minute
            
            # Let the state do one minute worth of work
            self._state.tick()
            # advance sim time by 1 minute
            self.clock.sleep_minutes(1)
        
        # Final queue length report at shutdown
        if self.metrics:
            try:
                self.metrics.record_queue_length(self.name, self.queue.size(), self.clock.now())
            except Exception:
                pass

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
    def is_broken(self) -> bool:
        """
        Returns True if the ride is currently not operational.
        We treat both BROKEN and MAINTENANCE as 'down'.
        """
        try:
            state_name = self._state.name()
        except Exception:
            # fallback if state not bound yet
            state_name = str(getattr(self._state, "__class__", type(self._state)).__name__)
        return state_name in ("BROKEN", "MAINTENANCE")

    def break_for(self, repair_minutes):
        now = self.clock.now()
        ext = max(1, int(repair_minutes))
        with self._lock:
            was_broken = self.is_broken()
            self._broken_until = max(self._broken_until, now + ext)
            if not was_broken:
                print(f"[minute {now}] {self.name} BREAKS for {ext} minutes")
                # Record breakdown event
                if self.metrics:
                    try:
                        self.metrics.record_breakdown(self.name, now, ext)
                    except Exception:
                        pass
                if self._repair_thread is None or not self._repair_thread.is_alive():
                    self._repair_thread = threading.Thread(target=self._repair_guardian, daemon=True)
                    self._repair_thread.start()
            # if already broken, we silently extend; no duplicate print

    def _repair_guardian(self):
        printed = False
        while not self.clock.should_stop():
            now = self.clock.now()
            with self._lock:
                if now >= self._broken_until:
                    if not printed:
                        print(f"[minute {now}] {self.name} REPAIRED")
                        # Record repair event
                        if self.metrics:
                            try:
                                self.metrics.record_repair(self.name, now)
                            except Exception:
                                pass
                        printed = True
                    break
            time.sleep(0.01)
