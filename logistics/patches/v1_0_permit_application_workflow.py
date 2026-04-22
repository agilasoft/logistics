# Copyright (c) 2025, Agilasoft.com and contributors
# For license information, please see license.txt
"""Idempotent: Workflow State / Action Master records and active Workflow on Permit Application (status field).

Frappe Submit (docstatus=1) happens on workflow Approve (Submitted -> Approved), not when filing
(Draft -> Submitted in business / status field). Pre-approval states keep docstatus=0.
"""

import frappe


def execute():
	ensure_workflow_masters()
	ensure_permit_workflow()
	frappe.clear_cache(doctype="Workflow")
	try:
		frappe.cache.hdel("workflow", "Permit Application")
	except Exception:
		pass


def ensure_workflow_masters() -> None:
	for s in (
		"Draft",
		"Submitted",
		"Under Review",
		"Approved",
		"Rejected",
		"Expired",
		"Renewed",
	):
		if not frappe.db.exists("Workflow State", s):
			frappe.get_doc(
				{
					"doctype": "Workflow State",
					"workflow_state_name": s,
				}
			).insert(ignore_permissions=True)

	for a in ("File", "Start Review", "Reject", "Approve", "Mark Expired"):
		if not frappe.db.exists("Workflow Action Master", a):
			frappe.get_doc(
				{
					"doctype": "Workflow Action Master",
					"workflow_action_name": a,
				}
			).insert(ignore_permissions=True)


def ensure_permit_workflow() -> None:
	if not frappe.db.exists("DocType", "Permit Application"):
		return

	allowed = "Customs User" if frappe.db.exists("Role", "Customs User") else "System Manager"
	all_edit = "All" if frappe.db.exists("Role", "All") else allowed

	wname = "Permit Application"
	if frappe.db.exists("Workflow", wname):
		return

	# doc_status: 0 = not Frappe-submitted, 1 = Frappe Submitted, 2 = Cancelled
	# Only "Approved" (and post-approval business states) use docstatus 1; filing/review use 0
	states = [
		("Draft", "0", all_edit),
		("Submitted", "0", all_edit),  # filed, still draft in ERP
		("Under Review", "0", allowed),
		("Rejected", "0", all_edit),  # stay draft, amend and re-file
		("Approved", "1", all_edit),  # Frappe submit runs on transition to this state
		("Expired", "1", all_edit),
		("Renewed", "1", all_edit),
	]
	# Frappe: before_save, validate, validate_workflow; on Approve, apply_workflow then doc.submit()
	transitions = [
		("Draft", "File", "Submitted", None),  # file with authority, doc stays draft
		("Submitted", "Start Review", "Under Review", None),
		("Submitted", "Reject", "Rejected", None),
		("Under Review", "Approve", "Approved", None),  # triggers doc.submit() when current doc is draft
		("Under Review", "Reject", "Rejected", None),
		(
			"Approved",
			"Mark Expired",
			"Expired",
			"doc.get('valid_to') and (str(doc.get('valid_to'))[0:10] < str(frappe.utils.now())[0:10])",
		),
	]

	wf = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": wname,
			"document_type": "Permit Application",
			"is_active": 1,
			"override_status": 0,
			"send_email_alert": 0,
			"workflow_state_field": "status",
		}
	)
	for state, dstatus, aedit in states:
		wf.append("states", {"state": state, "doc_status": dstatus, "allow_edit": aedit})

	for state, action, nxt, cond in transitions:
		row = {
			"state": state,
			"action": action,
			"next_state": nxt,
			"allowed": allowed,
			"allow_self_approval": 1,
		}
		if cond is not None:
			row["condition"] = cond
		wf.append("transitions", row)

	wf.insert(ignore_permissions=True)
