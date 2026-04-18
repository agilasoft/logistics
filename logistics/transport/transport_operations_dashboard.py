# Copyright (c) 2026, Agilasoft and contributors
"""Aggregated data for the Transport operations desk / workspace (map, transport company filter, alerts)."""

from __future__ import unicode_literals

import frappe

from logistics.operations_dashboard.heat_map_core import (
	operations_filter_users,
	run_heat_map_dashboard,
	session_company_context,
	transport_job_resolve_ports,
)

TRANSPORT_JOB_STATUSES = (
	"Draft",
	"Submitted",
	"In Progress",
	"Completed",
	"Closed",
	"Reopened",
	"Cancelled",
)


def _transport_company_label(code):
	name = frappe.db.get_value("Transport Company", code, "full_name") or code
	return "{0} ({1})".format(name, code)


@frappe.whitelist()
def get_transport_operations_filter_users(job_status_filter=None, include_draft=None):
	if job_status_filter is None and frappe.utils.cint(include_draft):
		job_status_filter = "open"
	comp = (session_company_context().get("company") or "").strip()
	return operations_filter_users(
		"Transport Job",
		job_status_filter,
		"status",
		TRANSPORT_JOB_STATUSES,
		comp,
	)


@frappe.whitelist()
def get_transport_operations_dashboard(
	limit=None,
	filter_user=None,
	traffic=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
):
	"""`airlines` param carries selected Transport Company names (client reuse)."""
	return run_heat_map_dashboard(
		"Transport Job",
		"Transport Job",
		job_status_field="status",
		valid_job_statuses=TRANSPORT_JOB_STATUSES,
		list_fields=[
			"name",
			"status",
			"modified",
			"sea_shipment",
			"air_shipment",
			"transport_company",
		],
		origin_field="origin_port",
		dest_field="destination_port",
		carrier_field="transport_company",
		carrier_doctype="Transport Company",
		carrier_label_fn=_transport_company_label,
		resolve_ports=transport_job_resolve_ports,
		job_status_filter=job_status_filter,
		filter_user=filter_user,
		traffic=traffic,
		carriers_param=airlines,
		limit=limit,
		include_draft=include_draft,
	)
