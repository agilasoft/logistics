# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Two-tier job/shipment readiness: submit, complete, and close gates."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.job_management.charge_reopen import CHARGE_REOPEN_CONFIG
from logistics.job_management.recognition_engine import (
	resolve_charge_row_cost,
	resolve_charge_row_selling,
)

GATES = ("submit", "complete", "close")

READINESS_DOCTYPES = frozenset(CHARGE_REOPEN_CONFIG.keys())

POSTED_INVOICE_STATUSES = frozenset(("Posted", "Paid"))

# Settings field → check code for complete/close hard blocks
_GATE_SETTING_MAP = {
	"complete": {
		"documents": "block_complete_if_required_documents_pending",
		"milestones": "block_complete_if_milestones_incomplete",
		"charges": "block_complete_if_charges_not_posted",
	},
	"close": {
		"documents": "block_close_if_required_documents_pending",
		"milestones": "block_close_if_milestones_incomplete",
		"charges": "block_close_if_charges_not_posted",
	},
}

_OPS_TERMINAL = {
	"Air Shipment": {
		"field": "tracking_status",
		"ok": frozenset(("Delivered",)),
	},
	"Sea Shipment": {
		"field": "shipping_status",
		"ok": frozenset(("Delivered", "Empty Container Returned", "Closed")),
	},
	"Declaration": {
		"field": "status",
		"ok": frozenset(("Cleared", "Released")),
	},
}


def _issue(code, message, severity="error", **extra):
	row = {"code": code, "message": message, "severity": severity}
	row.update(extra)
	return row


def _settings():
	try:
		return frappe.get_single("Logistics Settings")
	except Exception:
		return None


def _setting_on(settings, fieldname, default=0):
	if not settings:
		return cint(default)
	return cint(getattr(settings, fieldname, default))


def _charge_label(ch, idx):
	item = getattr(ch, "item_code", None) or getattr(ch, "charge_item", None) or _("Charge")
	name = getattr(ch, "item_name", None) or getattr(ch, "charge_name", None) or ""
	if name and name != item:
		return "#{0} {1} ({2})".format(idx + 1, item, name)
	return "#{0} {1}".format(idx + 1, item)


def _invoice_submitted(doctype, name):
	"""True only when the linked invoice exists and is submitted (docstatus=1)."""
	if not name:
		return False
	try:
		return cint(frappe.db.get_value(doctype, name, "docstatus")) == 1
	except Exception:
		return False


def _charge_item_code(ch):
	return getattr(ch, "item_code", None) or getattr(ch, "charge_item", None)


def check_charges_posted(doc):
	"""Return issues for billable/cost charges not posted to a submitted SI/PI."""
	issues = []
	charges = list(doc.get("charges") or [])
	for idx, ch in enumerate(charges):
		item_code = _charge_item_code(ch)
		label = _charge_label(ch, idx)

		revenue = flt(resolve_charge_row_selling(ch, prefer_actual=True))
		if revenue > 0 and item_code:
			si = getattr(ch, "sales_invoice", None)
			si_status = (getattr(ch, "sales_invoice_status", None) or "").strip()
			si_ok = (
				si_status in POSTED_INVOICE_STATUSES
				and si
				and _invoice_submitted("Sales Invoice", si)
			)
			if not si_ok:
				issues.append(
					_issue(
						"charge_not_posted_si",
						_("Revenue charge {0} is not posted to a submitted Sales Invoice (status: {1}).").format(
							label, si_status or _("Not Requested")
						),
						charge_idx=idx + 1,
						sales_invoice=si,
						sales_invoice_status=si_status,
					)
				)

		cost = flt(resolve_charge_row_cost(ch, prefer_actual=True))
		if cost > 0 and item_code:
			pi = getattr(ch, "purchase_invoice", None)
			pi_status = (getattr(ch, "purchase_invoice_status", None) or "").strip()
			pi_ok = (
				pi_status in POSTED_INVOICE_STATUSES
				and pi
				and _invoice_submitted("Purchase Invoice", pi)
			)
			if not pi_ok:
				issues.append(
					_issue(
						"charge_not_posted_pi",
						_("Cost charge {0} is not posted to a submitted Purchase Invoice (status: {1}).").format(
							label, pi_status or _("Not Requested")
						),
						charge_idx=idx + 1,
						purchase_invoice=pi,
						purchase_invoice_status=pi_status,
					)
				)
	return issues


def check_required_documents(doc):
	"""Return issues for required Job Document rows that are incomplete."""
	from logistics.document_management.api import get_incomplete_required_documents

	incomplete = get_incomplete_required_documents(doc)
	issues = []
	for label in incomplete:
		issues.append(
			_issue(
				"document_incomplete",
				_("Required document incomplete: {0}").format(label),
				document=label,
			)
		)
	return issues


