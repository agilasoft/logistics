# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import getdate, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "container_number", "label": _("Container Number"), "fieldtype": "Link", "options": "Container", "width": 140},
		{"fieldname": "deposit_amount", "label": _("Deposit Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "deposit_paid_date", "label": _("Deposit Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "return_status", "label": _("Return Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "days_outstanding", "label": _("Days Outstanding"), "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	today = getdate()
	data = frappe.db.sql("""
		SELECT
			c.name as container_number,
			c.deposit_amount,
			c.deposit_paid_date,
			c.return_status
		FROM `tabContainer` c
		WHERE c.deposit_amount > 0 AND c.return_status != 'Returned'
		ORDER BY c.deposit_amount DESC
	""", as_dict=True)
	for row in data:
		if row.deposit_paid_date:
			row["days_outstanding"] = date_diff(today, row.deposit_paid_date)
		else:
			row["days_outstanding"] = 0
	return data
