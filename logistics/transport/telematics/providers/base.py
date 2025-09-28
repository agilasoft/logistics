from typing import Any, Dict, Iterable, Optional, TypedDict
from datetime import datetime

class Position(TypedDict):
    external_id: str; ts: datetime; lat: float; lon: float
    speed_kph: Optional[float]; ignition: Optional[bool]
    odometer_km: Optional[float]; raw: Dict[str, Any]

class Event(TypedDict):
    external_id: str; ts: datetime; kind: str; meta: Dict[str, Any]

class Temperature(TypedDict):
    external_id: str; ts: datetime; sensor: str; temperature_c: float

class CanSnapshot(TypedDict):
    external_id: str; ts: datetime; fuel_l: Optional[float]; rpm: Optional[float]
    engine_hours: Optional[float]; coolant_c: Optional[float]
    ambient_c: Optional[float]; raw: Dict[str, Any]

class TelematicsProvider:
    def __init__(self, conf: Dict[str, Any]): ...
    def fetch_latest_positions(self, since: Optional[datetime]) -> Iterable[Position]: ...
    def fetch_events(self, since: datetime, until: datetime) -> Iterable[Event]: ...
    def fetch_temperatures(self, since: datetime, until: datetime) -> Iterable[Temperature]: ...
    def fetch_can(self, since: datetime, until: datetime) -> Iterable[CanSnapshot]: ...
