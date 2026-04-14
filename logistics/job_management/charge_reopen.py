# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Lock charge lines on submitted jobs/shipments when Job Status is closing; Reopened unlocks edits."""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.job_management.logistics_job_status import (
	CHARGE_LOCKED_STATUSES,
	JOB_STATUS_REOPENED,
)

# status_field: DocType field holding logistics Job Status (same options as Transport Job)
CHARGE_REOPEN_CONFIG = {
	"Transport Job": {
		"status_field": "status",
		"locked_values": CHARGE_LOCKED_STATUSES,
		"reopened_value": JOB_STATUS_REOPENED,
		"uses_transition_flags": True,
	},
	"Sea Shipment": {
		"status_field": "job_status",
		"locked_values": CHARGE_LOCKED_STATUSES,
		"reopened_value": JOB_STATUS_REOPENED,
		"uses_transition_flags": False,
	},
	"Air Shipment": {
		"status_field": "job_status",
		"locked_values": CHARGE_LOCKED_STATUSES,
		"reopened_value": JOB_STATUS_REOPENED,
		"uses_transition_flags": False,
	},
	"Warehouse Job": {
		"status_field": "job_status",
		"locked_values": CHARGE_LOCKED_STATUSES,
		"reopened_value": JOB_STATUS_REOPENED,
		"uses_transition_flags": False,
	},
	"Declaration": {
		"status_field": "job_status",
		"locked_values": CHARGE_LOCKED_STATUSES,
		"reopened_value": JOB_STATUS_REOPENED,
		"uses_transition_flags": False,
	},
}


def validate_submitted_charges_not_locked(doc, method=None):
	"""DocType validate hook: block charge grid changes when Job Status locks charges."""
	if not doc or getattr(doc, "docstatus", None) != 1:
		return
	cfg = CHARGE_REOPEN_CONFIG.get(doc.doctype)
	if not cfg:
		return
	field = cfg["status_field"]
	val = (getattr(doc, field, None) or "").strip()
	if val not in cfg["locked_values"]:
		return
	if not doc.has_value_changed("charges"):
		return
	label = _field_label(doc.doctype, field)
	frappe.throw(
		_("Cannot modify charges while {0} is {1}. Use Reopen Job (Action menu) to allow additional charges.").format(
			label, val
		),
		title=_("Charges locked"),
	)


def _field_label(doctype, fieldname):
	try:
		df = frappe.get_meta(doctype).get_field(fieldname)
		if df and df.label:
			return _(df.label)
	except Exception:
		pass
	return frappe.unscrub(fieldname)


@frappe.whitelist()
def reopen_job_for_charges(doctype, name):
	"""Set Job Status to Reopened so charge lines can be edited on a submitted document."""
	if doctype not in CHARGE_REOPEN_CONFIG:
		frappe.throw(_("Reopen Job is not available for {0}.").format(doctype))

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted documents can be reopened for charges."))

	cfg = CHARGE_REOPEN_CONFIG[doctype]
	field = cfg["status_field"]
	cur = (getattr(doc, field, None) or "").strip()
	if cur not in cfg["locked_values"]:
		frappe.throw(
			_("Reopen Job is only available when {0} is Completed or Closed (current: {1}).").format(
				_field_label(doctype, field), cur or _("(empty)")
			),
			title=_("Cannot reopen"),
		)

	new_val = cfg["reopened_value"]
	setattr(doc, field, new_val)
	if cfg.get("uses_transition_flags"):
		doc.flags.allow_charge_reopen_transition = True
	doc.flags.skip_job_status_sync = True
	doc.save()
	return {"ok": 1, "doctype": doctype, "name": name, field: new_val}


@frappe.whitelist()
def close_job_for_charges(doctype, name):
	"""Set Job Status to Closed after charge edits."""
	if doctype not in CHARGE_REOPEN_CONFIG:
		frappe.throw(_("Close Job is not available for {0}.").format(doctype))

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted documents can be closed."))

	cfg = CHARGE_REOPEN_CONFIG[doctype]
	field = cfg["status_field"]
	cur = (getattr(doc, field, None) or "").strip()
	if cur != cfg["reopened_value"]:
		frappe.throw(
			_("Close Job is only available when {0} is {1}.").format(
				_field_label(doctype, field), cfg["reopened_value"]
			)
		)

	setattr(doc, field, "Closed")
	if cfg.get("uses_transition_flags"):
		doc.flags.allow_charge_close_transition = True
	doc.flags.skip_job_status_sync = True
	doc.save()
	return {"ok": 1, "doctype": doctype, "name": name, field: "Closed"}
