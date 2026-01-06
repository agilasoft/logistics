# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate


class TransferOrder(Document):
    pass


@frappe.whitelist()
def make_warehouse_job(source_name: str, target_doc=None):
    """
    Create a Warehouse Job (Move) from a Transfer Order.
    - Copies header + items + charges
    - Links back for traceability via reference fields
    - Items go into the 'Orders' table on Warehouse Job (your allocators read from Orders)
    """

    def set_missing_values(source, target):
        # Header defaults
        target.type = "Move"
        target.job_open_date = source.order_date or nowdate()
        target.company = source.company
        target.branch = source.branch

        # Traceability (optional but useful)
        # Even if downstream allocators read from 'orders', this helps audit.
        target.reference_order_type = "Transfer Order"
        target.reference_order = source.name
        target.customer = source.customer
        target.warehouse_contract = source.contract

        # Carry over any helpful context into notes (optional)
        blips = []
        if getattr(source, "transfer_type", None):
            blips.append(f"Transfer Type: {source.transfer_type}")
        if getattr(source, "priority", None):
            blips.append(f"Priority: {source.priority}")
        if getattr(source, "reason", None):
            blips.append(f"Reason: {source.reason}")
        if getattr(source, "cust_reference", None):
            blips.append(f"Customer Ref: {source.cust_reference}")
        if blips:
            note = " / ".join(blips)
            target.notes = (target.notes + "\n" if getattr(target, "notes", "") else "") + note

    # --- Child row mappers --------------------------------------------------
    # NOTE: We use getattr(...) to tolerate field differences gracefully.

    def update_order(source_row, target_row, source_parent):
        """
        Map Transfer Order Item  -> Warehouse Job Order Items
        Only assign if attributes exist on source_row to avoid KeyErrors.
        """
        # Common item info
        target_row.item = getattr(source_row, "item", None) or getattr(source_row, "item_code", None)
        target_row.item_name = getattr(source_row, "item_name", None)
        target_row.uom = getattr(source_row, "uom", None)
        target_row.quantity = getattr(source_row, "quantity", None)

        # Handling/packing
        target_row.handling_unit_type = getattr(source_row, "handling_unit_type", None)
        target_row.handling_unit = getattr(source_row, "handling_unit", None)

        # Tracking flags / ids (if your child schema supports them)
        for fld in ("sku_tracking", "serial_tracking", "batch_tracking"):
            if hasattr(source_row, fld):
                setattr(target_row, fld, getattr(source_row, fld))

        # Serial / Batch (text or link variants if present)
        for src_fld, dst_fld in [
            ("serial_no_text", "serial_no_text"),
            ("batch_no_text", "batch_no_text"),
            ("serial_no", "serial_no"),
            ("batch_no", "batch_no"),
        ]:
            if hasattr(source_row, src_fld):
                setattr(target_row, dst_fld, getattr(source_row, src_fld))

        # Move-specific locations (if present on your Transfer Order Item)
        for src_fld, dst_fld in [
            ("from_location", "from_location"),
            ("to_location", "to_location"),
        ]:
            if hasattr(source_row, src_fld):
                setattr(target_row, dst_fld, getattr(source_row, src_fld))

    def update_charge(source_row, target_row, source_parent):
        """
        Map Transfer Order Charges -> Warehouse Job Charges
        """
        target_row.item_code = getattr(source_row, "item_code", None) or getattr(source_row, "charge_item", None)
        target_row.uom = getattr(source_row, "uom", None)
        target_row.quantity = getattr(source_row, "quantity", None)
        target_row.currency = getattr(source_row, "currency", None)
        target_row.rate = getattr(source_row, "rate", None)
        target_row.total = getattr(source_row, "total", None)

    # --- Mapping spec -------------------------------------------------------
    doc = get_mapped_doc(
        "Transfer Order",
        source_name,
        {
            "Transfer Order": {
                "doctype": "Warehouse Job",
                "field_map": {
                    # optional direct copies if you later add similar fields
                    # "order_date": "job_open_date",
                    "name": "reference_order",  # for traceability (also set in set_missing_values)
                },
                "field_no_map": [
                    "naming_series"
                ]
            },
            "Transfer Order Item": {
                "doctype": "Warehouse Job Order Items",
                "postprocess": update_order,
            },
            "Transfer Order Charges": {
                "doctype": "Warehouse Job Charges",
                "postprocess": update_charge,
            },
        },
        target_doc,
        set_missing_values,
    )

    # Save the job before returning
    doc.save()
    frappe.db.commit()

    return doc
