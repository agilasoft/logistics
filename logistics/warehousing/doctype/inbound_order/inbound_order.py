# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class InboundOrder(Document):
	pass


@frappe.whitelist()
def make_warehouse_job(source_name, target_doc=None):
    try:
        def set_missing_values(source, target):
            target.type = "Putaway"
            target.reference_order_type = "Inbound Order"
            target.reference_order = source.name
            target.company = source.company
            target.branch = source.branch
            target.customer = source.customer
            target.warehouse_contract = source.contract
        
        def update_item(source_doc, target_doc, source_parent):
            target_doc.item = source_doc.item
            target_doc.uom = source_doc.uom
            target_doc.quantity = source_doc.quantity
            target_doc.handling_unit_type = source_doc.handling_unit_type
            target_doc.handling_unit = source_doc.handling_unit
            target_doc.serial_no = source_doc.serial_no
            target_doc.batch_no = source_doc.batch_no

        def update_charge(source_doc, target_doc, source_parent):
            target_doc.item_code = source_doc.item_code
            target_doc.uom = source_doc.uom
            target_doc.quantity = source_doc.quantity
            target_doc.currency = source_doc.currency
            target_doc.rate = source_doc.rate
            target_doc.total = source_doc.total

        def update_dock(source_doc, target_doc, source_parent):
            target_doc.dock_door = source_doc.dock_door
            target_doc.eta = source_doc.eta
            target_doc.transport_company = source_doc.transport_company
            target_doc.vehicle_type = source_doc.vehicle_type
            target_doc.plate_no = source_doc.plate_no

        doc = get_mapped_doc(
            "Inbound Order",
            source_name,
            {
                "Inbound Order": {
                    "doctype": "Warehouse Job",
                    "field_map": {
                        "name": "reference_order"
                    },
                    "field_no_map": [
                        "naming_series"
                    ]
                },
                "Inbound Order Item": {
                    "doctype": "Warehouse Job Order Items",
                    "postprocess": update_item
                },
                "Inbound Order Charges": {
                    "doctype": "Warehouse Job Charges",
                    "postprocess": update_charge
                },
                "Inbound Order Dock": {
                    "doctype": "Warehouse Job Dock",
                    "postprocess": update_dock
                },
            },
            target_doc,
            set_missing_values
        )
        
        # Save the job before returning
        doc.save()
        frappe.db.commit()
        
        return doc
        
    except Exception as e:
        frappe.log_error(f"Error converting Inbound Order {source_name} to Warehouse Job: {str(e)}")
        frappe.throw(f"Failed to convert order to warehouse job: {str(e)}")
