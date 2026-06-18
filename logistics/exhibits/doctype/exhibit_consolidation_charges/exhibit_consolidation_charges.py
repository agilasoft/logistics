# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


_ALLOWED_CHARGE_TYPES = frozenset({"Margin", "Disbursement", "Revenue", "Cost"})


class ExhibitConsolidationCharges(Document):
	"""Exhibit Consolidation Charges child table.

	Cost-allocation focused charges line for the parent ``Exhibit`` doctype, modeled after
	``Air Consolidation Charges`` / ``Sea Consolidation Charges``. Amounts are recomputed on
	every save and the ``allocated_amount`` is derived from ``total_amount`` × ``allocation_percentage``.
	The actual allocation across targets (Dockets / Exhibit Jobs) is computed by the parent
	``Exhibit`` document via ``allocate_costs``.
	"""

	def validate(self):
		self.validate_charge_data()
		self.calculate_charge_amount()
		self.calculate_allocated_amount()
		self.update_charge_status()

	def validate_charge_data(self):
		if not self.charge_type:
			frappe.throw(_("Charge type is required"))
		if self.charge_type not in _ALLOWED_CHARGE_TYPES:
			frappe.throw(
				_("Charge type must be one of: {0}.").format(", ".join(sorted(_ALLOWED_CHARGE_TYPES))),
				title=_("Invalid charge type"),
			)
		if not self.revenue_calculation_method:
			frappe.throw(_("Revenue calculation method is required"))
		if not self.rate or flt(self.rate) <= 0:
			frappe.throw(_("Rate must be greater than 0"))
		if not self.currency:
			frappe.throw(_("Currency is required"))

	def calculate_charge_amount(self):
		"""Recalculate base amount, discount amount and total amount from rate, quantity and method."""
		rate = flt(self.rate)
		qty = flt(self.quantity)

		if self.revenue_calculation_method == "Per Unit":
			self.base_amount = rate * qty
		elif self.revenue_calculation_method == "Flat Rate":
			self.base_amount = rate
		elif self.revenue_calculation_method == "Percentage":
			self.base_amount = rate * (qty * 0.01) if qty else 0
		else:
			self.base_amount = flt(self.base_amount)

		base = flt(self.base_amount)
		if self.discount_percentage and base:
			self.discount_amount = base * (flt(self.discount_percentage) / 100.0)
		else:
			self.discount_amount = 0

		self.total_amount = (
			flt(self.base_amount)
			- flt(self.discount_amount)
			+ flt(self.surcharge_amount)
		)

	def calculate_allocated_amount(self):
		"""Row-level allocated amount from total × allocation %; parent fills the per-target table."""
		pct = flt(self.allocation_percentage)
		if pct > 0:
			self.allocated_amount = flt(self.total_amount) * (pct / 100.0)
		else:
			self.allocated_amount = 0

	def update_charge_status(self):
		if not self.charge_status or self.charge_status == "Draft":
			if flt(self.total_amount) > 0:
				self.charge_status = "Calculated"
