# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt

from logistics.utils.charges_calculation import (
	apply_charge_type_side_cleanup,
	compute_charge_row_estimates,
	realign_charge_row_quantities_from_parent,
)
from logistics.utils.freight_95_5 import validate_freight_95_5_row
from logistics.utils.other_services_charges_sync import validate_charge_item_not_manual_other_service


class TimeSensitiveCaseCharge(Document):
	"""Time Sensitive Case charges child table — standard operational charge schema."""

	def validate(self):
		validate_charge_item_not_manual_other_service(self, "Time Sensitive Case Charge", "item_code")
		validate_freight_95_5_row(self)
		self._calculate_charges()

	def _calculate_charges(self, parent_doc=None):
		apply_charge_type_side_cleanup(self)
		realign_charge_row_quantities_from_parent(self, parent_doc)
		compute_charge_row_estimates(self, parent_doc)

		if hasattr(self, "total_amount"):
			self.total_amount = flt(self.estimated_revenue) or 0

	def calculate_charge_amount(self, parent_doc=None):
		self._calculate_charges(parent_doc)
