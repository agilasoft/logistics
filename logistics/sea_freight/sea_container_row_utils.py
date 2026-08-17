# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shared field mapping for sea container child rows across Sales Quote, Booking, and Shipment."""

from frappe.utils import flt

# Commercial / identity fields copied from Sales Quote Containers to Sea Booking Containers.
SALES_QUOTE_TO_BOOKING_CONTAINER_FIELDS = (
	"type",
	"size",
	"mode",
	"delivery_modes",
	"free_time_days",
	"demurrage_free_time_days",
	"detention_free_time_days",
)

# Fields copied from Sea Booking Containers to Sea Freight Containers on convert.
BOOKING_TO_SHIPMENT_CONTAINER_FIELDS = (
	"container_no",
	"seal_no",
	"type",
	"mode",
	"delivery_modes",
	"sealed_by",
	"other_references",
	"size",
	"packages_in_container",
	"weight_in_container",
	"volume_in_container",
	"max_weight",
	"max_volume",
	"utilization_percentage",
	"free_time_days",
	"demurrage_free_time_days",
	"detention_free_time_days",
)


def container_row_to_dict(source_row, field_names):
	"""Build a child-row dict from ``source_row`` for ``append('containers', ...)``."""
	out = {}
	for fn in field_names:
		val = getattr(source_row, fn, None)
		if val is not None and val != "":
			out[fn] = val
	return out


def copy_sales_quote_containers_to_booking(sales_quote, sea_booking):
	"""Copy Sales Quote container rows (including free time) onto a Sea Booking."""
	rows = getattr(sales_quote, "containers", None) or []
	if not rows:
		return
	for row in rows:
		data = container_row_to_dict(row, SALES_QUOTE_TO_BOOKING_CONTAINER_FIELDS)
		if data:
			sea_booking.append("containers", data)


def copy_booking_containers_to_shipment(sea_booking, sea_shipment):
	"""Copy Sea Booking container rows (including free time) onto a Sea Shipment."""
	rows = getattr(sea_booking, "containers", None) or []
	if not rows:
		return
	for row in rows:
		data = container_row_to_dict(row, BOOKING_TO_SHIPMENT_CONTAINER_FIELDS)
		if data:
			sea_shipment.append("containers", data)


def effective_row_free_time_days(row):
	"""Return non-zero free time from a container child row, or None."""
	ft = flt(getattr(row, "free_time_days", 0) or 0)
	return ft if ft else None
