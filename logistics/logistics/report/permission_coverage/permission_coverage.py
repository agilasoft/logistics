# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from logistics.permission_studio.api import permission_coverage_rows


def execute(filters=None):
	columns = [
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 200},
		{"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data", "width": 180},
		{"label": _("Enabled"), "fieldname": "enabled", "fieldtype": "Check", "width": 90},
		{"label": _("In a Group"), "fieldname": "in_group", "fieldtype": "Data", "width": 110},
		{"label": _("Groups"), "fieldname": "groups", "fieldtype": "Data", "width": 240},
		{"label": _("Manual Permissions"), "fieldname": "manual_permissions", "fieldtype": "Int", "width": 150},
	]
	return columns, permission_coverage_rows(filters or {})
