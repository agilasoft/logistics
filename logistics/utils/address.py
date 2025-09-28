import frappe
from frappe.contacts.doctype.address.address import get_address_display

@frappe.whitelist()
def render_address_html(address_name: str | None = None, address: str | dict | None = None) -> str:
    """
    Return formatted HTML for an Address using ERPNext's standard template.

    Accepts either:
      - address_name: the Address.name (e.g. "Warehouse-Warehouse")
      - address: a dict or JSON string of the Address doc
    """
    # If 'address' was provided, it may be a JSON string
    if address:
        if isinstance(address, str):
            try:
                address = frappe.parse_json(address)
            except Exception:
                # If it's not JSON, treat it as a name after all
                address_name = address
                address = None

        if isinstance(address, dict):
            return get_address_display(address)

    if address_name:
        doc = frappe.get_doc("Address", address_name)
        return get_address_display(doc.as_dict())

    return ""
