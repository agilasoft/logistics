# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Copy Lead organization fields onto Prospect when ERPNext leaves them blank."""

from __future__ import unicode_literals

import frappe


def populate_annual_revenue_from_leads(doc, method=None):
	"""Fill Prospect annual revenue from a newly linked Lead when it is still empty.

	ERPNext copies annual revenue only in the server path used while creating an
	Opportunity. Create Prospect (form and list) builds the Prospect in the
	browser and omits the field. This covers that save, and Add to Prospect
	when the Prospect has no revenue yet. A later save does not refill a value
	the user cleared.
	"""
	if doc.get("annual_revenue"):
		return

	lead_names = []
	for row in doc.get("leads") or []:
		if not row.get("lead"):
			continue
		if doc.is_new() or row.get("__islocal"):
			lead_names.append(row.lead)

	if not lead_names:
		return

	revenue = frappe.db.get_value(
		"Lead",
		{"name": ["in", lead_names], "annual_revenue": [">", 0]},
		"annual_revenue",
		order_by="modified desc",
	)
	if revenue:
		doc.annual_revenue = revenue
