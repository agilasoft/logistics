# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Grant operational managers create/write/submit on Air/Sea Shipment.

Create Shipment is now gated on ``can_create`` of the shipment DocType. JSON
previously listed only System Manager, which would hide the button for
Air/Sea Freight Manager after the client gate.
"""

from __future__ import annotations

import frappe

ROWS = [
	{
		"parent": "Air Shipment",
		"role": "Air Freight Manager",
		"cancel": 0,
	},
	{
		"parent": "Sea Shipment",
		"role": "Sea Freight Manager",
		"cancel": 1,
	},
]


def execute():
	for spec in ROWS:
		_ensure_manager_perm(spec["parent"], spec["role"], cancel=spec["cancel"])
		frappe.clear_cache(doctype=spec["parent"])


def _ensure_manager_perm(doctype: str, role: str, cancel: int = 0):
	if not frappe.db.exists("DocType", doctype):
		return
	if not frappe.db.exists("Role", role):
		return

	dt = frappe.get_doc("DocType", doctype)
	for row in dt.permissions or []:
		if row.role == role and int(row.permlevel or 0) == 0:
			row.read = 1
			row.write = 1
			row.create = 1
			row.submit = 1
			row.delete = 1
			row.print = 1
			row.email = 1
			row.report = 1
			row.export = 1
			row.share = 1
			if cancel:
				row.cancel = 1
			dt.save(ignore_permissions=True)
			return

	dt.append(
		"permissions",
		{
			"role": role,
			"permlevel": 0,
			"read": 1,
			"write": 1,
			"create": 1,
			"submit": 1,
			"delete": 1,
			"cancel": 1 if cancel else 0,
			"print": 1,
			"email": 1,
			"report": 1,
			"export": 1,
			"share": 1,
		},
	)
	dt.save(ignore_permissions=True)
