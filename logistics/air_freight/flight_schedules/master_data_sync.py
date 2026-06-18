"""Compat shim. See ``goconnect.flight.master_data_sync``."""

from goconnect.flight.master_data_sync import *  # noqa: F401,F403
from goconnect.flight.master_data_sync import (  # noqa: F401
	get_airline_from_airline_master,
	get_unloco_from_airport_master,
	sync_airline_master_to_airline,
	sync_airport_master_to_unloco,
	sync_all_airline_masters_to_airline,
	sync_all_airport_masters_to_unloco,
	sync_all_locations_to_airport_master,
	sync_location_to_airport_master,
)
