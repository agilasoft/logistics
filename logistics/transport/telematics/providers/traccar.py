from __future__ import annotations
from typing import Any, Dict, Iterable
from datetime import datetime
import requests
from .base import TelematicsProvider, Position, Event, Temperature, CanSnapshot

def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

class TraccarProvider(TelematicsProvider):
    def __init__(self, conf: Dict[str, Any]):
        self.base = (conf.get("base_url") or "").rstrip("/")
        self.key = conf.get("api_key") or ""
        self.timeout = int(conf.get("timeout") or 20)

    def _get(self, path: str, params: Dict[str, Any]) -> Any:
        url = f"{self.base}{path}"
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        r = requests.get(url, params=params, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json() or {}

    def fetch_latest_positions(self, since):
        # Traccar: /api/positions (may require filtering)
        for it in self._get("/api/positions", {}):
            yield {
                "external_id": str(it.get("deviceId") or it.get("id")),
                "ts": _dt(it["deviceTime"] or it["serverTime"]),
                "lat": float(it["latitude"]),
                "lon": float(it["longitude"]),
                "speed_kph": float(it.get("speed", 0)) * 1.852,  # knots → kph if needed
                "ignition": it.get("attributes", {}).get("ignition"),
                "odometer_km": float(it.get("attributes", {}).get("odometer", 0))/1000.0,
                "raw": it,
            }

    def fetch_events(self, since, until):
        # Traccar: /api/reports/events?from=&to=&deviceId=
        return []
    def fetch_temperatures(self, since, until): return []
    def fetch_can(self, since, until): return []
