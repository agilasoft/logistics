# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from workflow_center.workflow_center.queries import (
	get_dashboard_items,
	get_dashboard_summary,
	get_user_roles,
)


def has_app_permission() -> bool:
	user = frappe.session.user
	return user == "Administrator" or bool(get_user_roles(user))


@frappe.whitelist()
def get_workflow_center_dashboard(filters=None, segment=None):
	"""Return KPI summary and item list for Workflow Center."""
	summary = get_dashboard_summary(filters=filters)
	items = get_dashboard_items(filters=filters)
	return {
		"summary": summary,
		"items": items,
	}


@frappe.whitelist()
def get_workflow_center_items(filters=None, segment=None):
	return get_dashboard_items(filters=filters, segment=segment)


@frappe.whitelist()
def get_workflow_center_summary(filters=None):
	return get_dashboard_summary(filters=filters)


@frappe.whitelist()
def get_workflow_center_filter_options():
	"""Return filter dropdown values for the desk page."""
	user = frappe.session.user
	roles = sorted(get_user_roles(user))
	companies = frappe.get_all("Company", pluck="name", order_by="name")
	branches = frappe.get_all("Branch", pluck="name", order_by="name") if frappe.db.table_exists("Branch") else []
	cost_centers = (
		frappe.get_all("Cost Center", pluck="name", order_by="name")
		if frappe.db.table_exists("Cost Center")
		else []
	)
	profit_centers = []
	if frappe.db.table_exists("Profit Center"):
		profit_centers = frappe.get_all("Profit Center", pluck="name", order_by="name")

	return {
		"roles": roles,
		"companies": companies,
		"branches": branches,
		"cost_centers": cost_centers,
		"profit_centers": profit_centers,
		"user": user,
		"full_name": frappe.get_value("User", user, "full_name") or user,
		"role_count": len(roles),
	}
