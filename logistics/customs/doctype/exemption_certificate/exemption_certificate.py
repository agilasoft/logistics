# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, nowdate


class ExemptionCertificate(Document):
	def validate(self):
		"""Validate exemption certificate data"""
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(_("Valid From date cannot be after Valid To date."))
		
		if self.exemption_value and self.exemption_value < 0:
			frappe.throw(_("Exemption Value cannot be negative."))
		
		if self.exemption_quantity and self.exemption_quantity < 0:
			frappe.throw(_("Exemption Quantity cannot be negative."))

		self._validate_declaration_usage_rows()
		self._validate_declaration_usage_totals()

	def before_submit(self):
		if not self.valid_from:
			frappe.throw(_("Valid From is required to submit."))
		if not self.valid_to:
			frappe.throw(_("Valid To is required to submit."))
		if not any(row.get("attachment") for row in (self.attachments or [])):
			frappe.throw(_("At least one attachment is required to submit."))

	def before_save(self):
		"""Calculate remaining values and update status"""
		self._aggregate_usage_from_declarations()
		self.calculate_remaining()
		self.update_status()
		self.update_verification_date()

	def _declaration_usage_totals(self):
		"""Sum exempted value/quantity from Related Declarations child rows."""
		sum_value = 0.0
		sum_qty = 0.0
		for row in self.declarations or []:
			sum_value += flt(getattr(row, "exempted_value", None) or 0)
			sum_qty += flt(getattr(row, "exempted_quantity", None) or 0)
		return sum_value, sum_qty

	def _aggregate_usage_from_declarations(self):
		"""Roll child-row usage into parent Used Value / Used Quantity (read-only on form)."""
		sum_value, sum_qty = self._declaration_usage_totals()
		self.used_value = sum_value
		self.used_quantity = sum_qty

	def _validate_declaration_usage_rows(self):
		"""Per-row checks: non-negative amounts, at most one row per declaration."""
		seen_declarations = set()
		for row in self.declarations or []:
			decl = getattr(row, "declaration", None)
			if not decl:
				continue
			ev = flt(getattr(row, "exempted_value", None) or 0)
			eq = flt(getattr(row, "exempted_quantity", None) or 0)
			if ev < 0:
				frappe.throw(
					_("Exempted Value cannot be negative (row {0}).").format(row.idx),
					title=_("Exemption Certificate"),
				)
			if eq < 0:
				frappe.throw(
					_("Exempted Quantity cannot be negative (row {0}).").format(row.idx),
					title=_("Exemption Certificate"),
				)
			if decl in seen_declarations:
				frappe.throw(
					_("Declaration {0} is linked more than once. Use a single row per declaration.").format(decl),
					title=_("Exemption Certificate"),
				)
			seen_declarations.add(decl)

	def _validate_declaration_usage_totals(self):
		"""Ensure summed usage does not exceed certificate limits."""
		sum_value, sum_qty = self._declaration_usage_totals()
		limit_v = flt(self.exemption_value or 0)
		limit_q = flt(self.exemption_quantity or 0)
		if limit_v and sum_value > limit_v:
			frappe.throw(
				_("Total exempted value ({0}) exceeds exemption value ({1}).").format(sum_value, limit_v),
				title=_("Exemption Certificate"),
			)
		if limit_q and sum_qty > limit_q:
			frappe.throw(
				_("Total exempted quantity ({0}) exceeds exemption quantity ({1}).").format(sum_qty, limit_q),
				title=_("Exemption Certificate"),
			)
	
	def calculate_remaining(self):
		"""Calculate remaining value and quantity"""
		exemption_value = flt(self.exemption_value or 0)
		exemption_quantity = flt(self.exemption_quantity or 0)
		used_value = flt(self.used_value or 0)
		used_quantity = flt(self.used_quantity or 0)
		
		self.remaining_value = exemption_value - used_value
		self.remaining_quantity = exemption_quantity - used_quantity
		
		# Ensure remaining values are not negative
		if self.remaining_value < 0:
			self.remaining_value = 0
		if self.remaining_quantity < 0:
			self.remaining_quantity = 0
	
	def update_status(self):
		"""Update status based on validity and remaining values"""
		if self.status == "Active":
			# Check if expired
			if self.valid_to and getdate(self.valid_to) < getdate(nowdate()):
				self.status = "Expired"
			# Check if fully used
			elif self.exemption_value and self.remaining_value <= 0:
				if self.exemption_quantity and self.remaining_quantity <= 0:
					self.status = "Expired"
	
	def update_verification_date(self):
		"""Update verification date when verified"""
		if self.verification_status == "Verified" and not self.verification_date:
			self.verification_date = nowdate()
			if not self.verified_by:
				self.verified_by = frappe.session.user

