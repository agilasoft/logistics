# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import today, flt


class VASOrder(Document):
    pass


@frappe.whitelist()
def make_warehouse_job(source_name, target_doc=None):
    """
    Map VAS Order -> Warehouse Job.

    Header mapping:
      - reference_order_type = "VAS Order"
      - reference_order       = <VAS Order name>
      - type                  = VAS Order.type (normalize "Other" -> "Others")
      - job_open_date         = VAS Order.order_date (fallback: today)
      - notes                 = "Created from VAS Order <name>"

    Child mapping:
      - VAS Order Item    -> Warehouse Job Order Items
      - VAS Order Charges -> Warehouse Job Charges
    """

    def set_missing_values(source, target):
        # Reference back to the originating VAS Order
        target.reference_order_type = "VAS Order"
        target.reference_order = source.name
        target.vas_order_type = source.type
        target.company = source.company
        target.branch = source.branch
        target.customer = source.customer
        target.warehouse_contract = source.contract

        # Type (normalize to match Warehouse Job options)
        target.type = "VAS"

        # Dates / Notes
        target.job_open_date = source.order_date or today()
        target.notes = f"Created from VAS Order {source.name}"

        # Optional: guardrail against invalid types (keeps UX friendly)
        try:
            wj_meta = frappe.get_meta("Warehouse Job")
            allowed = (wj_meta.get_field("type").options or "").split("\n")
            if allowed and src_type and src_type not in allowed:
                frappe.throw(f"Warehouse Job type '{src_type}' is not allowed. Allowed: {', '.join(allowed)}")
        except Exception:
            # Be permissive if metadata is unavailable
            pass

    def update_order_item(source_doc, target_doc, source_parent):
        """VAS Order Item -> Warehouse Job Order Items"""
        target_doc.item = getattr(source_doc, "item", None)
        target_doc.uom = getattr(source_doc, "uom", None)
        qty = getattr(source_doc, "quantity", None)
        target_doc.quantity = flt(qty) if qty else 1.0
        target_doc.handling_unit_type = getattr(source_doc, "handling_unit_type", None)
        target_doc.handling_unit = getattr(source_doc, "handling_unit", None)
        target_doc.serial_no = getattr(source_doc, "serial_no", None)
        target_doc.batch_no = getattr(source_doc, "batch_no", None)

    def update_charge(source_doc, target_doc, source_parent):
        """VAS Order Charges -> Warehouse Job Charges (best-effort field names)"""
        target_doc.item_code = (
            getattr(source_doc, "charge_item", None)
            or getattr(source_doc, "item_code", None)
            or getattr(source_doc, "item", None)
        )
        target_doc.uom = getattr(source_doc, "uom", None)
        target_doc.quantity = flt(getattr(source_doc, "quantity", 0)) or 0
        target_doc.currency = getattr(source_doc, "currency", None)
        target_doc.rate = flt(getattr(source_doc, "rate", 0)) or 0
        target_doc.total = flt(getattr(source_doc, "total", 0)) or 0

    doc = get_mapped_doc(
        "VAS Order",
        source_name,
        {
            "VAS Order": {
                "doctype": "Warehouse Job",
                "field_map": {
                    # Redundant with set_missing_values, but harmless & explicit
                    "name": "reference_order",
                },
            },
            "VAS Order Item": {
                "doctype": "Warehouse Job Order Items",
                "postprocess": update_order_item,
            },
            "VAS Order Charges": {
                "doctype": "Warehouse Job Charges",
                "postprocess": update_charge,
            },
        },
        target_doc,
        set_missing_values,
    )

    return doc
