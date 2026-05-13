# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from logistics.utils.charges_calculation import (
	apply_disbursement_charge_calculation_if_applicable,
	calculate_charge_cost,
	calculate_charge_revenue,
)
from logistics.utils.freight_95_5 import validate_freight_95_5_row


class TariffCharge(Document):
	"""Tariff rate line — same charge grid shape as Sales Quote Charge, keyed by Service Type."""

	def validate(self):
		validate_freight_95_5_row(self)
		self._calculate_charges()

	def _calculate_charges(self, parent_doc=None):
		if apply_disbursement_charge_calculation_if_applicable(self, parent_doc):
			return
		rev = calculate_charge_revenue(self, parent_doc)
		self.estimated_revenue = rev.get("amount", 0)
		if hasattr(self, "revenue_calc_notes"):
			self.revenue_calc_notes = rev.get("calc_notes", "")

		cost = calculate_charge_cost(self, parent_doc)
		self.estimated_cost = cost.get("amount", 0)
		if hasattr(self, "cost_calc_notes"):
			self.cost_calc_notes = cost.get("calc_notes", "")
