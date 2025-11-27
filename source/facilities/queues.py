# source/facilities/queues.py
from __future__ import annotations
import threading
from collections import deque #ton add and remove elements on both sides 
from dataclasses import dataclass
from typing import Deque, Iterable, List, Optional


class QueueItem:
    def __init__(self, obj, enq_minute, priority):
        self.obj = obj                      #visitor instance
        self.enq_minute = enq_minute        #minutes of when they joined the queue
        self.priority = priority            #Fast pass or regular, true means fast pass 

class RideQueue:
    """
    Thread-safe queue for rides with optional priority lane and fair batch boarding.

    Fairness rule:
      - When boarding a batch, take 1 from priority if available,
        then fill remaining seats from regular,
        then any remaining seats from priority.
    """

    def __init__(
        self,
        support_priority: bool = False,
        max_regular: Optional[int] = None,
        max_priority: Optional[int] = None,
    ):
        self.support_priority = support_priority #If it has fast pass 
        self._lock = threading.Lock() #protects all queues 
        self._not_empty = threading.Condition(self._lock) #wait until so enqueues and notifies rides 

        self._reg: Deque[QueueItem] = deque() #create the empty queue
        self._pri: Deque[QueueItem] = deque()

        #Set the capacity limits 
        self._max_regular = max_regular
        self._max_priority = max_priority

    # ----------------------- Query helpers -----------------------

    #acquire lock to read the length 
    def size(self) -> int:
        with self._lock:
            return len(self._reg) + len(self._pri)

    def len_regular(self) -> int:
        with self._lock:
            return len(self._reg)

    def len_priority(self) -> int:
        with self._lock:
            return len(self._pri)

    # ----------------------- Core operations -----------------------

    def enqueue(self, obj, now_minute: int, priority: bool = False) -> bool:
        """
        Try to put obj in the queue.
        Returns True if queued, False if rejected due to capacity.
        """
        item = QueueItem(obj=obj, enq_minute=now_minute, priority=priority) #creates the item to be enqueued 

        with self._lock:
            if priority and self.support_priority:
                if self._max_priority is not None and len(self._pri) >= self._max_priority: #check capaicty and enqueue
                    return False
                self._pri.append(item)
            else:
                if self._max_regular is not None and len(self._reg) >= self._max_regular:
                    return False
                self._reg.append(item) #enqueue to regular 

            self._not_empty.notify() #wake a ride thread that is waiting for arrival

            # record metrics (commented out - metrics handled at ride level)
            # if self.metrics:
            #     try:
            #         self.metrics._write({
            #             "sim_minute": now_minute,
            #             "event": "queue_join",
            #             "visitor_id": getattr(obj, "vid", None),
            #             "ride_name": self.name,
            #             "reason": "priority" if priority else "regular",
            #         })
            #     except Exception:
            #         pass

            return True #if teh item was enqueued 

    def remove(self, obj, now_minute=None):
        """
        Remove the first matching obj from either lane.
        Returns True if something was removed.
        O(n) but queues are typically not huge.
        """
        with self._lock:
            for i, it in enumerate(self._reg):
                if it.obj is obj:
                    self._rotate_remove(self._reg, i)
                    removed = True
                    break
            else:
                for i, it in enumerate(self._pri):
                    if it.obj is obj:
                        self._rotate_remove(self._pri, i)
                        removed = True
                        break
                else:
                    removed = False

        # Metrics handled at ride level
        # if removed and self.metrics and now_minute is not None:
        #     try:
        #         self.metrics.record_abandon(
        #             visitor_id=getattr(obj, "vid", None),
        #             ride_name=self.name,
        #             waited_minutes=0,
        #             sim_minute=now_minute,
        #         )
        #     except Exception:
        #         pass
        return removed

    def _rotate_remove(self, dq: Deque[QueueItem], index: int) -> None:
        
        dq.rotate(-index)       #bring the target to the left 
        dq.popleft()            #pop it 
        dq.rotate(index)        #restore the original order

    # ----------------------- Ride boarding -----------------------

    def wait_until_not_empty(self, clock, timeout_minutes: Optional[int] = None) -> bool:
        """
        Block (scaled by simulated time) until there is at least one item or timeout.
        Every simulated minute, the thread wakes up, re-acquires the lock, and checks if someone arrived
        Returns True if queue is non-empty; False if timed out.
        """
        with self._lock:
            if self._reg or self._pri:
                return True
            if timeout_minutes is None:
                # Wake once per simulated minute so we can react to stop signals.
                while not (self._reg or self._pri):
                    self._not_empty.wait(timeout=clock.seconds_per_minute())
                    # caller should also check clock.should_stop()
                return True
            else:
                # Convert sim minutes to real seconds via seconds_per_minute
                remaining = timeout_minutes
                while remaining > 0 and not (self._reg or self._pri):
                    wait_s = min(1, remaining) * clock.seconds_per_minute()
                    self._not_empty.wait(timeout=wait_s)
                    remaining -= 1
                return bool(self._reg or self._pri)

    def get_batch_for_boarding(self, capacity: int) -> List[QueueItem]:
        """
        Pop up to `capacity` items for the next ride cycle using fairness rule.
        Non-blocking; returns empty list if nothing to board.
        """
        if capacity <= 0:
            return []

        with self._lock:
            taken: List[QueueItem] = []

            # 1) Take 1 from priority if available
            if self.support_priority and self._pri:
                taken.append(self._pri.popleft())

            # 2) Fill remainder from regular lane
            while len(taken) < capacity and self._reg:
                taken.append(self._reg.popleft())

            # 3) If seats remain, take more from priority
            while len(taken) < capacity and self._pri:
                taken.append(self._pri.popleft())

            return taken


