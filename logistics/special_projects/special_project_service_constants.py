# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared constants for Special Project service / lifecycle rows."""

from __future__ import annotations

PLANNING_ORDER_TYPES = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Project Order",
	}
)

LIFECYCLE_EXECUTION_JOB_TYPES = frozenset(
	{
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Declaration",
		"Warehouse Job",
		"Project Job",
	}
)

LIFECYCLE_JOB_TYPE_OPTIONS = PLANNING_ORDER_TYPES
