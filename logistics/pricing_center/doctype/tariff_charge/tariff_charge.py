# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from logistics.utils.charges_calculation import compute_charge_row_estimates
from logistics.utils.freight_95_5 import validate_freight_95_5_row


class TariffCharge(Document):
	"""Tariff rate line — same charge grid shape as Sales Quote Charge, keyed by Service Type."""

	def validate(self):
		validate_freight_95_5_row(self)
		self._calculate_charges()

	def _calculate_charges(self, parent_doc=None):
		compute_charge_row_estimates(self, parent_doc)
