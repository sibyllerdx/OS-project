# source/park/visitor_factory.py
from __future__ import annotations
from abc import ABC, abstractmethod
from source.visitors.base import Visitor, Child, Tourist, AdrenalineAddict

class VisitorCreator(ABC):
    """Abstract Creator: defines the factory method interface."""

    @abstractmethod
    def factory_method(self, vid, park, clock, metrics) -> Visitor:
        """Return a concrete Visitor instance."""
        pass

    def register_visitor(self, vid, park, clock, metrics) -> Visitor:
        """
        Common logic shared by all creators — could be logging, counting, etc.
        Each concrete factory calls factory_method() to create the correct visitor.
        """
        visitor = self.factory_method(vid, park, clock, metrics)
        # Optional: log creation or keep stats
        print(f"Factory created visitor: {visitor.profile['kind']}")
        return visitor

class ChildCreator(VisitorCreator):
    def factory_method(self, vid, park, clock, metrics) -> Visitor:
        return Child(vid, park=park, clock=clock, metrics=metrics)

class TouristCreator(VisitorCreator):
    def factory_method(self, vid, park, clock, metrics) -> Visitor:
        return Tourist(vid, park=park, clock=clock, metrics=metrics)

class AdrenalineAddictCreator(VisitorCreator):
    def factory_method(self, vid, park, clock, metrics) -> Visitor:
        return AdrenalineAddict(vid, park=park, clock=clock, metrics=metrics)
