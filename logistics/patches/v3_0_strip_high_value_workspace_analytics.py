# Copyright (c) 2026, Agilasoft and contributors
"""Drop HV workspace number cards/charts; keep report shortcuts and cards."""

from __future__ import annotations

from logistics.patches.v3_0_sync_high_value_reports_workspace import execute as sync_reports_workspace

NUMBER_CARDS = (
	"HV Brands",
	"Active HV Quotes",
	"Live HV Jobs",
	"HV SLA Breached",
)
CHARTS = (
	"HV Quotes Trend",
	"HV Quotes by Brand",
	"HV Air SLA Mix",
	"HV SLA Aging Mix",
)


def execute():
	import frappe

	frappe.flags.in_patch = True
	sync_reports_workspace()
	_delete_docs("Number Card", NUMBER_CARDS)
	_delete_docs("Dashboard Chart", CHARTS)
	frappe.clear_cache()


def _delete_docs(doctype, names):
	import frappe

	for name in names:
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
