# Copyright (c) 2025, Agilasoft.com and contributors
# For license information, please see license.txt
"""Idempotent: replace str() in Permit Application workflow conditions — str is not in safe_eval globals.

Follow-up to v1_0_fix_permit_workflow_mark_expired_safe_eval: broader match (any transition with
str( and valid_to), for sites where the first patch did not apply or workflow was re-imported.
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
		if not cond or "str(" not in cond or "valid_to" not in cond:
			continue
		if cond.strip() == _MARK_EXPIRED_NEW:
			continue
		row.condition = _MARK_EXPIRED_NEW
		changed = True

	if changed:
		wf.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Workflow")
	try:
		frappe.cache.hdel("workflow", "Permit Application")
	except Exception:
		pass