class ServiceQueue:
    """
    Thread-safe single-lane queue for restaurants/food stands.
    FIFO only.

    Staff thread calls:    item = q.get_next(block=True, clock=clock)
    Visitor joins via:     q.enqueue(visitor, now_minute)
    Visitor can abandon:   q.remove(visitor)
    """

    def __init__(self, max_size: Optional[int] = None):
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._q: Deque[QueueItem] = deque()
        self._max_size = max_size

    # ---------- basic info ----------
    def size(self) -> int:
        with self._lock:
            return len(self._q)

    # ---------- producers (visitors) ----------
    def enqueue(self, obj, now_minute: int) -> bool:
        """
        Add a visitor to the tail of the queue.
        Returns False if the queue is at max capacity.
        """
        item = QueueItem(obj=obj, enq_minute=now_minute, priority=False)
        with self._lock:
            if self._max_size is not None and len(self._q) >= self._max_size:
                return False
            self._q.append(item)
            self._not_empty.notify()   # wake any waiting staff thread
            return True

    def remove(self, obj) -> bool:
        """
        Remove the first occurrence of `obj` (visitor) from the queue.
        Returns True if removed (e.g., impatience/abandon).
        """
        with self._lock:
            for i, it in enumerate(self._q):
                if it.obj is obj:                  # identity match
                    self._rotate_remove(i)
                    return True
            return False

    def _rotate_remove(self, index: int) -> None:
        self._q.rotate(-index)
        self._q.popleft()
        self._q.rotate(index)

    # ---------- consumers (staff) ----------
    def get_next(self, block: bool, clock, timeout_minutes: Optional[int] = None) -> Optional[QueueItem]:
        """
        Pop the next customer (FIFO).
        - block=False: non-blocking; return None if empty.
        - block=True: wait until someone arrives or until timeout (in simulated minutes).
        """
        with self._lock:
            # non-blocking path
            if not block:
                if self._q:
                    return self._q.popleft()
                return None

            # blocking path
            if not self._q:
                if timeout_minutes is None:
                    # wait indefinitely, waking once per simulated minute
                    while not self._q:
                        self._not_empty.wait(timeout=clock.seconds_per_minute())
                else:
                    remaining = timeout_minutes
                    while remaining > 0 and not self._q:
                        self._not_empty.wait(timeout=clock.seconds_per_minute())
                        remaining -= 1

            if self._q:
                return self._q.popleft()
            return None