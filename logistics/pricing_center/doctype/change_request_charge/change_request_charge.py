# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document

from logistics.utils.charges_calculation import compute_charge_row_estimates


class ChangeRequestCharge(Document):
	"""Aligned with Sales Quote Charge — same revenue/cost calculation pattern."""

	def validate(self):
		self._sync_revenue_calculation_method()
		self._calculate_charges()

	def _sync_revenue_calculation_method(self):
		"""Keep ``revenue_calculation_method`` and legacy ``calculation_method`` in step.

		Sales Quote Charge stores the sell-side method on ``revenue_calculation_method``.
		Change Request Charge historically used ``calculation_method``. Both names stay
		populated so job mappers and the grid read the same value.
		"""
		revenue = (self.get("revenue_calculation_method") or "").strip()
		legacy = (self.get("calculation_method") or "").strip()
		if revenue and revenue != legacy:
			self.calculation_method = revenue
		elif legacy and not revenue:
			self.revenue_calculation_method = legacy

	def _calculate_charges(self, parent_doc=None):
		compute_charge_row_estimates(self, parent_doc)

	def calculate_estimated_revenue(self, parent_doc=None):
		self._calculate_charges(parent_doc)

	def calculate_estimated_cost(self, parent_doc=None):
		self._calculate_charges(parent_doc)
