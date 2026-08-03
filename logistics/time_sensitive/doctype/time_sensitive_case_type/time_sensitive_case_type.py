# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TimeSensitiveCaseType(Document):
	pass


DEFAULT_CASE_TYPES = (
	("AOG", "Aircraft on Ground", "Critical", 10, 2),
	("ORGAN", "Live Organ", "Critical", 5, 1),
	("JIT", "Just-in-Time Line Stop", "Urgent", 15, 2),
	("CEF", "Critical Equipment Failure", "Urgent", 15, 4),
	("OBL", "Original BL Delivery", "High", 30, 8),
	("OTHER", "Other", "Urgent", 15, 4),
)


def seed_default_case_types():
	"""Idempotently seed standard time-sensitive case types."""
	for code, name, severity, response_mins, at_risk_hours in DEFAULT_CASE_TYPES:
		if frappe.db.exists("Time Sensitive Case Type", code):
			continue
		doc = frappe.new_doc("Time Sensitive Case Type")
		doc.code = code
		doc.case_type_name = name
		doc.default_severity = severity
		doc.default_response_minutes = response_mins
		doc.default_at_risk_hours = at_risk_hours
		doc.enabled = 1
		doc.insert(ignore_permissions=True)
