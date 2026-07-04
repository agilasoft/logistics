# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill planned/actual cost and revenue on Special Project Service rows."""

from __future__ import annotations

import frappe

from logistics.special_projects.lifecycle_job_financial_rollup import sync_lifecycle_job_financials
from logistics.special_projects.special_project_service_helpers import (
	tag_untagged_charges_to_planning_services,
)


def execute():
	if not frappe.db.exists("DocType", "Special Project"):
		return

	names = frappe.db.sql(
		"""
		SELECT DISTINCT sp.name
		FROM `tabSpecial Project` sp
		INNER JOIN `tabSpecial Project Charges` ch ON ch.parent = sp.name
		WHERE sp.docstatus < 2
		  AND IFNULL(ch.estimated_cost, 0) + IFNULL(ch.estimated_revenue, 0) > 0
		""",
		pluck="name",
	)
	for name in names:
		_sync_one(name)


def _sync_one(name: str) -> None:
	try:
		sp = frappe.get_doc("Special Project", name)
	except Exception:
		return
	if not sp.get("charges"):
		return
	tag_untagged_charges_to_planning_services(sp)
	sync_lifecycle_job_financials(sp)
	sp.save(ignore_permissions=True)
