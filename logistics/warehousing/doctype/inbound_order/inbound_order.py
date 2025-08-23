# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class InboundOrder(Document):
	pass


@frappe.whitelist()
def make_warehouse_job(source_name, target_doc=None):
    """
    Map Inbound Order -> Warehouse Job (default Type = Putaway).
    """

    def set_missing_values(source, target):
        target.type = "Putaway"   # Always Putaway for Inbound Orders
        target.job_open_date = frappe.utils.nowdate()
        target.reference_order_type = "Inbound Order"
        target.reference_order = source.name

    doc = get_mapped_doc(
        "Inbound Order",
        source_name,
        {
            "Inbound Order": {
                "doctype": "Warehouse Job",
                "field_map": {
                    # If you want to bring over fields:
                    # "customer": "customer",
                    # "contract": "contract",
                }
            },
            "Inbound Order Item": {
                "doctype": "Warehouse Job Item",
                "field_map": {
                    "item": "item",
                    "quantity": "quantity",
                    "handling_unit": "handling_unit",
                    "serial_no": "serial_no",
                    "batch_no": "batch_no",
                }
            }
        },
        target_doc,
        set_missing_values
    )

    return doc
    

@frappe.whitelist()
def allocate_existing_handling_unit(source_name, handling_unit_type, handling_unit, item_row_names):
    if not source_name or not handling_unit_type or not handling_unit or not item_row_names:
        frappe.throw("Missing required parameters.")

    if isinstance(item_row_names, str):
        item_row_names = frappe.parse_json(item_row_names)
    if not isinstance(item_row_names, (list, tuple)) or not item_row_names:
        frappe.throw("No item rows selected.")

    # Validate HU type (Handling Unit has field 'type')
    hu_type = frappe.db.get_value("Handling Unit", handling_unit, "type")
    if hu_type != handling_unit_type:
        frappe.throw(f"Handling Unit {handling_unit} is not of type {handling_unit_type}.")

    # Ensure rows belong to the parent
    rownames = frappe.get_all(
        "Inbound Order Item",
        filters={"parent": source_name, "name": ["in", item_row_names]},
        pluck="name"
    )
    if len(rownames) != len(item_row_names):
        frappe.throw("One or more selected rows do not belong to the Inbound Order.")

    # Update each child row (basic, explicit)
    updated = 0
    for rn in item_row_names:
        frappe.db.set_value("Inbound Order Item", rn, "handling_unit", handling_unit, update_modified=False)
        frappe.db.set_value("Inbound Order Item", rn, "handling_unit_type", handling_unit_type, update_modified=False)
        updated += 1

    frappe.db.commit()
    return {"handling_unit": handling_unit, "updated_count": updated}
