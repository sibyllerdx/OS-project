from source.park.visitor_factory import ChildCreator, TouristCreator, AdrenalineAddictCreator

class Park:
    def __init__(self, clock, metrics):
        self.clock = clock
        self.metrics = metrics
        self.visitors = []
        self._creators = {
            "Child": ChildCreator(),
            "Tourist": TouristCreator(),
            "AdrenalineAddict": AdrenalineAddictCreator()
        }

    def create_visitor(self, vtype: str, ids):
        """Factory method wrapper inside Park."""
        vid = ids.visitor()
        creator = self._creators.get(vtype)
        if not creator:
            print(f"⚠ Unknown visitor type: {vtype}")
            return None

        visitor = creator.register_visitor(vid, self, self.clock, self.metrics)
        self.visitors.append(visitor)
        return visitor
    
    def open_rides(self):
        # return Ride objects whose state allows enqueue
        return [r for r in self.rides if r.can_enqueue()]

    def estimated_wait_minutes(self, ride_name: str) -> int:
        # quick heuristic: queue_length / (capacity per cycle) * run_duration
        r = next((x for x in self.rides if x.name == ride_name), None)
        if not r: return 0
        q_len = r.queue.size()
        cap   = max(1, r.capacity)
        cycles = (q_len + cap - 1) // cap
        return cycles * max(1, r.run_duration)

    def join_ride_queue(self, visitor, ride):
        now = self.clock.now()
        ok = ride.queue.enqueue(visitor, now_minute=now, priority=getattr(visitor, "has_fastpass", False))
        if not ok:
            # queue full; visitor could try a different ride or eat
            pass
