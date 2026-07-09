# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Read-only virtual ``linked_services`` grid for operational booking parents."""

from __future__ import annotations

from typing import Any

import frappe

LINKED_SERVICE_VIEW_FIELDS = (
	"linked_service",
	"service_type",
	"job_type",
	"job_no",
	"job_description",
	"air_house_type",
	"airline",
	"freight_agent",
	"sea_house_type",
	"freight_agent_sea",
	"shipping_line",
	"transport_mode",
	"load_type",
	"direction",
	"origin_port",
	"destination_port",
	"transport_template",
	"vehicle_type",
	"container_type",
	"container_no",
	"location_type",
	"location_from",
	"location_to",
	"pick_mode",
	"drop_mode",
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
	"planned_cost",
	"actual_cost",
	"planned_revenue",
	"actual_revenue",
)


def build_linked_services_view_for_booking(
	parent_booking_type: str, parent_booking_name: str
) -> list[dict[str, Any]]:
	"""Build desk grid rows from ``Linked Service`` documents parented to a booking."""
	if not parent_booking_type or not parent_booking_name:
		return []
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)

	rows: list[dict[str, Any]] = []
	for ls in get_linked_services_for_booking(parent_booking_type, parent_booking_name):
		row: dict[str, Any] = {"linked_service": ls.name}
		for fn in LINKED_SERVICE_VIEW_FIELDS:
			if fn == "linked_service":
				continue
			if hasattr(ls, fn):
				row[fn] = getattr(ls, fn, None)
		rows.append(row)
	return rows


class VirtualLinkedServicesMixin:
	"""Mixin for operational parents with a read-only virtual ``linked_services`` table."""

	def __setup__(self):
		self._drop_virtual_linked_services_rows()

	def before_save(self):
		"""Ignore empty desk payloads for the read-only virtual ``linked_services`` grid."""
		if getattr(self, "name", None) and not getattr(self, "__islocal", False):
			self._drop_virtual_linked_services_rows()

	@property
	def linked_services(self):
		"""Live view of ``Linked Service`` documents parented to this booking."""
		if self.flags.get("_linked_services_view_cached"):
			cached = self.__dict__.get("linked_services")
			if cached:
				return cached
			# Desk save may replace the grid with ``[]`` while the cache flag stays set.
			if getattr(self, "name", None) and not getattr(self, "__islocal", False):
				value = self._build_linked_services_view()
				self.__dict__["linked_services"] = value
				self.flags._linked_services_view_cached = True
				return value
			return []
		value = self._build_linked_services_view()
		self.__dict__["linked_services"] = value
		self.flags._linked_services_view_cached = True
		return value

	def _build_linked_services_view(self):
		if not getattr(self, "name", None) or getattr(self, "__islocal", False):
			return []
		return build_linked_services_view_for_booking(self.doctype, self.name)

	def _drop_virtual_linked_services_rows(self):
		self.flags._linked_services_view_cached = False
		if "linked_services" in self.__dict__:
			del self.__dict__["linked_services"]
