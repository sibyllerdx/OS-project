import csv
import os
import threading
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from collections import defaultdict
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

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
            "sim_time",
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
    def _write(self, row: dict, sim_minute: int = None):
        if sim_minute is not None:
            # Convert sim_minute to time format (minute 0 = 10:00 AM)
            hours = 10 + (sim_minute // 60)
            minutes = sim_minute % 60
            # Handle PM times
            if hours >= 12:
                if hours > 12:
                    row["sim_time"] = f"{hours:02d}:{minutes:02d} PM"
                else:
                    row["sim_time"] = f"{hours:02d}:{minutes:02d} PM"
            else:
                row["sim_time"] = f"{hours:02d}:{minutes:02d} AM"
        with self._lock:
            self._writer.writerow(row)
            self._fh.flush()

    # ---------- arrivals ----------
    def record_arrival(self, visitor_id: int, visitor_type: str, sim_minute: int):
        self._write({
            "event": "arrival",
            "visitor_id": visitor_id,
            "visitor_type": visitor_type,
        }, sim_minute)

    # ---------- ride-related ----------
    def record_board(self, ride_name: str, count: int, sim_minute: int, ride_popularity=None):
        self._write({
            "event": "ride_board",
            "ride_name": ride_name,
            "count": count,
            "ride_popularity": ride_popularity,
        }, sim_minute)

    def record_abandon(self, visitor_id: int, ride_name: str, waited_minutes: int, sim_minute: int):
        self._write({
            "event": "queue_abandon",
            "visitor_id": visitor_id,
            "ride_name": ride_name,
            "reason": f"waited={waited_minutes}",
        }, sim_minute)

    def record_exit(self, visitor_id: int, sim_minute: int, reason: str = "done"):
        self._write({
            "event": "exit",
            "visitor_id": visitor_id,
            "reason": reason,
        }, sim_minute)

    # ---------- ride maintenance ----------
    def record_breakdown(self, ride_name: str, sim_minute: int, repair_duration: int):
        self._write({
            "event": "ride_breakdown",
            "ride_name": ride_name,
            "count": repair_duration,  # duration in minutes
        }, sim_minute)

    def record_repair(self, ride_name: str, sim_minute: int):
        self._write({
            "event": "ride_repaired",
            "ride_name": ride_name,
        }, sim_minute)

    # ---------- food/service ----------
    def record_order(self, visitor_id: int, stall_name: str, sim_minute: int):
        self._write({
            "event": "order",
            "visitor_id": visitor_id,
            "ride_name": stall_name,  # reuse column for place name
        }, sim_minute)

    def record_served(self, visitor_id: int, stall_name: str, sim_minute: int):
        self._write({
            "event": "served",
            "visitor_id": visitor_id,
            "ride_name": stall_name,
        }, sim_minute)

    # ---------- queue tracking ----------
    def record_queue_length(self, ride_name: str, queue_length: int, sim_minute: int):
        """Record current queue length for wait time analysis."""
        self._write({
            "event": "queue_length",
            "ride_name": ride_name,
            "count": queue_length,
        }, sim_minute)

    # ---------- cleanup ----------
    def close(self):
        with self._lock:
            try:
                self._fh.flush()
            finally:
                self._fh.close()

    # ---------- visualization ----------
    def generate_wait_time_graph(self):
        """Generate attraction wait time graph from metrics."""
        if not HAS_MATPLOTLIB:
            print("⚠️  matplotlib not available, skipping graph generation")
            return

        # Read queue length data from CSV
        queue_data = defaultdict(lambda: defaultdict(int))
        
        try:
            with open(self._path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['event'] == 'queue_length':
                        ride_name = row.get('ride_name', '')
                        sim_time = row.get('sim_time', '')
                        count = int(row.get('count', 0))
                        
                        if ride_name and sim_time:
                            # Convert HH:MM AM/PM to minutes since opening (10 AM = minute 0)
                            # Remove AM/PM suffix and parse time
                            time_str = sim_time.replace(' AM', '').replace(' PM', '')
                            time_parts = time_str.split(':')
                            hour = int(time_parts[0])
                            minute = int(time_parts[1])
                            
                            # Convert to minutes since 10 AM opening
                            if 'PM' in sim_time and hour != 12:
                                hour += 12
                            elif 'AM' in sim_time and hour == 12:
                                hour = 0
                            
                            total_minutes = (hour - 10) * 60 + minute
                            queue_data[ride_name][total_minutes] = count
        except Exception as e:
            print(f"⚠️  Error reading metrics for graph: {e}")
            return

        if not queue_data:
            print("⚠️  No queue data available for graphing")
            return

        # Create the plot
        plt.figure(figsize=(14, 6))
        plt.style.use('dark_background')
        
        # Plot each ride's wait time
        for ride_name, time_series in sorted(queue_data.items()):
            if time_series:
                times = sorted(time_series.keys())
                wait_times = [time_series[t] for t in times]
                plt.plot(times, wait_times, label=ride_name, linewidth=1.5, alpha=0.8)
        
        plt.xlabel('Time (minutes since opening)', fontsize=12)
        plt.ylabel('Queue Length (visitors)', fontsize=12)
        plt.title('Attraction Wait Time Throughout Day', fontsize=14, fontweight='bold')
        plt.legend(loc='upper right', fontsize=9)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save the graph
        graph_path = os.path.join(self.out_dir, 'wait_time_graph.png')
        plt.savefig(graph_path, dpi=150, facecolor='black')
        plt.close()
        
        print(f"📊 Wait time graph saved to: {graph_path}")
