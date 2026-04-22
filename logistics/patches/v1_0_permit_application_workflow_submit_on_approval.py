# Copyright (c) 2025, Agilasoft.com and contributors
# For license information, please see license.txt
"""
Migrate existing Permit Application workflow: Frappe submit only on Approve, not on filing.

- Pre-approval states (including business "Submitted" / Under Review / Rejected): doc_status 0
- Approve, Expired, Renewed: doc_status 1
- Draft -> Submitted (filed) transition: "Submit" -> "File" (clarity vs toolbar Submit)
Idempotent: safe to run multiple times.
"""

import frappe


def execute():
	if not frappe.db.exists("Workflow", "Permit Application"):
		return

	if not frappe.db.exists("Workflow Action Master", "File"):
		frappe.get_doc(
			{
				"doctype": "Workflow Action Master",
				"workflow_action_name": "File",
			}
		).insert(ignore_permissions=True)

	dmap = {
		"Draft": "0",
		"Submitted": "0",
		"Under Review": "0",
		"Rejected": "0",
		"Approved": "1",
		"Expired": "1",
		"Renewed": "1",
	}
	wf = frappe.get_doc("Workflow", "Permit Application")
	changed = False
	for row in wf.states:
		if row.state in dmap and row.doc_status != dmap[row.state]:
			row.doc_status = dmap[row.state]
			changed = True

	for row in wf.transitions:
		# old installs used "Submit" from Draft -> "Submitted" (filing)
		if row.state == "Draft" and row.next_state == "Submitted" and row.action in ("Submit", "File"):
			if row.action != "File":
				row.action = "File"
				changed = True

	if changed:
		wf.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Workflow")
	try:
		frappe.cache.hdel("workflow", "Permit Application")
	except Exception:
		pass
