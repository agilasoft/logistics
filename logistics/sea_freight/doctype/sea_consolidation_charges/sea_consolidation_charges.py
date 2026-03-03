# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt

from logistics.utils.charges_calculation import (
    calculate_charge_revenue,
    calculate_charge_cost,
)


class SeaConsolidationCharges(Document):
    """Sea Consolidation Charges child table - uses centralized charge calculation. Retains Cost Allocation section."""

    def validate(self):
        self._calculate_charges()
        self._update_allocated_amount()

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

        # Total amount for consolidation metrics (revenue side)
        self.total_amount = flt(self.estimated_revenue) or 0

    def _update_allocated_amount(self):
        """Set allocated_amount from total_amount and allocation_percentage when allocation is used."""
        if not hasattr(self, "allocated_amount") or not hasattr(self, "allocation_percentage"):
            return
        pct = flt(self.allocation_percentage, 2)
        if pct > 0:
            self.allocated_amount = flt(self.total_amount or 0) * (pct / 100)

    def calculate_charge_amount(self, parent_doc=None):
        """Recalculate charge amount. Called by parent recalculate methods."""
        self._calculate_charges(parent_doc)
        self._update_allocated_amount()
