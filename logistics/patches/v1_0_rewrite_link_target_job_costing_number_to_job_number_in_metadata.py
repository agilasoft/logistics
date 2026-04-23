# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
After renaming DocType **Job Costing Number** → **Job Number**, rows in ``tabCustom Field``,
``tabDocField``, and ``tabAccounting Dimension`` may still store ``options`` / ``document_type``
= "Job Costing Number". Any Link to that string makes Desk/API throw **DocType Job Costing Number not found**.

Rewrite those values to **Job Number** when that DocType exists. Idempotent.
"""

import frappe
from frappe.utils import get_table_name

OLD = "Job Costing Number"
NEW = "Job Number"


def _replace_text_column(doctype: str, column: str) -> None:
	if not frappe.db.has_column(doctype, column):
		return
	tn = get_table_name(doctype, wrap_in_backticks=True)
	frappe.db.sql(
		f"UPDATE {tn} SET `{column}` = REPLACE(`{column}`, %s, %s) WHERE `{column}` LIKE %s",
		(OLD, NEW, f"%{OLD}%"),
	)


def execute():
	if not frappe.db.exists("DocType", NEW):
		return True

	frappe.db.sql(
		"UPDATE `tabCustom Field` SET options = %s WHERE options = %s",
		(NEW, OLD),
	)
	frappe.db.sql(
		"UPDATE `tabDocField` SET options = %s WHERE options = %s",
		(NEW, OLD),
	)
	frappe.db.sql(
		"UPDATE `tabAccounting Dimension` SET document_type = %s WHERE document_type = %s",
		(NEW, OLD),
	)
	if frappe.db.has_column("DocType Link", "link_doctype"):
		frappe.db.sql(
			"UPDATE `tabDocType Link` SET link_doctype = %s WHERE link_doctype = %s",
			(NEW, OLD),
		)

	_replace_text_column("Property Setter", "value")
	_replace_text_column("Workspace", "content")
	_replace_text_column("Client Script", "script")
	if frappe.db.table_exists("Server Script"):
		_replace_text_column("Server Script", "script")

	frappe.db.commit()
	frappe.clear_cache()
	return True
