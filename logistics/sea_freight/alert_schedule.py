# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Scheduler paths and settings gates for sea delay and penalty checks."""

from __future__ import unicode_literals

HOURLY_SEA_ALERT_TASKS = (
	"logistics.sea_freight.tasks.check_sea_shipment_delays",
	"logistics.sea_freight.tasks.check_sea_shipment_penalties",
	"logistics.sea_freight.tasks.check_container_penalties",
)

DAILY_SEA_ALERT_TASKS = (
	"logistics.sea_freight.tasks.check_impending_penalties",
)


def alerts_enabled(settings, fieldname):
	"""True unless the settings row explicitly turns the flag off.

	A missing settings row leaves the check on. That matches the previous
	``getattr(..., 1)`` default used by the sea alert tasks.
	"""
	if settings is None:
		return True
	if isinstance(settings, dict):
		value = settings.get(fieldname, 1)
	else:
		value = getattr(settings, fieldname, 1)
	if value is None:
		return True
	return bool(value)


def log_check_completed(logger, title, message):
	"""Record a normal finish. Callers keep Error Log for failures."""
	logger.info("%s: %s", title, message)
