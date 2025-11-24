from ride import Ride

class RollerCoaster(Ride):
    """Fast, thrilling ride with high popularity."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("RollerCoaster", 16, 5, 3, queue, clock, metrics, 0.9)

class DropTower(Ride):
    """Intense vertical free-fall experience."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("DropTower", 8, 3, 2, queue, clock, metrics, 0.8)

class FerrisWheel(Ride):
    """Calm panoramic ride for all ages."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("FerrisWheel", 20, 7, 4, queue, clock, metrics, 0.6)

class BumperCars(Ride):
    """Classic, great for groups."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("BumperCars", 12, 4, 2, queue, clock, metrics, 0.5)

class HauntedHouse(Ride):
    """Dark indoor maze filled with spooky effects."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("HauntedHouse", 10, 6, 3, queue, clock, metrics, 0.7)

class SplashMountain(Ride):
    """Water based splash adventure ride."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("SplashMountain", 12, 5, 3, queue, clock, metrics, 0.8)

class SpinningTeacups(Ride):
    """kids/family favorite."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("SpinningTeacups", 18, 4, 3, queue, clock, metrics, 0.65)

class PirateShip(Ride):
    """Pendulum swing ride"""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("PirateShip", 14, 5, 2, queue, clock, metrics, 0.7)


class SpaceSimulator(Ride):
    """High-tech spinning capsule simulating space flight."""
    def __init__(self, queue, clock, metrics=None):
        super().__init__("SpaceSimulator", 10, 6, 3, queue, clock, metrics, 0.85)
