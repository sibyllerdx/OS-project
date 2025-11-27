# source/park/arrival.py
import threading
import random
import numpy as np


class ArrivalGenerator(threading.Thread):
    """
    Generates visitors minute by minute using a distribution curve.

    - total_visitors: exact number of visitors to generate
    - curve_points: list of {'minute': int, 'mean': float} defining distribution shape
    - visitor_mix:  dict like {'Child': 0.2, 'Tourist': 0.6, ...}
    """
    def __init__(self, clock, park, ids, metrics, total_visitors: int, curve_points, visitor_mix):
        super().__init__(daemon=True)
        self.clock = clock
        self.park = park
        self.ids = ids
        self.metrics = metrics
        self.total_visitors = int(total_visitors)

        # Store (minute, mean) pairs sorted by minute
        self.points = sorted(
            [(int(p["minute"]), float(p["mean"])) for p in curve_points],
            key=lambda x: x[0]
        )

        # Normalize visitor mix
        total = sum(visitor_mix.values())
        self.vtypes = list(visitor_mix.keys())
        self.vweights = [v / total for v in visitor_mix.values()]

        # Create all visitors upfront and assign arrival times
        self.visitors = self._create_all_visitors()
        print(f"📋 Created {len(self.visitors)} visitors with scheduled arrival times")

    # ---- visitor creation ----
    def _create_all_visitors(self):
        """
        Create all visitor objects upfront and assign arrival times based on distribution.
        Returns list of (minute, visitor) tuples sorted by arrival time.
        """
        # Calculate visitor type counts
        type_counts = {}
        for vtype, weight in zip(self.vtypes, self.vweights):
            count = int(round(self.total_visitors * weight))
            type_counts[vtype] = count
        
        # Adjust for rounding errors
        total_assigned = sum(type_counts.values())
        if total_assigned < self.total_visitors:
            # Add remaining to most common type
            most_common = max(type_counts, key=type_counts.get)
            type_counts[most_common] += self.total_visitors - total_assigned
        elif total_assigned > self.total_visitors:
            # Remove excess from most common type
            most_common = max(type_counts, key=type_counts.get)
            type_counts[most_common] -= total_assigned - self.total_visitors
        
        # Create visitors with retries to ensure we get exactly the count we need
        all_visitors = []
        for vtype, count in type_counts.items():
            created = 0
            attempts = 0
            max_attempts = count * 3  # Allow retries
            
            while created < count and attempts < max_attempts:
                visitor = self.park.create_visitor(vtype, self.ids)
                if visitor:
                    all_visitors.append(visitor)
                    created += 1
                attempts += 1
            
            if created < count:
                print(f"  Warning: Only created {created}/{count} {vtype} visitors")
        
        print(f"  Type distribution requested: {type_counts}")
        print(f"  Successfully created: {len(all_visitors)} visitors")
        
        # Assign arrival times based on distribution curve
        arrival_times = self._generate_arrival_times(len(all_visitors))
        
        # Pair visitors with arrival times and sort
        visitors_with_times = list(zip(arrival_times, all_visitors))
        visitors_with_times.sort(key=lambda x: x[0])
        
        return visitors_with_times
    
    def _generate_arrival_times(self, count):
        """Generate arrival times following the distribution curve."""
        # Get the last minute from curve points
        max_minute = self.points[-1][0] if self.points else 600
        
        # Calculate relative probability for each minute
        minute_weights = []
        for minute in range(max_minute + 1):
            weight = self._mean_at(minute)
            minute_weights.append(max(0.0, weight))
        
        # Normalize to probabilities
        total_weight = sum(minute_weights)
        if total_weight == 0:
            # Fallback: uniform distribution
            minute_weights = [1.0] * len(minute_weights)
            total_weight = len(minute_weights)
        
        minute_probs = [w / total_weight for w in minute_weights]
        
        # Assign arrival times
        minutes = list(range(len(minute_probs)))
        arrival_times = np.random.choice(
            minutes,
            size=count,
            p=minute_probs,
            replace=True
        )
        
        return list(arrival_times)

    # ---- curve evaluation ----
    def _mean_at(self, minute: int) -> float:
        """Linear interpolation between control points; clamp at ends."""
        pts = self.points

        if minute <= pts[0][0]:
            return pts[0][1]
        if minute >= pts[-1][0]:
            return pts[-1][1]

        for (m1, y1), (m2, y2) in zip(pts, pts[1:]):
            if m1 <= minute <= m2:
                span = m2 - m1
                t = 0.0 if span == 0 else (minute - m1) / span
                return y1 + t * (y2 - y1)

        return pts[-1][1]

    # ---- thread loop ----
    def run(self):
        visitor_index = 0
        started_count = 0
        recorded_count = 0
        
        while visitor_index < len(self.visitors):
            minute = self.clock.now()
            
            # Start all visitors scheduled for this minute or earlier
            while visitor_index < len(self.visitors):
                arrival_minute, visitor = self.visitors[visitor_index]
                
                if arrival_minute > minute:
                    # No more visitors for this minute
                    break
                
                # Start this visitor
                visitor.start()
                started_count += 1
                
                # Record arrival
                if self.metrics:
                    try:
                        vtype = type(visitor).__name__
                        self.metrics.record_arrival(visitor.vid, vtype, minute)
                        recorded_count += 1
                    except Exception as e:
                        print(f"⚠️ Error recording arrival for visitor {visitor.vid}: {e}")
                
                visitor_index += 1
            
            # Check if we're done
            if visitor_index >= len(self.visitors):
                print(f"✅ All {len(self.visitors)} visitors have entered the park by minute {minute}")
                print(f"   Started: {started_count} visitor threads")
                print(f"   Recorded: {recorded_count} arrivals")
                break
            
            # Check if simulation is ending
            if self.clock.should_stop():
                print(f"⚠️ Clock stopped but {len(self.visitors) - visitor_index} visitors still pending")
                break
            
            # one simulated minute
            self.clock.sleep_minutes(1)
