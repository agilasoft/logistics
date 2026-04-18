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
	chart = tally_chart(data, "status", _("Containers"))
	return columns, data, None, chart, []


def get_columns():
	return [
		{"fieldname": "container_number", "label": _("Container Number"), "fieldtype": "Link", "options": "Container", "width": 140},
		{"fieldname": "container_type", "label": _("Container Type"), "fieldtype": "Link", "options": "Container Type", "width": 120},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 140},
		{"fieldname": "current_location_name", "label": _("Current Location"), "fieldtype": "Data", "width": 150},
		{"fieldname": "linked_shipment", "label": _("Linked Shipment"), "fieldtype": "Link", "options": "Sea Shipment", "width": 130},
		{"fieldname": "demurrage_days", "label": _("Demurrage Days"), "fieldtype": "Float", "width": 110},
		{"fieldname": "detention_days", "label": _("Detention Days"), "fieldtype": "Float", "width": 110},
		{"fieldname": "return_status", "label": _("Return Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "estimated_penalty_amount", "label": _("Estimated Penalty"), "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("status"):
		conditions.append("c.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("container_type"):
		conditions.append("c.container_type = %(container_type)s")
		values["container_type"] = filters["container_type"]
	if filters.get("return_status"):
		conditions.append("c.return_status = %(return_status)s")
		values["return_status"] = filters["return_status"]

	where = " AND " + " AND ".join(conditions) if conditions else ""

	data = frappe.db.sql("""
		SELECT
			c.name as container_number,
			c.container_type,
			c.status,
			c.current_location_name,
			(SELECT sfc.parent FROM `tabSea Freight Containers` sfc
			 WHERE sfc.container = c.name AND sfc.parenttype = 'Sea Shipment' LIMIT 1) as linked_shipment,
			c.demurrage_days,
			c.detention_days,
			c.return_status,
			c.estimated_penalty_amount
		FROM `tabContainer` c
		WHERE 1=1 {0}
		ORDER BY c.modified DESC
	""".format(where), values, as_dict=True)
	return data
