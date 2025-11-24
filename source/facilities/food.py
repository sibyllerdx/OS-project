from source.facilities.food import Restaurant, FoodTruck
from source.metrics_recorder import MetricsRecorder
# from source.facilities.queues import FoodQueue  # or any FIFO with dequeue()/size()

metrics = MetricsRecorder()
burger_q = SomeFoodQueueImpl()
clock = ParkClock(...)

burger = Restaurant(
    name="BurgerTruck",
    service_time_range=(3, 6),
    capacity=4,
    order_queue=burger_q,
    clock=clock,
    metrics=metrics,
)
burger.start()
