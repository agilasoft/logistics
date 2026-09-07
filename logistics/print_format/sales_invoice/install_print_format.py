#!/usr/bin/env python3
"""
Install BIR Sales Invoice Print Format
"""
import frappe
import os

def _app_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def _sales_invoice_html_path():
    consolidated = os.path.join(_app_root(), "print_format", "sales_invoice", "sales_invoice.html")
    if os.path.isfile(consolidated):
        return consolidated
    return os.path.join(os.path.dirname(__file__), "sales_invoice.html")


def _disbursement_bill_html_path():
    return os.path.join(_app_root(), "print_format", "sales_invoice", "disbursement_bill.html")


def _upsert_print_format(name, html_content, create_if_missing=False):
    if frappe.db.exists("Print Format", name):
        print_format = frappe.get_doc("Print Format", name)
        print_format.html = html_content
        print_format.save()
        print(f"✓ Updated existing {name} print format")
        return

    if not create_if_missing:
        return

    print_format = frappe.get_doc({
        "doctype": "Print Format",
        "name": name,
        "doc_type": "Sales Invoice",
        "module": "Logistics",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "Jinja",
        "html": html_content,
        "font_size": 8,
        "disabled": 0,
        "align_labels_right": 0,
        "line_breaks": 0,
        "print_format_builder": 0,
        "raw_printing": 0,
        "show_section_headings": 0,
    })
    print_format.insert(ignore_permissions=True)
    print(f"✓ Created new {name} print format")


def install_sales_invoice_print_format():
    """Install or update Sales Invoice print formats from consolidated HTML."""

    with open(_sales_invoice_html_path(), "r", encoding="utf-8") as f:
        html_content = f.read()

    _upsert_print_format("Sales Invoice HTML", html_content)
    _upsert_print_format("BIR Sales Invoice", html_content, create_if_missing=True)

    dsb_path = _disbursement_bill_html_path()
    if os.path.isfile(dsb_path):
        with open(dsb_path, "r", encoding="utf-8") as f:
            dsb_html = f.read()
        _upsert_print_format("Disbursement Bill HTML", dsb_html, create_if_missing=True)

    frappe.db.commit()
    print("✓ Sales Invoice print format installed successfully!")
    print("  Use Sales Invoice > Print > Sales Invoice HTML")
    print("  Use Sales Invoice > Print > Disbursement Bill HTML")

if __name__ == "__main__":
    import sys
    site = sys.argv[1] if len(sys.argv) > 1 else None
    if site:
        frappe.init(site=site)
        frappe.connect()
        install_sales_invoice_print_format()
    else:
        print("Please provide a site name as argument")


