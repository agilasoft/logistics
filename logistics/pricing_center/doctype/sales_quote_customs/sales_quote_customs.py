# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from logistics.utils.charges_calculation import (
	calculate_charge_revenue,
	calculate_charge_cost,
)


class SalesQuoteCustoms(Document):
	"""Sales Quote Customs charge line (aligned with Declaration Charges)."""

	def validate(self):
		self._calculate_charges()

	def _calculate_charges(self, parent_doc=None):
		"""Calculate estimated revenue and cost using centralized charges module."""
		rev = calculate_charge_revenue(self, parent_doc)
		self.estimated_revenue = rev.get("amount", 0)
		if hasattr(self, "revenue_calc_notes"):
			self.revenue_calc_notes = rev.get("calc_notes", "")
		elif hasattr(self, "calculation_notes"):
			self.calculation_notes = rev.get("calc_notes", "")

		cost = calculate_charge_cost(self, parent_doc)
		self.estimated_cost = cost.get("amount", 0)
		if hasattr(self, "cost_calc_notes"):
			self.cost_calc_notes = cost.get("calc_notes", "")
		elif hasattr(self, "calculation_notes") and not rev.get("calc_notes"):
			self.calculation_notes = cost.get("calc_notes", "")

	def calculate_estimated_revenue(self, parent_doc=None):
		"""Calculate estimated revenue. Called by parent recalculate methods."""
		self._calculate_charges(parent_doc)

	def calculate_estimated_cost(self, parent_doc=None):
		"""Calculate estimated cost. Called by parent recalculate methods."""
		self._calculate_charges(parent_doc)

	def calculate_charge_amount(self, parent_doc=None):
		"""Recalculate charge amount. Called by parent recalculate methods."""
		self._calculate_charges(parent_doc)
