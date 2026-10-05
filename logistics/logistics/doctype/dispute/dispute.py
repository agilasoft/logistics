# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from logistics.utils.invoice_dispute import (
	ACTIVE_DISPUTE_STATUSES,
	RESOLVED_DISPUTE_STATUSES,
	get_active_dispute_for_invoice,
)

ALLOWED_REFERENCE_DOCTYPES = ("Sales Invoice", "Purchase Invoice")


class Dispute(Document):
	def validate(self):
		self.validate_invoice_reference()
		self.set_party_from_invoice()
		self.validate_single_active_dispute()
		self.sync_resolution_date()

	def validate_invoice_reference(self):
		if self.reference_doctype not in ALLOWED_REFERENCE_DOCTYPES:
			frappe.throw(_("Invoice Type must be Sales Invoice or Purchase Invoice."))

		if not self.reference_name:
			return

		if not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(
				_("{0} {1} does not exist.").format(_(self.reference_doctype), self.reference_name)
			)

		docstatus = frappe.db.get_value(self.reference_doctype, self.reference_name, "docstatus")
		if docstatus != 1:
			frappe.throw(
				_("Disputes can only be raised against submitted {0}.").format(_(self.reference_doctype))
			)

	def set_party_from_invoice(self):
		if not self.reference_doctype or not self.reference_name:
			return

		inv = frappe.db.get_value(
			self.reference_doctype,
			self.reference_name,
			["company", "customer", "supplier"],
			as_dict=True,
		)
		if not inv:
			return

		self.company = inv.company
		if self.reference_doctype == "Sales Invoice":
			self.party_type = "Customer"
			self.party = inv.customer
		else:
			self.party_type = "Supplier"
			self.party = inv.supplier

	def validate_single_active_dispute(self):
		if self.status not in ACTIVE_DISPUTE_STATUSES:
			return
		if not self.reference_doctype or not self.reference_name:
			return

		existing = get_active_dispute_for_invoice(
			self.reference_doctype,
			self.reference_name,
			exclude_name=self.name,
		)
		if existing:
			frappe.throw(
				_(
					"Invoice {0} already has an active dispute {1} ({2}). Resolve or close it before opening another."
				).format(self.reference_name, existing.name, existing.status)
			)

	def sync_resolution_date(self):
		if self.status in RESOLVED_DISPUTE_STATUSES and not self.resolution_date:
			self.resolution_date = getdate()
		if self.status in ACTIVE_DISPUTE_STATUSES:
			self.resolution_date = None
