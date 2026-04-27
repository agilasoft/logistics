# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt

from logistics.invoice_integration.container_deposit_pi import (
	get_container_deposit_pending_refund_account,
	item_is_container_deposit,
)
from logistics.utils.charges_calculation import (
    apply_disbursement_charge_calculation_if_applicable,
    calculate_charge_revenue,
    calculate_charge_cost,
)
from logistics.utils.other_services_charges_sync import validate_charge_item_not_manual_other_service
from logistics.utils.freight_95_5 import validate_freight_95_5_row


class SeaShipmentCharges(Document):
    """Sea Shipment Charges (Sea Shipment) child table - uses centralized charge calculation."""

    def validate(self):
        validate_charge_item_not_manual_other_service(self, "Sea Shipment Charges", "charge_item")
        validate_freight_95_5_row(self)
        self._set_container_deposit_pending_refund_gl_display()
        self._calculate_charges()

    def _set_container_deposit_pending_refund_gl_display(self):
        if not frappe.get_meta(self.doctype).get_field("container_deposit_pending_refund_gl"):
            return
        item = self.get("item_code")
        if not item or not item_is_container_deposit(item):
            self.container_deposit_pending_refund_gl = ""
            return
        self.container_deposit_pending_refund_gl = get_container_deposit_pending_refund_account() or ""

    def _calculate_charges(self, parent_doc=None):
        """Recalculate only actual revenue and cost (basis for SI/PI). Estimated revenue/cost come from Booking and are not changed."""
        if apply_disbursement_charge_calculation_if_applicable(self, parent_doc):
            if hasattr(self, "total_amount"):
                self.total_amount = flt(self.estimated_revenue) or 0
            return
        rev = calculate_charge_revenue(self, parent_doc)
        cost = calculate_charge_cost(self, parent_doc)
        if hasattr(self, "actual_revenue"):
            self.actual_revenue = flt(rev.get("amount", 0))
        if hasattr(self, "actual_cost"):
            self.actual_cost = flt(cost.get("amount", 0))
        if hasattr(self, "revenue_calc_notes"):
            self.revenue_calc_notes = rev.get("calc_notes", "")
        elif hasattr(self, "calculation_notes"):
            self.calculation_notes = rev.get("calc_notes", "")
        if hasattr(self, "cost_calc_notes"):
            self.cost_calc_notes = cost.get("calc_notes", "")
        elif hasattr(self, "calculation_notes") and not rev.get("calc_notes"):
            self.calculation_notes = cost.get("calc_notes", "")
        if hasattr(self, "total_amount"):
            self.total_amount = flt(self.estimated_revenue) or 0

    def calculate_charge_amount(self, parent_doc=None):
        """Recalculate charge amount. Called by parent recalculate methods."""
        self._calculate_charges(parent_doc)
