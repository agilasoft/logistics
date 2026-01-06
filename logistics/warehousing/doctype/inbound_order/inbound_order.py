# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class InboundOrder(Document):
	pass


@frappe.whitelist()
def make_warehouse_job(source_name, target_doc=None):
    try:
        # Validate that contract is not cancelled before proceeding
        if source_name:
            source_doc = frappe.get_doc("Inbound Order", source_name)
            if source_doc.contract:
                contract_status = frappe.db.get_value("Warehouse Contract", source_doc.contract, "docstatus")
                if contract_status == 2:  # Cancelled
                    frappe.throw(_("Cannot create Warehouse Job from Inbound Order with cancelled contract: {0}").format(source_doc.contract))
        
        def set_missing_values(source, target):
            target.type = "Putaway"
            target.reference_order_type = "Inbound Order"
            target.reference_order = source.name
            target.company = source.company
            target.branch = source.branch
            target.customer = source.customer
            # Only set warehouse_contract if contract exists and is not cancelled
            if source.contract:
                contract_status = frappe.db.get_value("Warehouse Contract", source.contract, "docstatus")
                if contract_status != 2:  # Not cancelled
                    target.warehouse_contract = source.contract
                else:
                    frappe.throw(_("Cannot link cancelled contract: {0}").format(source.contract))
        
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
        # Log error with a short title to avoid CharacterLengthExceededError (max 140 chars for title)
        error_msg = f"Error converting Inbound Order {source_name} to Warehouse Job: {str(e)}"
        # Truncate error message if too long (keep full details in error log body)
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        frappe.log_error(error_msg, "Inbound Order to Warehouse Job Error")
        frappe.throw(_("Failed to convert order to warehouse job: {0}").format(str(e)))
