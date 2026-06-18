# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from logistics.invoice_integration.container_deposit_pi import (
    get_container_deposit_pending_refund_account,
    item_is_container_deposit,
)
from logistics.utils.charges_calculation import (
    apply_charge_type_side_cleanup,
    apply_disbursement_charge_calculation_if_applicable,
    calculate_charge_revenue,
    calculate_charge_cost,
)
from logistics.utils.other_services_charges_sync import validate_charge_item_not_manual_other_service
from logistics.utils.freight_95_5 import validate_freight_95_5_row


class MICEProjectCharges(Document):
    """Exhibit Charges child table - uses centralised charge calculation.

    Used by parents: Exhibit, Docket, Exhibit Order, Exhibit Job.
    """

    def validate(self):
        validate_charge_item_not_manual_other_service(self, "MICE Project Charges", "charge_item")
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
        company = self._resolve_parent_company()
        self.container_deposit_pending_refund_gl = (
            get_container_deposit_pending_refund_account(company) or ""
        )

    def _resolve_parent_company(self):
        """Look up the parent's company, resolving Docket / Exhibit Order back to their Exhibit when blank."""
        parent = self.get("parent")
        parenttype = self.get("parenttype")
        if not parent or not parenttype:
            return None
        if parenttype == "MICE Project":
            return frappe.db.get_value("MICE Project", parent, "company")
        if parenttype == "Docket":
            company = frappe.db.get_value("Docket", parent, "company")
            if company:
                return company
            exhibit = frappe.db.get_value("Docket", parent, "exhibit")
            if exhibit:
                return frappe.db.get_value("MICE Project", exhibit, "company")
        if parenttype == "MICE Order":
            company = frappe.db.get_value("MICE Order", parent, "company")
            if company:
                return company
            exhibit = frappe.db.get_value("MICE Order", parent, "exhibit")
            if exhibit:
                return frappe.db.get_value("MICE Project", exhibit, "company")
        if parenttype == "MICE Job":
            company = frappe.db.get_value("MICE Job", parent, "company")
            if company:
                return company
            exhibit = frappe.db.get_value("MICE Job", parent, "exhibit")
            if exhibit:
                return frappe.db.get_value("MICE Project", exhibit, "company")
        return None

    def _calculate_charges(self, parent_doc=None):
        """Recalculate actual revenue and cost (basis for SI/PI). Estimated revenue/cost come from Booking."""
        apply_charge_type_side_cleanup(self)
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
