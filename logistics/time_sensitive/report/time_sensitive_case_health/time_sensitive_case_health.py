# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": _("Case"), "fieldname": "name", "fieldtype": "Link", "options": "Time Sensitive Case", "width": 140},
		{"label": _("Title"), "fieldname": "case_title", "fieldtype": "Data", "width": 180},
		{"label": _("Type"), "fieldname": "case_type_name", "fieldtype": "Data", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("SLA"), "fieldname": "sla_status", "fieldtype": "Data", "width": 100},
		{"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 90},
		{"label": _("Deadline"), "fieldname": "critical_deadline", "fieldtype": "Datetime", "width": 150},
		{"label": _("Remaining (s)"), "fieldname": "remaining_seconds", "fieldtype": "Int", "width": 110},
		{"label": _("Coordinator"), "fieldname": "coordinator", "fieldtype": "Link", "options": "User", "width": 140},
	]

	conds = ["docstatus < 2"]
	values = {}
	if filters.get("status"):
		conds.append("status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("sla_status"):
		conds.append("sla_status = %(sla_status)s")
		values["sla_status"] = filters["sla_status"]
	if filters.get("case_type"):
		conds.append("case_type = %(case_type)s")
		values["case_type"] = filters["case_type"]
	if filters.get("customer"):
		conds.append("customer = %(customer)s")
		values["customer"] = filters["customer"]

	where = " AND ".join(conds)
	rows = frappe.db.sql(
		f"""
		SELECT name, case_title, case_type_name, customer, status, sla_status,
		       severity, critical_deadline, coordinator
		FROM `tabTime Sensitive Case`
		WHERE {where}
		ORDER BY
			FIELD(sla_status, 'Breached', 'At Risk', 'On Track', 'Completed'),
			critical_deadline ASC
		LIMIT 500
		""",
		values,
		as_dict=True,
	)
	now = now_datetime()
	for r in rows:
		if r.critical_deadline:
			r.remaining_seconds = int(time_diff_in_seconds(get_datetime(r.critical_deadline), now))
		else:
			r.remaining_seconds = None
	return columns, rows
