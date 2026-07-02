# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt

from logistics.pricing_center.utils.opportunity_scopes import (
	populate_virtual_scope_actuals,
	populate_virtual_scope_actuals_for_rows,
)


@frappe.whitelist()
def get_opportunity_scope_actuals(
	opportunity: str | None = None,
	company: str | None = None,
	customer: str | None = None,
	scopes: str | None = None,
):
	"""Return virtual YTD actual revenue/profit for scopes without saving."""
	if opportunity:
		doc = frappe.get_doc("Opportunity", opportunity)
		return populate_virtual_scope_actuals(doc)

	if scopes:
		scope_rows = json.loads(scopes) if isinstance(scopes, str) else scopes
		if not company:
			frappe.throw(_("Company is required when scopes are passed from the form"))
		party = (customer or "").strip() or None
		computed = populate_virtual_scope_actuals_for_rows(scope_rows, company, party)
		total_revenue = sum(flt(row["actual_revenue"]) for row in computed)
		total_profit = sum(flt(row["actual_profit"]) for row in computed)
		total_value = sum(flt(row.get("opportunity_value")) for row in scope_rows)
		return {
			"custom_total_scope_opportunity_value": total_value,
			"custom_total_scope_actual_revenue": total_revenue,
			"custom_total_scope_actual_profit": total_profit,
			"scopes": computed,
		}

	frappe.throw(_("Opportunity or scopes are required"))
