# Copyright (c) 2025, Agilasoft.com and contributors
# For license information, please see license.txt
"""Idempotent: replace str() in Permit Application workflow conditions — str is not in safe_eval globals.

Rewrites the Mark Expired condition (action Mark Expired → Expired) and any other transition whose
condition still contains str( together with valid_to, to a get_datetime/.date() comparison.
"""

import frappe

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
		if not cond or "str(" not in cond:
			continue
		if cond.strip() == _MARK_EXPIRED_NEW:
			continue
		# Any str() breaks workflow safe_eval (no str builtin). Standard case is Mark Expired.
		is_mark_expired = row.action == "Mark Expired" and row.next_state == "Expired"
		if is_mark_expired or "valid_to" in cond:
			row.condition = _MARK_EXPIRED_NEW
			changed = True

	if changed:
		wf.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Workflow")
	try:
		frappe.cache.hdel("workflow", "Permit Application")
	except Exception:
		pass
