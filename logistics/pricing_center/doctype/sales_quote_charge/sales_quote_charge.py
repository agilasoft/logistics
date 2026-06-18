# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document

from logistics.utils.charges_calculation import compute_charge_row_estimates
from logistics.utils.freight_95_5 import validate_freight_95_5_row


class SalesQuoteCharge(Document):
	"""Sales Quote Charge child table - unified charges across Air, Sea, Transport, Customs, Warehousing."""

	def validate(self):
		validate_freight_95_5_row(self)
		self._calculate_charges()

	def _calculate_charges(self, parent_doc=None):
		"""Calculate estimated revenue and cost using centralized charges module."""
		compute_charge_row_estimates(self, parent_doc)

	def calculate_estimated_revenue(self, parent_doc=None):
		"""Calculate estimated revenue. Called by parent recalculate methods."""
		self._calculate_charges(parent_doc)

	def calculate_estimated_cost(self, parent_doc=None):
		"""Calculate estimated cost. Called by parent recalculate methods."""
		self._calculate_charges(parent_doc)
