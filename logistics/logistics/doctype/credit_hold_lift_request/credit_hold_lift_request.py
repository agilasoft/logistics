# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CreditHoldLiftRequest(Document):
	def validate(self):
		self.validate_dates()
		self.validate_reference()

	def validate_dates(self):
		if self.valid_from and self.valid_to and getdate(self.valid_from) > getdate(self.valid_to):
			frappe.throw(_("Valid From cannot be after Valid To."))

	def validate_reference(self):
		if self.scope != "Single Document":
			return
		if not self.reference_name:
			frappe.throw(_("Reference is required when Scope is Single Document."))
		if not self.relieved_doctype:
			return
		if not frappe.db.exists(self.relieved_doctype, self.reference_name):
			frappe.throw(
				_("{0} {1} does not exist.").format(_(self.relieved_doctype), self.reference_name)
			)

	def before_submit(self):
		if frappe.session.user == "Administrator":
			return
		roles = frappe.get_roles()
		if "System Manager" in roles or "Credit Manager" in roles:
			return
		frappe.throw(_("Only a Credit Manager can submit this document."), title=_("Not permitted"))
