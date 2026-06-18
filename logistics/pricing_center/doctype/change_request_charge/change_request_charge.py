# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document

from logistics.utils.charges_calculation import compute_charge_row_estimates


class ChangeRequestCharge(Document):
	"""Aligned with Sales Quote Charge — same revenue/cost calculation pattern."""

	def validate(self):
		self._calculate_charges()

	def _calculate_charges(self, parent_doc=None):
		compute_charge_row_estimates(self, parent_doc)

	def calculate_estimated_revenue(self, parent_doc=None):
		self._calculate_charges(parent_doc)

	def calculate_estimated_cost(self, parent_doc=None):
		self._calculate_charges(parent_doc)
