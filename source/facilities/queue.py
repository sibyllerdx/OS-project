import threading

# General class to handle queues for the different extra features that we have (bathrooms, Bars,...)
# By using this class we are making sure that the critical areas are coded correctly and thus our future code will be easier.
class Queue:
    def __init__(self) -> None:
        # Two internal queues: priority (fast pass) and regular
        self.priority = []
        self.regular = []
        self.lock = threading.Lock()

    # person can be any object (id, dict, etc.)
    def add_person(self, person, fast_pass: bool = False):
        with self.lock:
            if fast_pass:
                self.priority.append(person)
            else:
                self.regular.append(person)

    def remove_person(self, person):
        with self.lock:
            if person in self.priority:
                self.priority.remove(person)
            elif person in self.regular:
                self.regular.remove(person)

    # ---- Metrics ----
    def total_length(self):
        with self.lock:
            return len(self.priority) + len(self.regular)

    def priority_length(self):
        with self.lock:
            return len(self.priority)

    def regular_length(self):
        with self.lock:
            return len(self.regular)

    def check_person_in(self, person):
        with self.lock:
            return person in self.priority or person in self.regular

    # ---- Batch for a ride ----
    def get_batch_for_ride(self, wagon_capacity: int):
        """
        Returns and removes up to `wagon_capacity` people from the queue.
        Always tries to take up to 5 people from the priority queue first,
        then fills the rest from the regular queue.
        """
        if wagon_capacity <= 0:
            return []

        with self.lock:
            batch = []

            # First: up to 5 from priority (or less if not enough / small capacity)
            num_from_priority = min(5, wagon_capacity, len(self.priority))
            for _ in range(num_from_priority):
                batch.append(self.priority.pop(0))

            remaining_slots = wagon_capacity - len(batch)

            # Then: fill remaining slots from regular
            num_from_regular = min(remaining_slots, len(self.regular))
            for _ in range(num_from_regular):
                batch.append(self.regular.pop(0))

            return batch