def _row_get(row, key, default=None):
	if isinstance(row, dict):
		return row.get(key, default)
	if hasattr(row, "get"):
		try:
			return row.get(key, default)
		except Exception:
			pass
	return getattr(row, key, default)


def check_milestones_complete(doc):
	"""Return issues for milestones that are not Completed."""
	if not hasattr(doc, "milestones"):
		return []
	issues = []
	for idx, row in enumerate(doc.get("milestones") or []):
		status = (_row_get(row, "status") or "").strip()
		if status == "Completed":
			continue
		label = (
			_row_get(row, "milestone")
			or _row_get(row, "milestone_name")
			or _row_get(row, "description")
			or _("Milestone #{0}").format(idx + 1)
		)
		issues.append(
			_issue(
				"milestone_incomplete",
				_("Milestone incomplete: {0} ({1})").format(label, status or _("Planned")),
				milestone=label,
				status=status,
			)
		)
	return issues


def check_submit_master_data(doc):
	"""Submit-tier soft checklist for missing master data (hard blocks stay on DocType before_submit)."""
	issues = []
	dt = doc.doctype
	if dt == "Air Shipment":
		required = [
			("booking_date", _("Booking Date")),
			("air_booking", _("Air Booking")),
			("shipper", _("Shipper")),
			("consignee", _("Consignee")),
			("origin_port", _("Origin Port")),
			("destination_port", _("Destination Port")),
			("direction", _("Direction")),
			("local_customer", _("Local Customer")),
		]
		for field, label in required:
			if not getattr(doc, field, None):
				issues.append(
					_issue("missing_party", _("{0} is required").format(label), field=field)
				)
		if not getattr(doc, "airline", None):
			# Soft warning — airline often filled later via MAWB
			issues.append(
				_issue(
					"missing_carrier",
					_("Airline is not set"),
					severity="warning",
					field="airline",
				)
			)
	elif dt == "Sea Shipment":
		required = [
			("booking_date", _("Booking Date")),
			("sea_booking", _("Sea Booking")),
			("shipper", _("Shipper")),
			("consignee", _("Consignee")),
			("origin_port", _("Origin Port")),
			("destination_port", _("Destination Port")),
			("direction", _("Direction")),
			("local_customer", _("Local Customer")),
		]
		for field, label in required:
			if not getattr(doc, field, None):
				issues.append(
					_issue("missing_party", _("{0} is required").format(label), field=field)
				)
	return issues


def check_ops_terminal_status(doc):
	"""Warning when operational status has not reached a terminal value."""
	spec = _OPS_TERMINAL.get(doc.doctype)
	if not spec:
		if doc.doctype == "Transport Job":
			return _check_transport_legs_terminal(doc)
		return []
	field = spec["field"]
	cur = (getattr(doc, field, None) or "").strip()
	if cur in spec["ok"]:
		return []
	return [
		_issue(
			"ops_not_terminal",
			_("{0} is {1}; expected a terminal status before close.").format(
				_(frappe.unscrub(field)), cur or _("(empty)")
			),
			severity="warning",
			field=field,
			status=cur,
		)
	]


def _check_transport_legs_terminal(doc):
	legs = list(doc.get("legs") or doc.get("transport_legs") or [])
	if not legs:
		return []
	bad = []
	for idx, leg in enumerate(legs):
		status = (getattr(leg, "status", None) or "").strip()
		if status not in ("Completed", "Billed"):
			bad.append("#{0} ({1})".format(idx + 1, status or _("empty")))
	if not bad:
		return []
	return [
		_issue(
			"ops_not_terminal",
			_("Transport leg(s) not Completed/Billed: {0}").format(", ".join(bad)),
			severity="warning",
		)
	]


def get_job_readiness(doc, gate="close"):
	"""
	Build readiness checklist for a gate.

	Returns dict: { ok, gate, doctype, name, errors[], warnings[], checks{} }
	``ok`` is True when there are no error-severity issues (warnings allowed).
	"""
	gate = (gate or "close").strip().lower()
	if gate not in GATES:
		frappe.throw(_("Invalid readiness gate: {0}").format(gate))

	errors = []
	warnings = []
	checks = {}

	if gate == "submit":
		master = check_submit_master_data(doc)
		docs = check_required_documents(doc)
		checks["master_data"] = master
		checks["documents"] = docs
		for issue in master + docs:
			(errors if issue["severity"] == "error" else warnings).append(issue)
	else:
		docs = check_required_documents(doc)
		milestones = check_milestones_complete(doc)
		charges = check_charges_posted(doc)
		ops = check_ops_terminal_status(doc)
		checks["documents"] = docs
		checks["milestones"] = milestones
		checks["charges"] = charges
		checks["ops_terminal"] = ops
		for issue in docs + milestones + charges:
			# Severity for enforce is decided by settings; checklist always reports as error potential
			errors.append(issue)
		for issue in ops:
			warnings.append(issue)

	return {
		"ok": not errors,
		"gate": gate,
		"doctype": getattr(doc, "doctype", None),
		"name": getattr(doc, "name", None),
		"errors": errors,
		"warnings": warnings,
		"checks": checks,
	}


