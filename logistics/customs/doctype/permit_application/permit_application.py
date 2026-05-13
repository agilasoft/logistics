# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import add_days, getdate, nowdate


class PermitApplication(Document):
	def before_insert(self):
		self._ensure_default_issuing_authority()

	def validate(self):
		"""Validate permit application data"""
		self._ensure_default_issuing_authority()
		self._validate_permit_event_dates()
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(_("Valid From date cannot be after Valid To date."))

		if self.renewal_of:
			renewal_doc = frappe.get_doc("Permit Application", self.renewal_of)
			if renewal_doc.status not in ["Approved", "Expired"]:
				frappe.throw(_("Can only renew an Approved or Expired permit."))

		self._require_filing_data_after_draft()
		# After other checks: derive status from dates (validate runs before before_save).
		self.sync_status_from_permit_triggers()
		self.apply_expired_status()
		self._require_filing_data_after_draft()

	def _validate_permit_event_dates(self):
		"""Approval / rejection dates cannot be in the future; rejection cannot precede approval."""
		today_d = getdate(nowdate())
		if self.approval_date and getdate(self.approval_date) > today_d:
			frappe.throw(
				_("Approval Date cannot be later than today."),
				title=_("Invalid Approval Date"),
			)
		if self.rejection_date and getdate(self.rejection_date) > today_d:
			frappe.throw(
				_("Rejection Date cannot be later than today."),
				title=_("Invalid Rejection Date"),
			)
		if self.approval_date and self.rejection_date:
			if getdate(self.rejection_date) < getdate(self.approval_date):
				frappe.throw(
					_("Rejection Date cannot be earlier than Approval Date."),
					title=_("Invalid Rejection Date"),
				)

	def _require_filing_data_after_draft(self):
		"""Once filed (or beyond), require dates and attachments. Draft-only edits stay relaxed."""
		if not self.get("status") or self.status == "Draft" or self.status == "Rejected":
			return
		if not self.valid_from:
			frappe.throw(_("Valid From is required."))
		if not self.valid_to:
			frappe.throw(_("Valid To is required."))
		if not any(row.get("attachment") for row in (self.attachments or [])):
			frappe.throw(_("At least one attachment is required to file a permit application."))

	def before_submit(self):
		# Frappe submit runs only on workflow "Approve" (to Approved), not the toolbar, not filing
		if self.get("status") != "Approved":
			frappe.throw(
				_("Use Workflow to file and approve. The Submit button is not used to file this form."),
				title=_("Use Workflow to Approve"),
			)

	def _ensure_default_issuing_authority(self):
		"""Default issuing authority from Permit Type if not set."""
		if self.get("issuing_authority") or not self.get("permit_type"):
			return
		try:
			permit_type_doc = frappe.get_cached_doc("Permit Type", self.permit_type)
		except frappe.DoesNotExistError:
			return
		default_authority = permit_type_doc.get("issuing_authority")
		if default_authority:
			self.issuing_authority = default_authority

	def before_save(self):
		"""Auto-update dates and status based on validity"""
		self.update_status_dates()
		self.apply_expired_status()
		self.set_default_currency()

	def sync_status_from_permit_triggers(self):
		"""
		Drive status from business dates. Renewed is kept when already renewed or set via renewal chain.
		"""
		if self.status == "Renewed":
			return
		# Rejected: rejection_date is the trigger (including Draft).
		if self.rejection_date:
			self.status = "Rejected"
			return
		# Approved: approval_date (no rejection_date) from draft or in-flight review states.
		if self.approval_date and self.status in (
			"Draft",
			"Submitted",
			"Under Review",
			"Rejected",
		):
			self.status = "Approved"

	def apply_expired_status(self):
		"""Expired when Valid To is before today (Approved permits only).

		When validity is extended so Valid To is today or later, restore Approved if the permit was approved.
		"""
		if self.status == "Renewed":
			return
		today_d = getdate(nowdate())
		if self.status == "Expired":
			if self.rejection_date:
				return
			if self.approval_date and self.valid_to and getdate(self.valid_to) >= today_d:
				self.status = "Approved"
			return
		if self.status == "Approved" and self.valid_to and getdate(self.valid_to) < today_d:
			self.status = "Expired"

	def update_status_dates(self):
		"""Backfill approval/rejection dates from status when date was not captured."""
		if self.status == "Approved" and not self.approval_date:
			self.approval_date = nowdate()
		elif self.status == "Rejected" and not self.rejection_date:
			self.rejection_date = nowdate()

	def set_default_currency(self):
		"""Set default currency from company if not set"""
		if self.company and not self.currency:
			company_doc = frappe.get_doc("Company", self.company)
			if company_doc.default_currency:
				self.currency = company_doc.default_currency

	def on_update(self):
		"""Handle status changes"""
		if self.status == "Approved" and self.permit_type:
			# Auto-set validity dates from permit type if not set
			permit_type = frappe.get_doc("Permit Type", self.permit_type)
			if permit_type.validity_period and not self.valid_to:
				if self.valid_from:
					self.valid_to = add_days(self.valid_from, permit_type.validity_period)
				elif self.approval_date:
					self.valid_from = self.approval_date
					self.valid_to = add_days(self.approval_date, permit_type.validity_period)
		self._mark_renewal_superseded()

	def _mark_renewal_superseded(self):
		"""When this renewal is Approved, mark the prior permit (renewal_of) as Renewed."""
		if self.status != "Approved" or not self.renewal_of:
			return
		previous = self.get_doc_before_save()
		if previous and previous.get("status") == "Approved":
			return
		frappe.db.set_value(
			"Permit Application",
			self.renewal_of,
			"status",
			"Renewed",
			update_modified=False,
		)


@frappe.whitelist()
def preview_permit_application_status(doc=None):
	"""Return status derived from current fields (live update on the form before/without save)."""
	if isinstance(doc, str):
		doc = frappe.parse_json(doc)
	if not isinstance(doc, dict):
		doc = {}
	name = doc.get("name")
	if name and frappe.db.exists("Permit Application", name):
		if frappe.db.get_value("Permit Application", name, "status") == "Renewed":
			return {"status": "Renewed"}
	tmp = frappe.new_doc("Permit Application")
	for fn in ("status", "approval_date", "rejection_date", "valid_to", "valid_from", "renewal_of"):
		if doc.get(fn) not in (None, ""):
			tmp.set(fn, doc.get(fn))
	tmp.sync_status_from_permit_triggers()
	tmp.apply_expired_status()
	return {"status": tmp.status}
