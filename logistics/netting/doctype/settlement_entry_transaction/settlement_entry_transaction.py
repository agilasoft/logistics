# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class SettlementEntryTransaction(Document):
	def validate(self):
		"""Validate settlement entry transaction."""
		self.validate_reference()
		self.fetch_outstanding_amount()
	
	def validate_reference(self):
		"""Validate that reference is valid."""
		if not self.reference_doctype or not self.reference_name:
			return
		
		if not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(_("Reference {0} {1} does not exist.").format(self.reference_doctype, self.reference_name))
		
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		
		# Extract party type and party from reference
		if self.reference_doctype == "Sales Invoice":
			self.party_type = "Customer"
			self.party = ref_doc.customer
			self.reference_date = ref_doc.posting_date
			self.due_date = ref_doc.due_date
		elif self.reference_doctype == "Purchase Invoice":
			self.party_type = "Supplier"
			self.party = ref_doc.supplier
			self.reference_date = ref_doc.posting_date
			self.due_date = ref_doc.due_date
		elif self.reference_doctype == "Journal Entry":
			# Extract party from journal entry accounts
			for acc in ref_doc.accounts:
				if acc.party_type in ["Customer", "Supplier"] and acc.party:
					self.party_type = acc.party_type
					self.party = acc.party
					break
			
			if not self.party_type or not self.party:
				frappe.throw(_("Journal Entry {0} must have at least one account with Customer or Supplier party.").format(self.reference_name))
			
			self.reference_date = ref_doc.posting_date
			self.due_date = ref_doc.posting_date
		else:
			frappe.throw(_("Reference DocType {0} is not supported.").format(self.reference_doctype))
	
	def fetch_outstanding_amount(self):
		"""Fetch outstanding amount from reference document."""
		if not self.reference_doctype or not self.reference_name:
			return
		
		if self.reference_doctype == "Sales Invoice":
			ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
			self.outstanding_amount = flt(ref_doc.outstanding_amount)
			self.total_amount = flt(ref_doc.grand_total)
			
			if not self.allocated_amount and self.outstanding_amount:
				self.allocated_amount = self.outstanding_amount
		
		elif self.reference_doctype == "Purchase Invoice":
			ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
			self.outstanding_amount = flt(ref_doc.outstanding_amount)
			self.total_amount = flt(ref_doc.grand_total)
			
			if not self.allocated_amount and self.outstanding_amount:
				self.allocated_amount = self.outstanding_amount
		
		elif self.reference_doctype == "Journal Entry":
			ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
			
			# Calculate net amount from journal entry
			total_debit = sum([flt(acc.debit_in_account_currency) for acc in ref_doc.accounts])
			total_credit = sum([flt(acc.credit_in_account_currency) for acc in ref_doc.accounts])
			
			# For Journal Entry, use the absolute difference as outstanding
			self.outstanding_amount = abs(total_debit - total_credit)
			self.total_amount = self.outstanding_amount
			
			if not self.allocated_amount and self.outstanding_amount:
				self.allocated_amount = self.outstanding_amount

