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
    Release Order -> Warehouse Job
      - Job Type: Pick
      - Reference: Release Order
      - Child mappings:
          • Release Order Item    -> Warehouse Job Order Items   (parentfield: orders)
          • Release Order Charges -> Warehouse Job Charges       (parentfield: table_dxtc)
          • Release Order Dock    -> Warehouse Job Dock          (parentfield: docks)
    """

    def _get(obj, field, default=None):
        return getattr(obj, field, default)

    def set_missing_values(source, target):
        target.type = "Pick"
        target.reference_order_type = "Release Order"
        target.reference_order = source.name
        target.customer = _get(source, "customer")
        target.warehouse_contract = _get(source, "contract")

        if hasattr(source, "company"):
            target.company = source.company
        if hasattr(source, "branch"):
            target.branch = source.branch
        if hasattr(target, "job_open_date"):
            target.job_open_date = nowdate()

    def update_item(src, tgt, src_parent):
        tgt.item = _get(src, "item")
        tgt.uom = _get(src, "uom")
        tgt.quantity = _get(src, "quantity")
        tgt.serial_no = _get(src, "serial_no")
        tgt.batch_no = _get(src, "batch_no")
        tgt.handling_unit_type = _get(src, "handling_unit_type")
        # optional passthroughs if present on RO Item
        hu = _get(src, "handling_unit")
        if hu:
            tgt.handling_unit = hu
        loc = _get(src, "location")
        if loc:
            tgt.location = loc

    def update_charge(src, tgt, src_parent):
        item_code = (
            _get(src, "charge_item")
            or _get(src, "item_code")
            or _get(src, "item")
            or _get(src, "item_charge")
        )
        if item_code:
            tgt.item_code = item_code
        tgt.uom = _get(src, "uom")
        tgt.quantity = _get(src, "quantity")
        tgt.currency = _get(src, "currency")
        tgt.rate = _get(src, "rate")
        tgt.total = _get(src, "total")

    def update_dock(src, tgt, src_parent):
        tgt.dock_door = _get(src, "dock_door")
        tgt.eta = _get(src, "eta")
        tgt.transport_company = _get(src, "transport_company")
        tgt.vehicle_type = _get(src, "vehicle_type")
        tgt.plate_no = _get(src, "plate_no")

    doc = get_mapped_doc(
        "Release Order",
        source_name,
        {
            "Release Order": {
                "doctype": "Warehouse Job",
                "field_map": {"name": "reference_order"},
                "field_no_map": [
                    "naming_series"
                ]
            },
            "Release Order Item": {
                "doctype": "Warehouse Job Order Items",
                # ensure items go into Warehouse Job's 'orders' table field
                "field_map": {"parentfield": "orders"},
                "postprocess": update_item,
            },
            "Release Order Charges": {
                "doctype": "Warehouse Job Charges",
                # ensure charges go into 'table_dxtc' table field
                "field_map": {"parentfield": "charges"},
                "postprocess": update_charge,
            },
            "Release Order Dock": {
                "doctype": "Warehouse Job Dock",
                # ensure docks go into 'docks' table field
                "field_map": {"parentfield": "docks"},
                "postprocess": update_dock,
            },
        },
        target_doc,
        set_missing_values,
    )

    # Save the job before returning
    doc.save()
    frappe.db.commit()

    return doc
