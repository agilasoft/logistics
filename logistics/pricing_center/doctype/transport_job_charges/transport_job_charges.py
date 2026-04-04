# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from logistics.utils.charges_calculation import (
    apply_disbursement_charge_calculation_if_applicable,
    calculate_charge_revenue,
    calculate_charge_cost,
)
from logistics.utils.other_services_charges_sync import validate_charge_item_not_manual_other_service


class TransportJobCharges(Document):
    """Transport Job Charges child table - uses centralized charge calculation."""

    def validate(self):
        validate_charge_item_not_manual_other_service(self, "Transport Job Charges", "item_code")
        self._calculate_charges()
        self._recalculate_total_standard_cost()

    def _calculate_charges(self, parent_doc=None):
        """Recalculate only actual revenue and cost (basis for SI/PI). Estimated revenue/cost come from Order and are not changed."""
        parent = parent_doc
        if parent is None and getattr(self, "parent", None) and getattr(self, "parenttype", None):
            try:
                parent = frappe.get_doc(self.parenttype, self.parent)
            except Exception:
                parent = None
        if apply_disbursement_charge_calculation_if_applicable(self, parent):
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
        self._recalculate_total_standard_cost()

    def _recalculate_total_standard_cost(self):
        """total_standard_cost = quantity × standard_unit_cost (uses cost_quantity if quantity is zero)."""
        if not frappe.get_meta(self.doctype).get_field("total_standard_cost"):
            return
        qty = flt(getattr(self, "quantity", 0) or 0)
        if qty <= 0:
            qty = flt(getattr(self, "cost_quantity", 0) or 0)
        standard_unit_cost = flt(getattr(self, "standard_unit_cost", 0) or 0)
        self.total_standard_cost = qty * standard_unit_cost
