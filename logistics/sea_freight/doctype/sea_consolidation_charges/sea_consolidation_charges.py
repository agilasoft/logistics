# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt

from logistics.utils.charges_calculation import calculate_charge_cost


class SeaConsolidationCharges(Document):
    """Sea Consolidation Charges: cost-side calculation and allocation only (no revenue fields)."""

    def validate(self):
        self._calculate_charges()
        self._update_allocated_amount()

    def _calculate_charges(self, parent_doc=None):
        """Calculate estimated cost using centralized charges module."""
        cost = calculate_charge_cost(self, parent_doc)
        self.estimated_cost = cost.get("amount", 0)
        if hasattr(self, "cost_calc_notes"):
            self.cost_calc_notes = cost.get("calc_notes", "")

    def _update_allocated_amount(self):
        """Set allocated_amount from cost and allocation_percentage when allocation is used."""
        if not hasattr(self, "allocated_amount") or not hasattr(self, "allocation_percentage"):
            return
        pct = flt(self.allocation_percentage, 2)
        if pct > 0:
            base = flt(self.estimated_cost or self.buying_amount or 0)
            self.allocated_amount = base * (pct / 100)

    def calculate_charge_amount(self, parent_doc=None):
        """Recalculate charge amount. Called by parent recalculate methods."""
        self._calculate_charges(parent_doc)
        self._update_allocated_amount()
