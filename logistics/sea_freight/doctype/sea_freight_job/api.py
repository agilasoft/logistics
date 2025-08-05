import frappe
import re
from frappe.contacts.doctype.address.address import get_address_display

@frappe.whitelist()
def get_formatted_address(address_name):
    if not address_name:
        return "No address name provided"
    try:
        address = frappe.get_doc("Address", address_name)
        html_display = get_address_display(address.as_dict())
        plain_text = re.sub(r'<br\s*/?>', '\n', html_display or '')
        return plain_text.strip()
    except Exception as e:
        return f"Error: {str(e)}"
