# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

"""
Cross-module credit control: Customer logistics credit status, ERPNext credit limit,
overdue Sales Invoices, and per-doctype rules in Logistics Settings.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, add_days

# DocTypes that participate in hooks (must match registered doc_events).
# Party is resolved via get_credit_customer_for_doc (customer, local_customer, booking_party, …).
CREDIT_SUBJECT_DOCTYPES = (
	"Sales Quote",
	"Air Booking",
	"Air Shipment",
	"Sea Booking",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Transport Consolidation Job",
	"Declaration",
	"Declaration Order",
	"General Job",
	"Warehouse Job",
	"Special Project",
	"Inbound Order",
	"Release Order",
	"Transfer Order",
	"VAS Order",
	"Stocktake Order",
	"Gate Pass",
	"Periodic Billing",
	"Warehouse Contract",
)

_CUSTOMER_PARTY_FIELDS = (
	"customer",
	"local_customer",
	"booking_party",
	"controlling_party",
)


def get_credit_settings():
	if not frappe.db.exists("DocType", "Logistics Settings"):
		return None
	try:
		return frappe.get_single("Logistics Settings")
	except Exception:
		return None


def user_has_credit_bypass(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	settings = get_credit_settings()
	if not settings:
		return False
	role = getattr(settings, "credit_control_bypass_role", None)
	if not role:
		return False
	return role in frappe.get_roles(user)


def get_credit_customer_for_doc(doc):
	"""Return Customer name for credit checks, or None."""
	if not doc:
		return None
	for fname in _CUSTOMER_PARTY_FIELDS:
		df = doc.meta.get_field(fname)
		if df and doc.get(fname) and df.options == "Customer":
			return doc.get(fname)
	return None


def get_credit_company_for_doc(doc):
	"""Company for ERPNext credit limit / overdue checks."""
	if doc.get("company"):
		return doc.get("company")
	return frappe.defaults.get_user_default("Company")


def _full_hold_rule_for_all_doctypes():
	"""Virtual rule when Apply hold to all DocTypes is on: all Warn / Hold flags enabled."""
	return frappe._dict(block_insert=1, block_save=1, block_submit=1, block_print=1)


def _get_effective_credit_rule(settings, doctype):
	"""
	Return a mapping with block_insert, block_save, block_submit, block_print, or None if DocType not subject.
	"""
	if getattr(settings, "credit_apply_hold_to_all_doctypes", 0):
		if doctype not in CREDIT_SUBJECT_DOCTYPES:
			return None
		return _full_hold_rule_for_all_doctypes()
	for row in settings.get("credit_control_rules") or []:
		if row.controlled_doctype == doctype:
			return row
	return None


def has_active_credit_lift(doc):
	"""
	Submitted Credit Hold Lift Request that matches customer, relieved DocType, validity dates,
	and optional company / single-document scope. When True, credit blocks and save warnings are skipped.
	"""
	if not doc or not frappe.db.exists("DocType", "Credit Hold Lift Request"):
		return False
	customer = get_credit_customer_for_doc(doc)
	if not customer:
		return False
	today = getdate()
	candidates = frappe.get_all(
		"Credit Hold Lift Request",
		filters=[
			["docstatus", "=", 1],
			["customer", "=", customer],
			["relieved_doctype", "=", doc.doctype],
			["valid_from", "<=", today],
			["valid_to", ">=", today],
		],
		fields=["scope", "reference_name", "company"],
	)
	doc_company = doc.get("company")
	for row in candidates:
		if row.company:
			if not doc_company or row.company != doc_company:
				continue
		scope = row.scope or "All Documents"
		if scope == "Single Document":
			if not doc.get("name") or row.reference_name != doc.get("name"):
				continue
		return True
	return False


def get_manual_credit_status(customer):
	if not customer or not frappe.db.exists("Customer", customer):
		return "Good"
	status = frappe.db.get_value("Customer", customer, "logistics_credit_status")
	return status or "Good"


def is_credit_limit_breached(customer, company):
	if not customer or not company:
		return False
	try:
		from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding
	except ImportError:
		return False
	limit = flt(get_credit_limit(customer, company))
	if limit <= 0:
		return False
	outstanding = flt(get_customer_outstanding(customer, company))
	return outstanding > limit


def has_overdue_outstanding_invoices(customer, company, grace_days=0):
	if not customer or not company:
		return False
	cutoff = add_days(getdate(), -cint(grace_days))
	return bool(
		frappe.db.sql(
			"""
			select name from `tabSales Invoice`
			where customer = %s and company = %s and docstatus = 1
			and ifnull(outstanding_amount, 0) > 0
			and due_date is not null and due_date < %s
			limit 1
			""",
			(customer, company, cutoff),
		)
	)


def credit_hold_reasons(customer, company, settings):
	"""Return list of translated reason strings."""
	reasons = []
	if not customer:
		return reasons

	status = get_manual_credit_status(customer)
	if getattr(settings, "credit_block_on_status_on_hold", 0) and status == "On Hold":
		reasons.append(_("Customer credit status is On Hold."))
	if getattr(settings, "credit_block_on_status_watch", 0) and status == "Watch":
		reasons.append(_("Customer credit status is Watch."))

	if getattr(settings, "credit_apply_limit_breach", 0) and company:
		if is_credit_limit_breached(customer, company):
			reasons.append(_("Customer is over credit limit."))

	if getattr(settings, "credit_apply_payment_terms_breach", 0) and company:
		grace = getattr(settings, "credit_payment_terms_grace_days", 0) or 0
		if has_overdue_outstanding_invoices(customer, company, grace_days=grace):
			reasons.append(_("Customer has overdue receivables (payment terms deviation)."))

	return reasons


def is_under_credit_hold(doc, settings):
	customer = get_credit_customer_for_doc(doc)
	if not customer:
		return False, []
	company = get_credit_company_for_doc(doc)
	reasons = credit_hold_reasons(customer, company, settings)
	return bool(reasons), reasons


def get_credit_block_message(doc, action):
	"""
	Return error message string if action is blocked, else None.
	action: insert | submit | print (save uses on-screen warning only; see on_credit_validate).
	"""
	if doc.flags.get("skip_credit_control"):
		return None
	if user_has_credit_bypass():
		return None
	if has_active_credit_lift(doc):
		return None

	settings = get_credit_settings()
	if not settings or not getattr(settings, "enable_credit_control", 0):
		return None

	row = _get_effective_credit_rule(settings, doc.doctype)
	if not row:
		return None

	hold, reasons = is_under_credit_hold(doc, settings)
	if not hold:
		return None

	flag_map = {
		"insert": "block_insert",
		"submit": "block_submit",
		"print": "block_print",
	}
	col = flag_map.get(action)
	if not col or not row.get(col):
		return None

	base = _("Credit control blocked this action for {0} {1}.").format(
		_(doc.doctype), doc.get("name") or ""
	)
	if reasons:
		return base + " " + " ".join(reasons)
	return base


def enforce_credit_action(doc, action):
	msg = get_credit_block_message(doc, action)
	if msg:
		frappe.throw(msg, title=_("Credit control"))


def on_credit_before_insert(doc, method=None):
	enforce_credit_action(doc, "insert")


def on_credit_validate(doc, method=None):
	if doc.is_new():
		return
	if doc.flags.get("skip_credit_control"):
		return
	if user_has_credit_bypass():
		return
	if has_active_credit_lift(doc):
		return
	settings = get_credit_settings()
	if not settings or not getattr(settings, "enable_credit_control", 0):
		return
	row = _get_effective_credit_rule(settings, doc.doctype)
	if not row or not row.get("block_save"):
		return
	hold, reasons = is_under_credit_hold(doc, settings)
	if not hold:
		return
	base = _("Credit control warning for {0} {1}.").format(_(doc.doctype), doc.get("name") or "")
	msg = base + (" " + " ".join(reasons) if reasons else "")
	frappe.msgprint(msg, title=_("Credit control"), indicator="orange", alert=True)


def on_credit_before_submit(doc, method=None):
	enforce_credit_action(doc, "submit")


_print_validation_patched = False


def _ensure_print_validation_patch():
	"""Frappe allows print if user has read OR print; patch core validator so credit runs always."""
	global _print_validation_patched
	if _print_validation_patched:
		return
	import frappe.utils.print_format as print_format_module
	import frappe.www.printview as printview_module

	_orig = printview_module.validate_print_permission

	def _validate_print_permission(doc):
		msg = get_credit_block_message(doc, "print")
		if msg:
			frappe.throw(msg, title=_("Credit control"))
		return _orig(doc)

	printview_module.validate_print_permission = _validate_print_permission
	print_format_module.validate_print_permission = _validate_print_permission
	_print_validation_patched = True


def merge_credit_hooks(doc_events):
	"""Attach credit hooks to CREDIT_SUBJECT_DOCTYPES; merge with existing string/list handlers."""
	_ensure_print_validation_patch()

	def _append(doctype, event, handler):
		cur = doc_events.setdefault(doctype, {}).get(event)
		if cur is None:
			doc_events[doctype][event] = handler
		elif isinstance(cur, list):
			if handler not in cur:
				doc_events[doctype][event] = cur + [handler]
		else:
			if cur != handler:
				doc_events[doctype][event] = [cur, handler]

	for dt in CREDIT_SUBJECT_DOCTYPES:
		_append(dt, "before_insert", "logistics.utils.credit_management.on_credit_before_insert")
		_append(dt, "validate", "logistics.utils.credit_management.on_credit_validate")
		_append(dt, "before_submit", "logistics.utils.credit_management.on_credit_before_submit")
