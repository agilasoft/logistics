# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""CRM Sales Quote integration: custom fields, client scripts, Pricing workspace reports."""

from __future__ import unicode_literals

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from logistics.pricing_center.utils.client_script_sync import sync_pricing_center_client_scripts

_SALES_QUOTE_REPORTS = [
	"Sales Quote Executive Control Snapshot",
	"Sales Quote Submission Health Ratio",
	"Sales Quote Status Funnel Mix",
	"Sales Quote Open Draft Aging Backlog",
	"Sales Quote Monthly Pipeline and Value",
	"Sales Quote Weekly Pipeline and Value",
	"Sales Quote Monthly Throughput Index",
	"Sales Quote Weekly Throughput Index",
	"Sales Quote Customer Win Concentration",
	"Sales Quote Sales Representative Concentration",
	"Sales Quote Operations Representative Concentration",
	"Sales Quote Owner Workload Review",
	"Sales Quote Branch Performance View",
	"Sales Quote Direction Trade Mix",
	"Sales Quote Incoterm Commercial Mix",
	"Sales Quote Transport Mode Offer Mix",
	"Sales Quote Main Service Mix",
	"Sales Quote Job Type Portfolio Mix",
	"Sales Quote Quotation Type Mix",
	"Sales Quote Overdue Validity Pressure",
]


def execute():
	if frappe.db.exists("DocType", "Sales Quote"):
		create_custom_fields(_sales_quote_crm_fields(), update=True)
	sync_pricing_center_client_scripts()
	_add_sales_quote_reports_to_pricing_workspace()
	frappe.clear_cache(doctype="Sales Quote")
	frappe.clear_cache(doctype="Opportunity")
	frappe.clear_cache(doctype="Lead")
	frappe.clear_cache(doctype="Customer")
	frappe.db.commit()


def _sales_quote_crm_fields():
	return {
		"Sales Quote": [
			{
				"fieldname": "crm_references_section",
				"fieldtype": "Section Break",
				"label": "CRM References",
				"insert_after": "additional_information_tab",
				"collapsible": 1,
			},
			{
				"fieldname": "opportunity",
				"fieldtype": "Link",
				"label": "Opportunity",
				"options": "Opportunity",
				"insert_after": "crm_references_section",
				"read_only": 1,
			},
			{
				"fieldname": "lead",
				"fieldtype": "Link",
				"label": "Lead",
				"options": "Lead",
				"insert_after": "opportunity",
				"read_only": 1,
			},
		]
	}


def _add_sales_quote_reports_to_pricing_workspace():
	if not frappe.db.exists("Workspace", "Pricing"):
		return

	ws = frappe.get_doc("Workspace", "Pricing")
	existing = {link.link_to for link in (ws.links or []) if link.link_to}
	reports_to_add = []
	for report_title in _SALES_QUOTE_REPORTS:
		if report_title in existing:
			continue
		if not frappe.db.exists("Report", report_title):
			continue
		reports_to_add.append(report_title)

	if not reports_to_add:
		return

	if not any(link.label == "Sales Quote analytics" for link in (ws.links or [])):
		ws.append(
			"links",
			{
				"label": "Sales Quote analytics",
				"link_count": len(reports_to_add),
				"link_type": "Report",
				"type": "Card Break",
			},
		)

	for report_title in reports_to_add:
		ws.append(
			"links",
			{
				"label": report_title,
				"link_to": report_title,
				"link_type": "Report",
				"type": "Link",
				"is_query_report": 1,
				"report_ref_doctype": "Sales Quote",
			},
		)

	content = json.loads(ws.content or "[]")
	has_sq_card = any(
		block.get("type") == "card" and block.get("data", {}).get("card_name") == "Sales Quote analytics"
		for block in content
	)
	if not has_sq_card:
		content.append(
			{
				"id": "sqAnalyticsHdr",
				"type": "header",
				"data": {"text": '<span class="h4"><b>Sales Quote analytics</b></span>', "col": 12},
			}
		)
		content.append(
			{"id": "sqAnalyticsCard", "type": "card", "data": {"card_name": "Sales Quote analytics", "col": 12}}
		)
		ws.content = json.dumps(content)

	ws.save(ignore_permissions=True)
