# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from logistics.utils.charges_calculation import (
    apply_charge_type_side_cleanup,
    compute_charge_row_estimates,
)
from logistics.utils.other_services_charges_sync import validate_charge_item_not_manual_other_service
from logistics.utils.freight_95_5 import validate_freight_95_5_row


class TransportOrderCharges(Document):
    """Transport Order Charges child table - uses centralized charge calculation."""

    def validate(self):
        validate_charge_item_not_manual_other_service(self, "Transport Order Charges", "item_code")
        validate_freight_95_5_row(self)
        self._calculate_charges()

    def _calculate_charges(self, parent_doc=None):
        """Calculate estimated revenue and cost using centralized charges module."""
        apply_charge_type_side_cleanup(self)
        parent = parent_doc
        if parent is None and getattr(self, "parent", None) and getattr(self, "parenttype", None):
            try:
                parent = frappe.get_doc(self.parenttype, self.parent)
            except Exception:
                parent = None
        if parent and getattr(parent, "_internal_job_charge_overlay_applied", None):
            if hasattr(self, "total_amount"):
                self.total_amount = flt(self.estimated_revenue) or 0
            return

        compute_charge_row_estimates(self, parent_doc)

        if hasattr(self, "total_amount"):
            self.total_amount = flt(self.estimated_revenue) or 0

    def calculate_charge_amount(self, parent_doc=None):
        """Recalculate charge amount. Called by parent recalculate methods."""
        self._calculate_charges(parent_doc)
