from source.core import Clock, pick_weighted, Status

clock = Clock(speed_factor=0.2, open_minutes=10)
print("Starting test...")
clock.sleep_minutes(5)
print("Current minute:", clock.now())

items = ["A", "B", "C"]
weights = [0.6, 0.3, 0.1]
print("Weighted pick:", pick_weighted(items, weights))

print("Status example:", Status.OPEN)