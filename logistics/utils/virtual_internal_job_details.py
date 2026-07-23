# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Operational parents whose linked legs are ``Linked Service`` documents (no desk grid)."""

from __future__ import annotations

# Operational parents that own Linked Service documents instead of a persisted Internal Jobs table.
VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS = frozenset(
	{
		"Sea Booking",
		"Sea Shipment",
		"Air Booking",
		"Air Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration",
		"Declaration Order",
		"Warehouse Job",
		"Inbound Order",
		"Release Order",
		"Cross-Docking Order",
		"General Job",
		"Project Job",
		"MICE Job",
		"Exhibit Job",
	}
)


def uses_virtual_internal_job_details(parent_doctype: str | None) -> bool:
	return (parent_doctype or "") in VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS
