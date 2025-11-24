# source/main.py (snippet)
import yaml
from source.core import Clock, Ids
from source.park.arrival import ArrivalGenerator

def main():
    with open("Config/park.yaml") as f:
        cfg = yaml.safe_load(f)

    clock = Clock(cfg["time"]["speed_factor"], cfg["time"]["open_minutes"])
    ids = Ids()

    # ... build Park, Rides, Queues, Metrics, etc. (not shown)
    park = build_park_from_cfg(cfg, clock)      # your function
    metrics = build_metrics()

    a_cfg = cfg["arrival"]
    arrival = ArrivalGenerator(
        clock=clock,
        park=park,
        ids=ids,
        metrics=metrics,
        curve_pts=a_cfg["curve_points"],
        visitor_mix=a_cfg["visitor_types"],
        jitter=a_cfg.get("jitter", 0.0),
    )

    # start all threads
    for t in [arrival, *park.threads(), metrics]:
        t.start()

    clock.run_until_close()
    clock.stop()
    for t in [arrival, *park.threads(), metrics]:
        t.join()

if __name__ == "__main__":
    main()
