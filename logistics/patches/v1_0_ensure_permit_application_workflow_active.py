# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt
"""Ensure Permit Application has an active Workflow.

Without an active workflow, the desk shows the default Submit button for this submittable doctype.
Submit is only allowed when status is Approved (see permit_application.before_submit), so users
see a confusing ValidationError. This patch creates the workflow if missing (e.g. skipped migrate)
or re-activates it if it was turned off. Idempotent.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Permit Application"):
		return

	from logistics.patches.v1_0_permit_application_workflow import (
		ensure_permit_workflow,
		ensure_workflow_masters,
	)

	ensure_workflow_masters()
	wname = "Permit Application"

	if frappe.db.exists("Workflow", wname):
		wf = frappe.get_doc("Workflow", wname)
		if not wf.is_active:
			wf.is_active = 1
			wf.save(ignore_permissions=True)
	else:
		ensure_permit_workflow()

	frappe.clear_cache(doctype="Workflow")
	try:
		frappe.cache.hdel("workflow", "Permit Application")
	except Exception:
		pass
