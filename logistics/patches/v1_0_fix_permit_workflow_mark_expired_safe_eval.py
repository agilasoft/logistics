# Copyright (c) 2025, Agilasoft.com and contributors
# For license information, please see license.txt
"""Fix Permit Application workflow: Mark Expired condition used str(), which is not in workflow safe_eval globals."""

import frappe

_MARK_EXPIRED_OLD = (
	"doc.get('valid_to') and (str(doc.get('valid_to'))[0:10] < str(frappe.utils.now())[0:10])"
)
_MARK_EXPIRED_NEW = (
	"doc.get('valid_to') and frappe.utils.get_datetime(doc.get('valid_to')).date() < "
	"frappe.utils.get_datetime(frappe.utils.now()).date()"
)


def execute():
	if not frappe.db.exists("Workflow", "Permit Application"):
		return

	wf = frappe.get_doc("Workflow", "Permit Application")
	changed = False
	for row in wf.transitions:
		cond = row.condition
		if not cond:
			continue
		# Any transition using str() around valid_to (safe_eval has no str builtin)
		if (cond == _MARK_EXPIRED_OLD) or (
			"str(" in cond and "valid_to" in cond and cond.strip() != _MARK_EXPIRED_NEW
		):
			row.condition = _MARK_EXPIRED_NEW
			changed = True

	if changed:
		wf.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Workflow")
	try:
		frappe.cache.hdel("workflow", "Permit Application")
	except Exception:
		pass
