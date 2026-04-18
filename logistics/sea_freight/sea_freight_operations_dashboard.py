# Copyright (c) 2026, Agilasoft and contributors
"""Aggregated data for the Sea Freight operations desk / workspace (map, shipping lines, alerts)."""

from __future__ import unicode_literals

import frappe

from logistics.operations_dashboard.heat_map_core import (
	operations_filter_users,
	run_heat_map_dashboard,
	session_company_context,
)

SEA_SHIPMENT_JOB_STATUSES = (
	"Draft",
	"Submitted",
	"In Progress",
	"Completed",
	"Closed",
	"Reopened",
	"Cancelled",
)


def _shipping_line_label(code):
	row = frappe.db.get_value("Shipping Line", code, ["shipping_line_name"], as_dict=True) or {}
	return "{0} ({1})".format(row.get("shipping_line_name") or code, code)


@frappe.whitelist()
def get_sea_freight_operations_filter_users(job_status_filter=None, include_draft=None):
	if job_status_filter is None and frappe.utils.cint(include_draft):
		job_status_filter = "open"
	comp = (session_company_context().get("company") or "").strip()
	return operations_filter_users(
		"Sea Shipment",
		job_status_filter,
		"job_status",
		SEA_SHIPMENT_JOB_STATUSES,
		comp,
	)


@frappe.whitelist()
def get_sea_freight_operations_dashboard(
	limit=None,
	filter_user=None,
	traffic=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
):
	"""Param `airlines` re-used as JSON list of Shipping Line names (same client contract as air)."""
	return run_heat_map_dashboard(
		"Sea Shipment",
		"Sea Shipment",
		job_status_field="job_status",
		valid_job_statuses=SEA_SHIPMENT_JOB_STATUSES,
		origin_field="origin_port",
		dest_field="destination_port",
		carrier_field="shipping_line",
		carrier_doctype="Shipping Line",
		carrier_label_fn=_shipping_line_label,
		job_status_filter=job_status_filter,
		filter_user=filter_user,
		traffic=traffic,
		carriers_param=airlines,
		limit=limit,
		include_draft=include_draft,
	)
