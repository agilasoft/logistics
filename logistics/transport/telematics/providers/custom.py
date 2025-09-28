from __future__ import annotations
from typing import Any, Dict, Iterable
from datetime import datetime
from .base import TelematicsProvider, Position, Event, Temperature, CanSnapshot

class CustomProvider(TelematicsProvider):
    """Use this for in-house or uncommon providers."""
    def __init__(self, conf: Dict[str, Any]):
        self.conf = conf

    def fetch_latest_positions(self, since): return []
    def fetch_events(self, since, until): return []
    def fetch_temperatures(self, since, until): return []
    def fetch_can(self, since, until): return []
