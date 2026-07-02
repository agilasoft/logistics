# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from logistics.pricing_center.utils.opportunity_dashboard import (
	build_opportunity_dashboard_payload,
	render_opportunity_dashboard_html,
)
from logistics.pricing_center.utils.opportunity_scopes import populate_virtual_scope_actuals


def _build_dashboard_doc(
	opportunity: str | None = None,
	company: str | None = None,
	customer: str | None = None,
	scopes: str | list | None = None,
):
	if opportunity:
		doc = frappe.get_doc("Opportunity", opportunity)
		populate_virtual_scope_actuals(doc)
		return doc

	if scopes:
		scope_rows = json.loads(scopes) if isinstance(scopes, str) else scopes
		doc = frappe._dict(
			{
				"company": company,
				"opportunity_from": "Customer" if customer else None,
				"party_name": customer,
				"currency": None,
				"custom_opportunity_scopes": [],
			}
		)
		for row in scope_rows or []:
			child = frappe._dict(row)
			child.parenttype = "Opportunity"
			doc.custom_opportunity_scopes.append(child)
		return doc

	frappe.throw(_("Opportunity or scopes are required"))


@frappe.whitelist()
def get_opportunity_dashboard(
	opportunity: str | None = None,
	company: str | None = None,
	customer: str | None = None,
	scopes: str | None = None,
):
	"""Dashboard payload: annual opportunity value vs YTD revenue/profit."""
	doc = _build_dashboard_doc(opportunity=opportunity, company=company, customer=customer, scopes=scopes)
	return build_opportunity_dashboard_payload(doc)


@frappe.whitelist()
def get_opportunity_dashboard_html(
	opportunity: str | None = None,
	company: str | None = None,
	customer: str | None = None,
	scopes: str | None = None,
	metric: str | None = None,
):
	"""Rendered HTML for the Opportunity value attainment dashboard."""
	doc = _build_dashboard_doc(opportunity=opportunity, company=company, customer=customer, scopes=scopes)
	payload = build_opportunity_dashboard_payload(doc)
	return render_opportunity_dashboard_html(payload, metric=metric)
