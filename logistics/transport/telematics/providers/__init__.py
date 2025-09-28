from typing import Dict, Any
from .base import TelematicsProvider
from .remora import RemoraProvider
from .traccar import TraccarProvider
from .wialon import WialonProvider
from .geotab import GeotabProvider
from .samsara import SamsaraProvider
from .custom import CustomProvider

def make_provider(provider_type: str, conf: Dict[str, Any]) -> TelematicsProvider:
    t = (provider_type or "").upper()
    if t == "REMORA":  return RemoraProvider(conf)
    if t == "TRACCAR": return TraccarProvider(conf)
    if t == "WIALON":  return WialonProvider(conf)
    if t == "GEOTAB":  return GeotabProvider(conf)
    if t == "SAMSARA": return SamsaraProvider(conf)
    if t == "CUSTOM":  return CustomProvider(conf)
    raise ValueError(f"Unknown telematics provider: {provider_type}")
