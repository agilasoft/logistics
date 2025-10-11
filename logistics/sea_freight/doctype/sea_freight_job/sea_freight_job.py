# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document

class SeaFreightJob(Document):
    pass
    
import frappe

@frappe.whitelist()
def create_sales_invoice(booking_name, posting_date, customer, tax_category=None, invoice_type=None):
    booking = frappe.get_doc('Sea Freight Booking', booking_name)

    # Fetch naming series from the Invoice Type doctype
    naming_series = None
    if invoice_type:
        naming_series = frappe.db.get_value("Invoice Type", invoice_type, "naming_series")

    invoice = frappe.new_doc('Sales Invoice')
    invoice.customer = customer
    invoice.posting_date = posting_date
    invoice.tax_category = tax_category or None
    invoice.naming_series = naming_series or None
    invoice.invoice_type = invoice_type or None  # Optional: standard field if exists
    invoice.custom_invoice_type = invoice_type or None  # Custom field explicitly filled
    invoice.job_reference = booking_name  # Optional: link to booking

    for charge in booking.charges:
        if charge.bill_to == customer and charge.invoice_type == invoice_type:
            invoice.append('items', {
                'item_code': charge.charge_item,
                'item_name': charge.charge_name or charge.charge_item,
                'description': charge.charge_description,
                'qty': 1,
                'rate': charge.selling_amount or 0,
                'currency': charge.selling_currency,
                'item_tax_template': charge.item_tax_template or None
            })

    if not invoice.items:
        frappe.throw("No matching charges found for the selected customer and invoice type.")

    invoice.set_missing_values()
    invoice.insert(ignore_permissions=True)
    return invoice

@frappe.whitelist()
def compute_chargeable(self):
    weight = self.weight or 0
    volume = self.volume or 0

    # Use direction to determine conversion factor
    if self.direction == "Domestic":
        volume_weight = volume * 333  # Philippine domestic standard
    else:
        volume_weight = volume * 1000  # International standard

    self.chargeable = max(weight, volume_weight)
