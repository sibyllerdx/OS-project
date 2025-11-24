import csv
import os
import threading
from datetime import datetime

class MetricsRecorder:
    """
    Thread-safe CSV logger for simulation events.
    Call record_* methods from any thread (arrival, ride, visitor, staff).
    """

    def __init__(self, out_dir: str = "results", filename: str = "metrics.csv"):
        self.out_dir = out_dir
        self.filename = filename
        self._path = os.path.join(out_dir, filename)
        os.makedirs(out_dir, exist_ok=True)

        # Create file with header if new/empty
        self._lock = threading.Lock()
        new_file = not os.path.exists(self._path) or os.path.getsize(self._path) == 0
        self._fh = open(self._path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=[
            "wall_time",
            "sim_minute",
            "event",
            # common fields
            "visitor_id",
            "visitor_type",
            "ride_name",
            "count",
            "ride_popularity",
            "reason",
        ])
        if new_file:
            self._writer.writeheader()
            self._fh.flush()

    # ---------- low-level write ----------
    def _write(self, row: dict):
        row.setdefault("wall_time", datetime.utcnow().isoformat(timespec="seconds"))
        with self._lock:
            self._writer.writerow(row)
            self._fh.flush()

    # ---------- arrivals ----------
    def record_arrival(self, visitor_id: int, visitor_type: str, sim_minute: int):
        self._write({
            "sim_minute": sim_minute,
            "event": "arrival",
            "visitor_id": visitor_id,
            "visitor_type": visitor_type,
        })

    # ---------- ride-related ----------
    def record_board(self, ride_name: str, count: int, sim_minute: int, ride_popularity=None):
        self._write({
            "sim_minute": sim_minute,
            "event": "ride_board",
            "ride_name": ride_name,
            "count": count,
            "ride_popularity": ride_popularity,
        })

    def record_abandon(self, visitor_id: int, ride_name: str, waited_minutes: int, sim_minute: int):
        self._write({
            "sim_minute": sim_minute,
            "event": "queue_abandon",
            "visitor_id": visitor_id,
            "ride_name": ride_name,
            "reason": f"waited={waited_minutes}",
        })

    def record_exit(self, visitor_id: int, sim_minute: int, reason: str = "done"):
        self._write({
            "sim_minute": sim_minute,
            "event": "exit",
            "visitor_id": visitor_id,
            "reason": reason,
        })

    # ---------- food/service ----------
    def record_order(self, visitor_id: int, stall_name: str, sim_minute: int):
        self._write({
            "sim_minute": sim_minute,
            "event": "order",
            "visitor_id": visitor_id,
            "ride_name": stall_name,  # reuse column for place name
        })

    def record_served(self, visitor_id: int, stall_name: str, sim_minute: int):
        self._write({
            "sim_minute": sim_minute,
            "event": "served",
            "visitor_id": visitor_id,
            "ride_name": stall_name,
        })

    # ---------- cleanup ----------
    def close(self):
        with self._lock:
            try:
                self._fh.flush()
            finally:
                self._fh.close()
