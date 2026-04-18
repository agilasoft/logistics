# Copyright (c) 2026, Agilasoft and contributors
"""Aggregated data for the Air Freight operations desk page (map, airlines, alerts)."""

from __future__ import unicode_literals

import frappe

from logistics.operations_dashboard.heat_map_core import (
	operations_filter_users,
	run_heat_map_dashboard,
	session_company_context,
)

AIR_SHIPMENT_JOB_STATUSES = (
	"Draft",
	"Submitted",
	"In Progress",
	"Completed",
	"Closed",
	"Reopened",
	"Cancelled",
)


def _airline_label(code):
	row = frappe.db.get_value("Airline", code, ["airline_name"], as_dict=True) or {}
	return "{0} ({1})".format(row.get("airline_name") or code, code)


@frappe.whitelist()
def get_air_freight_operations_filter_users(job_status_filter=None, include_draft=None):
	if job_status_filter is None and frappe.utils.cint(include_draft):
		job_status_filter = "open"
	comp = (session_company_context().get("company") or "").strip()
	return operations_filter_users(
		"Air Shipment",
		job_status_filter,
		"job_status",
		AIR_SHIPMENT_JOB_STATUSES,
		comp,
	)


@frappe.whitelist()
def get_air_freight_operations_dashboard(
	limit=None,
	filter_user=None,
	traffic=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
):
	return run_heat_map_dashboard(
		"Air Shipment",
		"Air Shipment",
		job_status_field="job_status",
		valid_job_statuses=AIR_SHIPMENT_JOB_STATUSES,
		origin_field="origin_port",
		dest_field="destination_port",
		carrier_field="airline",
		carrier_doctype="Airline",
		carrier_label_fn=_airline_label,
		job_status_filter=job_status_filter,
		filter_user=filter_user,
		traffic=traffic,
		carriers_param=airlines,
		limit=limit,
		include_draft=include_draft,
	)
