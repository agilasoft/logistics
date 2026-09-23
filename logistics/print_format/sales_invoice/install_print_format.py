#!/usr/bin/env python3
"""
Install BIR Sales Invoice Print Format
"""
import json
import os

import frappe

PRINT_FORMAT_NAME = "Sales Invoice HTML"
FIXTURE_NAME = "BIR Sales Invoice"
DOC_TYPE = "Sales Invoice"
MODULE = "Logistics"


def _app_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def _sales_invoice_html_path():
    consolidated = os.path.join(_app_root(), "print_format", "sales_invoice", "sales_invoice.html")
    if os.path.isfile(consolidated):
        return consolidated
    return os.path.join(os.path.dirname(__file__), "sales_invoice.html")


def _disbursement_bill_html_path():
    return os.path.join(_app_root(), "print_format", "sales_invoice", "disbursement_bill.html")


def _json_path():
    return os.path.join(os.path.dirname(__file__), "sales_invoice.json")


def read_html():
    with open(_sales_invoice_html_path(), encoding="utf-8") as f:
        return f.read()


def write_fixture_json(html_content=None):
    """Write/update the standard Print Format JSON fixture from the HTML file."""
    html_content = html_content if html_content is not None else read_html()
    json_path = _json_path()
    if os.path.isfile(json_path):
        with open(json_path, encoding="utf-8") as f:
            fixture = json.load(f)
    else:
        fixture = {
            "doctype": "Print Format",
            "name": FIXTURE_NAME,
            "doc_type": DOC_TYPE,
            "module": MODULE,
            "owner": "Administrator",
            "modified_by": "Administrator",
        }
    fixture.update(
        {
            "align_labels_right": 0,
            "custom_format": 1,
            "disabled": 0,
            "doc_type": DOC_TYPE,
            "doctype": "Print Format",
            "font_size": 8,
            "html": html_content,
            "line_breaks": 0,
            "module": MODULE,
            "name": FIXTURE_NAME,
            "print_format_builder": 0,
            "print_format_type": "Jinja",
            "raw_printing": 0,
            "show_section_headings": 0,
            "standard": "Yes",
        }
    )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(fixture, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return fixture


def _set_as_default_print_format(doctype, print_format_name):
    existing = frappe.db.get_value(
        "Property Setter",
        {
            "doc_type": doctype,
            "property": "default_print_format",
            "doctype_or_field": "DocType",
        },
        "name",
    )
    if existing:
        current = frappe.db.get_value("Property Setter", existing, "value")
        if current != print_format_name:
            frappe.db.set_value("Property Setter", existing, "value", print_format_name)
            print(f"✓ Default print format for {doctype} set to {print_format_name}")
    else:
        frappe.make_property_setter(
            {
                "doctype": doctype,
                "doctype_or_field": "DocType",
                "property": "default_print_format",
                "value": print_format_name,
                "property_type": "Data",
            },
            validate_fields_for_doctype=False,
        )
        print(f"✓ Default print format for {doctype} set to {print_format_name}")
    frappe.clear_cache(doctype=doctype)


def _apply_standard_fields(print_format, html_content, standard):
    print_format.html = html_content
    print_format.doc_type = DOC_TYPE
    print_format.module = MODULE
    print_format.custom_format = 1
    print_format.print_format_type = "Jinja"
    print_format.disabled = 0
    print_format.standard = standard
    print_format.print_format_builder = 0


def _upsert_print_format(name, html_content, create_if_missing=False, standard="Yes"):
    in_install = frappe.flags.in_install
    in_import = frappe.flags.in_import
    frappe.flags.in_install = True
    frappe.flags.in_import = True
    try:
        if frappe.db.exists("Print Format", name):
            print_format = frappe.get_doc("Print Format", name)
            _apply_standard_fields(print_format, html_content, standard)
            print_format.save(ignore_permissions=True)
            print(f"✓ Updated existing {name} print format")
            return

        if not create_if_missing:
            return

        print_format = frappe.get_doc({
            "doctype": "Print Format",
            "name": name,
            "doc_type": DOC_TYPE,
            "module": MODULE,
            "standard": standard,
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
    finally:
        frappe.flags.in_install = in_install
        frappe.flags.in_import = in_import


def install_sales_invoice_print_format():
    """Install or update Sales Invoice print formats from consolidated HTML."""

    html_content = read_html()
    try:
        write_fixture_json(html_content)
    except OSError:
        # Frappe Cloud migrates from a read-only app tree. The Print Format
        # documents below are what the site needs; the fixture file is not.
        pass

    _upsert_print_format(PRINT_FORMAT_NAME, html_content, create_if_missing=True)
    _upsert_print_format(FIXTURE_NAME, html_content, create_if_missing=True)

    dsb_path = _disbursement_bill_html_path()
    if os.path.isfile(dsb_path):
        with open(dsb_path, encoding="utf-8") as f:
            dsb_html = f.read()
        _upsert_print_format("Disbursement Bill HTML", dsb_html, create_if_missing=True, standard="No")

    _set_as_default_print_format(DOC_TYPE, PRINT_FORMAT_NAME)

    frappe.db.commit()
    print("✓ Sales Invoice print format installed successfully!")
    print(f"  Use Sales Invoice > Print > {PRINT_FORMAT_NAME}")
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
