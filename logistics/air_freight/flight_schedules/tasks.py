"""Compat shim. See ``goconnect.flight.tasks``.

These cron entry points are now registered by ``goconnect/hooks.py``; the
re-exports below keep any direct ``frappe.call`` / ``bench execute`` paths
in ``logistics`` working without touching individual call sites.
"""

from goconnect.flight.tasks import *  # noqa: F401,F403
from goconnect.flight.tasks import (  # noqa: F401
	cleanup_old_schedules,
	cleanup_old_sync_logs,
	sync_active_flights,
	sync_airline_master,
	sync_airport_master,
	sync_route_data,
	update_air_freight_jobs_with_flight_status,
)
