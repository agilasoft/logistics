# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import getdate, date_diff

from logistics.analytics_reports.bootstrap import tally_chart


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = tally_chart(data, "return_status", _("Deposits"))
	return columns, data, None, chart, []


def get_columns():
	return [
		{"fieldname": "container_number", "label": _("Container"), "fieldtype": "Link", "options": "Container", "width": 160},
		{"fieldname": "job_number", "label": _("Job Number"), "fieldtype": "Link", "options": "Job Number", "width": 120},
		{"fieldname": "event_type", "label": _("Event Type"), "fieldtype": "Data", "width": 130},
		{"fieldname": "line_amount", "label": _("Line amount"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "deposit_paid_date", "label": _("Deposit date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "return_status", "label": _("Return Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "je_reference", "label": _("Accounting ref"), "fieldtype": "Data", "width": 180},
		{"fieldname": "days_outstanding", "label": _("Days outstanding"), "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	today = getdate()
	rows = frappe.db.sql(
		"""
		SELECT
			c.name AS container_number,
			c.return_status,
			d.job_number,
			d.event_type,
			d.deposit_date,
			d.deposit_amount,
			d.refund_amount,
			d.reference_doctype,
			d.reference_name
		FROM `tabContainer Deposit` d
		INNER JOIN `tabContainer` c ON c.name = d.parent
		WHERE
			(IFNULL(d.deposit_amount, 0) > 0 OR IFNULL(d.refund_amount, 0) > 0)
			AND IFNULL(c.return_status, '') != 'Returned'
		ORDER BY c.name, d.idx
		""",
		as_dict=True,
	)
	for row in rows:
		row["line_amount"] = frappe.utils.flt(row.deposit_amount) or frappe.utils.flt(row.refund_amount)
		d = row.get("deposit_date")
		if d:
			row["deposit_paid_date"] = d
			row["days_outstanding"] = date_diff(today, d)
		else:
			row["deposit_paid_date"] = None
			row["days_outstanding"] = 0
		if row.get("reference_doctype") and row.get("reference_name"):
			row["je_reference"] = "{0}: {1}".format(row.reference_doctype, row.reference_name)
		else:
			row["je_reference"] = None
	return rows
