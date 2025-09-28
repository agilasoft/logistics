from __future__ import annotations
from typing import Any, Dict, Iterable
from datetime import datetime
from .base import TelematicsProvider, Position, Event, Temperature, CanSnapshot

class WialonProvider(TelematicsProvider):
    def __init__(self, conf: Dict[str, Any]):
        self.base = (conf.get("base_url") or "").rstrip("/")
        self.key = conf.get("api_key") or ""
        self.timeout = int(conf.get("timeout") or 20)

    def fetch_latest_positions(self, since):  # implement via Messages/Unit params
        return []
    def fetch_events(self, since, until): return []
    def fetch_temperatures(self, since, until): return []
    def fetch_can(self, since, until): return []
