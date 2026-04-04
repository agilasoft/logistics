# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document

from logistics.utils.charges_calculation import (
	apply_disbursement_charge_calculation_if_applicable,
	calculate_charge_cost,
	calculate_charge_revenue,
)


class ChangeRequestCharge(Document):
	"""Aligned with Sales Quote Charge — same revenue/cost calculation pattern."""

	def validate(self):
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

	def calculate_estimated_revenue(self, parent_doc=None):
		self._calculate_charges(parent_doc)

	def calculate_estimated_cost(self, parent_doc=None):
		self._calculate_charges(parent_doc)
