# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.analytics_reports.bootstrap import tally_chart


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = tally_chart(data, "container_type", _("Penalties"))
	return columns, data, None, chart, []


def get_columns():
	return [
		{"fieldname": "container_number", "label": _("Container Number"), "fieldtype": "Link", "options": "Container", "width": 140},
		{"fieldname": "container_type", "label": _("Container Type"), "fieldtype": "Link", "options": "Container Type", "width": 120},
		{"fieldname": "demurrage_days", "label": _("Demurrage Days"), "fieldtype": "Float", "width": 110},
		{"fieldname": "detention_days", "label": _("Detention Days"), "fieldtype": "Float", "width": 110},
		{"fieldname": "estimated_penalty_amount", "label": _("Estimated Penalty"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "free_time_until", "label": _("Free Time Until"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "linked_shipment", "label": _("Linked Shipment"), "fieldtype": "Link", "options": "Sea Shipment", "width": 130},
	]


def get_data(filters):
	data = frappe.db.sql("""
		SELECT
			c.name as container_number,
			c.container_type,
			c.demurrage_days,
			c.detention_days,
			c.estimated_penalty_amount,
			c.free_time_until,
			(SELECT sfc.parent FROM `tabSea Freight Containers` sfc
			 WHERE sfc.container = c.name AND sfc.parenttype = 'Sea Shipment' LIMIT 1) as linked_shipment
		FROM `tabContainer` c
		WHERE c.has_penalties = 1
		ORDER BY c.estimated_penalty_amount DESC
	""", as_dict=True)
	return data
