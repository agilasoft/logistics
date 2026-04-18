# Copyright (c) 2026, Agilasoft and contributors
"""Aggregated data for the Customs operations desk / workspace (map, declaration alerts)."""

from __future__ import unicode_literals

import frappe

from logistics.operations_dashboard.heat_map_core import (
	operations_filter_users,
	run_heat_map_dashboard,
	session_company_context,
)

DECLARATION_JOB_STATUSES = (
	"Draft",
	"Submitted",
	"In Progress",
	"Completed",
	"Closed",
	"Reopened",
	"Cancelled",
)


@frappe.whitelist()
def get_customs_operations_filter_users(job_status_filter=None, include_draft=None):
	if job_status_filter is None and frappe.utils.cint(include_draft):
		job_status_filter = "open"
	comp = (session_company_context().get("company") or "").strip()
	return operations_filter_users(
		"Declaration",
		job_status_filter,
		"job_status",
		DECLARATION_JOB_STATUSES,
		comp,
	)


@frappe.whitelist()
def get_customs_operations_dashboard(
	limit=None,
	filter_user=None,
	traffic=None,
	job_status_filter=None,
	include_draft=None,
):
	return run_heat_map_dashboard(
		"Declaration",
		"Declaration",
		job_status_field="job_status",
		valid_job_statuses=DECLARATION_JOB_STATUSES,
		origin_field="port_of_loading",
		dest_field="port_of_discharge",
		carrier_field=None,
		carrier_doctype=None,
		carrier_label_fn=None,
		job_status_filter=job_status_filter,
		filter_user=filter_user,
		traffic=traffic,
		carriers_param=None,
		limit=limit,
		include_draft=include_draft,
	)
