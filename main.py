#!/usr/bin/env python3
"""
Main entry point for the amusement park simulation.
Loads configuration, initializes all components, and runs the simulation.
"""

import sys
import os
# Add source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source'))

import yaml
from core import Clock
from park.arrival import ArrivalGenerator
from park.park import Park
from park.maintenance import MaintenanceDaemon
from facilities.ride import Ride
from facilities.queues import RideQueue, ServiceQueue
from facilities.food import BurgerTruck, IceCreamStand
from metrics_recorder import MetricsRecorder
import inspect
from facilities import ride_instances


class IdGenerator:
    """Simple ID generator for visitors."""
    def __init__(self):
        self._visitor_id = 0
    
    def visitor(self) -> int:
        self._visitor_id += 1
        return self._visitor_id


def build_park_from_config(cfg: dict, clock: Clock, metrics: MetricsRecorder) -> Park:
    """Build the Park object with all rides from configuration."""
    park = Park(clock, metrics)
    
    # Instantiate all rides defined in source/facilities/ride_instances.py
    # (ignore YAML `rides` entries; all rides will come from the ride_instances module)
    park.rides = []
    fastpass_enabled = cfg.get("policy", {}).get("fastpass", False)
    queue_capacity = 100

    for name, obj in inspect.getmembers(ride_instances, inspect.isclass):
        try:
            if issubclass(obj, Ride) and obj is not Ride:
                queue = RideQueue(
                    support_priority=fastpass_enabled,
                    max_regular=queue_capacity,
                    max_priority=queue_capacity // 2 if fastpass_enabled else None
                )
                # ride_instances classes expect (queue, clock, metrics=None)
                ride = obj(queue, clock, metrics)
                park.rides.append(ride)
        except Exception:
            # skip anything that isn't compatible with the expected constructor
            continue
    
    # Create food facilities
    food_cfg = cfg.get("food", [])
    park.food_facilities = []
    
    for f_cfg in food_cfg:
        name = f_cfg["name"]
        service_time = tuple(f_cfg["service_time"])
        capacity = f_cfg["capacity"]
        
        # Create queue for food facility
        food_queue = ServiceQueue(max_size=capacity * 2)
        
        # Create appropriate food facility
        if "Burger" in name:
            facility = BurgerTruck(name, service_time, capacity, food_queue, clock, metrics)
        else:
            facility = IceCreamStand(name, service_time, capacity, food_queue, clock, metrics)
        
        park.food_facilities.append(facility)
    
    return park


def main():
    """Main simulation entry point."""
    print("🎢 Starting Amusement Park Simulation...")
    
    # Load configuration
    with open("Config/park.yaml") as f:
        cfg = yaml.safe_load(f)
    
    # Initialize core components
    clock = Clock(cfg["time"]["speed_factor"], cfg["time"]["open_minutes"])
    ids = IdGenerator()
    metrics = MetricsRecorder()
    
    # Build park from config
    park = build_park_from_config(cfg, clock, metrics)
    
    # Create maintenance daemon
    maint_cfg = cfg.get("maintenance", {})
    maintenance = MaintenanceDaemon(
        rides=park.rides,
        clock=clock,
        mean_uptime=maint_cfg.get("mean_uptime", 120),
        mean_repair=maint_cfg.get("mean_repair", 10)
    )
    
    # Create arrival generator
    a_cfg = cfg["arrival"]
    arrival = ArrivalGenerator(
        clock=clock,
        park=park,
        ids=ids,
        metrics=metrics,
        total_visitors=a_cfg["total_visitors"],
        curve_points=a_cfg["curve_points"],
        visitor_mix=a_cfg["visitor_types"],
    )
    
    # Collect all threads
    all_threads = [
        arrival,
        maintenance,
        *park.rides,
        *park.food_facilities,
    ]
    
    print(f"📊 Park setup complete:")
    print(f"  - {len(park.rides)} rides")
    print(f"  - {len(park.food_facilities)} food facilities")
    print(f"  - Speed factor: {cfg['time']['speed_factor']} (1 sim min = {clock.seconds_per_minute():.2f} real sec)")
    print(f"  - Operating hours: {cfg['time']['open_minutes']} simulated minutes")
    print("\n🚀 Starting simulation threads...\n")
    
    # Start all threads
    for t in all_threads:
        t.start()
    
    # Run simulation until closing time
    try:
        clock.run_until_close()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    # Signal shutdown
    print("\n🛑 Closing park...")
    clock.stop()
    
    # Wait for all threads to finish
    for t in all_threads:
        t.join(timeout=5.0)
    
    # Close metrics and generate visualization
    metrics.close()

    print("\n" + "="*60)
    print("Generating wait time visualization...")
    # Pass the list of active ride names so the graph ignores old/removed rides
    try:
        active_ride_names = [r.name for r in park.rides]
    except Exception:
        active_ride_names = None
    metrics.generate_wait_time_graph(include_rides=active_ride_names)
    print("="*60)
    print("✅ Simulation complete!")
    print(f"📈 Metrics saved to: {metrics._path}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
