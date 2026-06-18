# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT Accounting & Finance Summary - portfolio view across A&F trackers + ERPNext."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	as_on = filters.get("as_on_date") or nowdate()

	bad_total = frappe.db.sql(
		"SELECT SUM(amount) FROM `tabBad Account Entry` WHERE status NOT IN ('Recovered','Written Off')"
	)
	bad_total = flt(bad_total[0][0]) if bad_total and bad_total[0] and bad_total[0][0] is not None else 0.0

	credit_exposure = frappe.db.sql(
		"SELECT SUM(exposure_amount), SUM(credit_limit) FROM `tabClient Credit Line`"
	)
	exposure = flt(credit_exposure[0][0]) if credit_exposure and credit_exposure[0] and credit_exposure[0][0] is not None else 0.0
	limit_total = flt(credit_exposure[0][1]) if credit_exposure and credit_exposure[0] and credit_exposure[0][1] is not None else 0.0

	investments = frappe.db.sql(
		"SELECT SUM(principal) FROM `tabInvestment Holding`"
	)
	investments_total = flt(investments[0][0]) if investments and investments[0] and investments[0][0] is not None else 0.0

	bank_recon = frappe.db.sql(
		"SELECT COUNT(*), SUM(amount) FROM `tabBank Reconciliation Discrepancy` WHERE status IN ('Open','Investigating')"
	)
	bank_recon_count = int(bank_recon[0][0]) if bank_recon and bank_recon[0] and bank_recon[0][0] is not None else 0
	bank_recon_amount = flt(bank_recon[0][1]) if bank_recon and bank_recon[0] and bank_recon[0][1] is not None else 0.0

	bonds = frappe.db.sql(
		"SELECT SUM(amount) FROM `tabSupplier Cash Bond` WHERE refund_status IN ('Outstanding','Partially Refunded')"
	)
	bonds_total = flt(bonds[0][0]) if bonds and bonds[0] and bonds[0][0] is not None else 0.0

	# Collections aging 60+ (Sales Invoice based)
	collections_60_plus = 0.0
	try:
		rs = frappe.db.sql(
			"""
			SELECT SUM(outstanding_amount)
			FROM `tabSales Invoice`
			WHERE docstatus = 1
			  AND outstanding_amount > 0
			  AND DATEDIFF(%s, posting_date) >= 60
			""",
			(as_on,),
		)
		collections_60_plus = flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
	except Exception:
		pass

	# Unbilled shipments proxy: Air Shipment + Sea Shipment with billing_status not Billed
	unbilled_count = 0
	try:
		for dt in ("Air Shipment", "Sea Shipment"):
			rs = frappe.db.sql(
				"""
				SELECT COUNT(*) FROM `tab{dt}`
				WHERE docstatus = 1
				  AND IFNULL(billing_status, '') NOT IN ('Billed','Fully Billed')
				""".format(dt=dt)
			)
			unbilled_count += int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
	except Exception:
		pass

	columns = [
		{"fieldname": "metric", "label": _("Metric"), "fieldtype": "Data", "width": 320},
		{"fieldname": "value", "label": _("Value (PHP)"), "fieldtype": "Currency", "width": 200},
	]
	rows = [
		{"metric": _("Collections 60+ days outstanding"), "value": collections_60_plus},
		{"metric": _("Bad Accounts (active)"), "value": bad_total},
		{"metric": _("Unbilled Shipments (count)"), "value": unbilled_count},
		{"metric": _("Credit Lines - Total Exposure"), "value": exposure},
		{"metric": _("Credit Lines - Total Limit"), "value": limit_total},
		{"metric": _("Investment Holdings (principal)"), "value": investments_total},
		{"metric": _("Bank Recon Discrepancies (open count)"), "value": bank_recon_count},
		{"metric": _("Bank Recon Discrepancies (amount)"), "value": bank_recon_amount},
		{"metric": _("Supplier Cash Bond (outstanding)"), "value": bonds_total},
	]
	chart = {
		"data": {
			"labels": [_("Collections 60+"), _("Bad Accounts"), _("Credit Exposure"), _("Bonds")],
			"datasets": [{"name": _("Amount"), "values": [collections_60_plus, bad_total, exposure, bonds_total]}],
		},
		"type": "bar",
		"title": _("A&F Headline Risks"),
	}
	report_summary = [
		{"label": _("Collections 60+"), "value": collections_60_plus, "datatype": "Currency", "currency": "PHP", "indicator": "Red"},
		{"label": _("Bad Accounts"), "value": bad_total, "datatype": "Currency", "currency": "PHP", "indicator": "Red"},
		{"label": _("Credit Exposure"), "value": exposure, "datatype": "Currency", "currency": "PHP", "indicator": "Orange"},
		{"label": _("Unbilled Shipments"), "value": unbilled_count, "datatype": "Int", "indicator": "Orange"},
	]
	return columns, rows, None, chart, report_summary