def _blocking_issues_for_gate(doc, gate, settings=None):
	"""Return list of issues that should hard-block for this gate given settings."""
	settings = settings if settings is not None else _settings()
	gate = (gate or "").strip().lower()
	blocking = []

	if gate == "submit":
		# Document submit block remains in document_management.api (settings already there).
		# Master-data hard blocks stay on DocType before_submit.
		return blocking

	field_map = _GATE_SETTING_MAP.get(gate) or {}
	if _setting_on(settings, field_map.get("documents"), 0 if gate == "complete" else 1):
		blocking.extend(check_required_documents(doc))
	if _setting_on(settings, field_map.get("milestones"), 0 if gate == "complete" else 1):
		blocking.extend(check_milestones_complete(doc))
	if _setting_on(settings, field_map.get("charges"), 0 if gate == "complete" else 1):
		blocking.extend(check_charges_posted(doc))
	return blocking


def enforce_job_readiness(doc, gate="close"):
	"""Throw when settings require blocking issues for the gate."""
	if not doc or getattr(doc, "flags", None) and doc.flags.get("skip_job_readiness"):
		return
	if doc.doctype not in READINESS_DOCTYPES:
		return

	blocking = _blocking_issues_for_gate(doc, gate)
	if not blocking:
		return

	lines = [frappe.utils.escape_html(i.get("message") or i.get("code") or "") for i in blocking]
	title = {
		"complete": _("Job not ready to Complete"),
		"close": _("Job not ready to Close"),
		"submit": _("Job not ready to Submit"),
	}.get(gate, _("Job readiness"))
	msg = _("Cannot set Job Status to {0}: resolve the following first.").format(
		_("Completed") if gate == "complete" else _("Closed") if gate == "close" else gate
	)
	frappe.throw(msg + "\n\n" + "\n".join(lines), title=title)


def _status_field_for(doc):
	cfg = CHARGE_REOPEN_CONFIG.get(doc.doctype)
	return cfg["status_field"] if cfg else None


def validate_job_readiness_on_status_change(doc, method=None):
	"""DocType validate hook: enforce complete/close readiness when Job Status transitions."""
	if not doc or doc.doctype not in READINESS_DOCTYPES:
		return
	if getattr(doc, "flags", None) and doc.flags.get("skip_job_readiness"):
		return
	if cint(getattr(doc, "docstatus", 0)) != 1:
		return

	field = _status_field_for(doc)
	if not field:
		return

	new_val = (getattr(doc, field, None) or "").strip()
	if new_val not in ("Completed", "Closed"):
		return

	# Only enforce when status is changing into the target (or first save into it)
	changed = False
	try:
		changed = doc.has_value_changed(field)
	except Exception:
		changed = True
	if not changed and not doc.is_new():
		# Still enforce Closed path when Close Job API sets flag then saves
		if not getattr(doc.flags, "enforce_job_readiness_close", False):
			return

	if new_val == "Completed":
		enforce_job_readiness(doc, gate="complete")
	elif new_val == "Closed":
		enforce_job_readiness(doc, gate="close")


@frappe.whitelist()
def get_job_readiness_summary(doctype, name, gate=None):
	"""Whitelist: structured readiness checklist for desk Action menu."""
	if doctype not in READINESS_DOCTYPES:
		frappe.throw(_("Job readiness is not available for {0}.").format(doctype))
	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} {1} does not exist.").format(doctype, name))

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	if not gate:
		# Infer useful default from current status
		field = _status_field_for(doc)
		cur = (getattr(doc, field, None) or "").strip() if field else ""
		if cur in ("Completed", "Reopened", "Closed"):
			gate = "close"
		elif cint(doc.docstatus) == 1:
			gate = "complete"
		else:
			gate = "submit"

	result = get_job_readiness(doc, gate=gate)

	# Annotate which checks would hard-block under current settings
	settings = _settings()
	blocking_codes = set()
	for issue in _blocking_issues_for_gate(doc, gate, settings=settings):
		blocking_codes.add(issue.get("code"))
	result["would_block"] = bool(blocking_codes)
	result["blocking_codes"] = sorted(blocking_codes)
	return result
