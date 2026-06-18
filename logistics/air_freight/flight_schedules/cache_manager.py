"""Compat shim. See ``goconnect.flight.cache_manager``."""

from goconnect.flight.cache_manager import *  # noqa: F401,F403
from goconnect.flight.cache_manager import (  # noqa: F401
	FlightCacheManager,
	clear_all_cache,
	get_cache_statistics,
)
