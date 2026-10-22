# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Legacy Job: encode an old-system file on the existing shipment form."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint

from logistics.job_management.prior_system_posting import PRIOR_SYSTEM_POSTED_STATUS


def extend_bootinfo(bootinfo):
	"""Tell the desk whether Job Management Settings allows Legacy Jobs."""
	bootinfo.logistics_job_management_settings = {"allow_legacy_jobs": allow_legacy_jobs()}


@frappe.whitelist()
def get_allow_legacy_jobs():
	"""Return the live Allow Legacy Jobs flag so desk forms can hide the checkbox."""
	return allow_legacy_jobs()


LEGACY_JOB_DOCTYPES = (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Declaration",
	"Warehouse Job",
)

SETTINGS_DOCTYPE = "Job Management Settings"


def allow_legacy_jobs():
	"""Return whether Job Management Settings allows the Legacy Job checkbox."""
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return False
	return cint(frappe.db.get_single_value(SETTINGS_DOCTYPE, "allow_legacy_jobs"))


def is_legacy_job(doc):
	"""Return whether this document is a Legacy Job (or the older Beginning Job flag)."""
	return cint(getattr(doc, "is_legacy_job", 0)) or cint(getattr(doc, "is_beginning_job", 0))


def validate_legacy_job(doc, method=None):
	"""Keep Legacy Job and prior-system statuses on the settings path."""
	meta = getattr(doc, "meta", None)
	if meta is None or not (meta.has_field("is_legacy_job") or meta.has_field("is_beginning_job")):
		return

	current = is_legacy_job(doc)
	if meta.has_field("is_legacy_job") and meta.has_field("is_beginning_job"):
		doc.is_beginning_job = cint(doc.is_legacy_job)

	previous = 0
	if not doc.is_new() and doc.name and frappe.db.exists(doc.doctype, doc.name):
		if meta.has_field("is_legacy_job"):
			previous = cint(frappe.db.get_value(doc.doctype, doc.name, "is_legacy_job"))
		if not previous and meta.has_field("is_beginning_job"):
			previous = cint(frappe.db.get_value(doc.doctype, doc.name, "is_beginning_job"))

	if current and not previous and not allow_legacy_jobs():
		frappe.throw(
			_("Turn on Allow Legacy Jobs in Job Management Settings before marking a file as a Legacy Job."),
			title=_("Legacy Job"),
		)
	if previous and not current:
		frappe.throw(_("Legacy Job cannot be cleared."), title=_("Legacy Job"))

	if current:
		return
	for row in doc.get("charges") or []:
		for fieldname, label in (
			("sales_invoice_status", _("Revenue")),
			("purchase_invoice_status", _("Cost")),
		):
			status = (getattr(row, fieldname, None) or "").strip()
			if status == PRIOR_SYSTEM_POSTED_STATUS:
				frappe.throw(
					_("{0} posted in the prior system is only valid on a Legacy Job.").format(label),
					title=_("Legacy Job"),
				)
