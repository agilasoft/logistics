# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate


class ReleaseOrder(Document):
    pass


@frappe.whitelist()
def make_warehouse_job(source_name, target_doc=None):
    """
    Map Release Order -> Warehouse Job using get_mapped_doc.
    - Job Type: Pick
    - Reference: Release Order
    - Copies company/branch/customer when present
    - Maps child tables:
        • Release Order Item       -> Warehouse Job Order Items
        • Release Order Charges    -> Warehouse Job Charges
    """

    def set_missing_values(source, target):
        target.type = "Pick"
        target.reference_order_type = "Release Order"
        target.reference_order = source.name
        target.customer = source.customer
        # scope
        if hasattr(source, "company"):
            target.company = source.company
        if hasattr(source, "branch"):
            target.branch = source.branch
        if hasattr(source, "customer"):
            target.customer = source.customer
        # optional, if your Job has this field
        if hasattr(target, "job_open_date"):
            target.job_open_date = nowdate()

    def update_item(source_doc, target_doc, source_parent):
        # Release Order Item fields (per your DocType):
        # item, uom, quantity, serial_no, batch_no, handling_unit_type
        target_doc.item = getattr(source_doc, "item", None)
        if hasattr(source_doc, "uom"):
            target_doc.uom = source_doc.uom
        if hasattr(source_doc, "quantity"):
            target_doc.quantity = source_doc.quantity
        if hasattr(source_doc, "serial_no"):
            target_doc.serial_no = source_doc.serial_no
        if hasattr(source_doc, "batch_no"):
            target_doc.batch_no = source_doc.batch_no
        if hasattr(source_doc, "handling_unit_type"):
            target_doc.handling_unit_type = source_doc.handling_unit_type
        # Only map these if your RO Item actually has them
        if hasattr(source_doc, "handling_unit"):
            target_doc.handling_unit = source_doc.handling_unit
        if hasattr(source_doc, "location"):
            target_doc.location = source_doc.location

    def update_charge(source_doc, target_doc, source_parent):
        # Be flexible: accept charge_item or item_code
        item_code = (
            getattr(source_doc, "charge_item", None)
            or getattr(source_doc, "item_code", None)
            or getattr(source_doc, "item", None)
            or getattr(source_doc, "item_charge", None)
        )
        target_doc.item_code = item_code
        if hasattr(source_doc, "uom"):
            target_doc.uom = source_doc.uom
        if hasattr(source_doc, "quantity"):
            target_doc.quantity = source_doc.quantity
        if hasattr(source_doc, "currency"):
            target_doc.currency = source_doc.currency
        if hasattr(source_doc, "rate"):
            target_doc.rate = source_doc.rate
        if hasattr(source_doc, "total"):
            target_doc.total = source_doc.total

    doc = get_mapped_doc(
        "Release Order",
        source_name,
        {
            "Release Order": {
                "doctype": "Warehouse Job",
                "field_map": {
                    "name": "reference_order"
                },
            },
            "Release Order Item": {
                "doctype": "Warehouse Job Order Items",
                "postprocess": update_item,
            },
            "Release Order Charges": {
                "doctype": "Warehouse Job Charges",
                "postprocess": update_charge,
            },
        },
        target_doc,
        set_missing_values,
    )

    return doc
