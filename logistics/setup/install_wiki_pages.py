# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Install or update CargoNext wiki pages for the user guide.

Run with: bench --site [site] execute logistics.setup.install_wiki_pages.install_wiki_pages

Optional arguments:
  wiki_space_route: Route of the wiki space (default: welcome)
  update_existing: If True, update existing pages; if False, skip (default: True)
"""

from __future__ import unicode_literals

import os

import frappe
from frappe import _


# Map of content file name (without .md) to (title, parent_label for sidebar)
# Organized by ERPNext structure: Getting Started, Settings, Transactions, Masters, Reports
WIKI_PAGES_CONFIG = {
    # Introduction
    "getting_started": ("Getting Started", "Introduction"),
    "document_management": ("Document Management", "Introduction"),
    "milestone_tracking": ("Milestone Tracking", "Introduction"),
    "document_list_template": ("Document List Template", "Introduction"),
    "logistics_document_type": ("Logistics Document Type", "Introduction"),
    "customer_portal": ("Customer Portal", "Introduction"),
    # Settings
    "logistics_settings": ("Logistics Settings", "Setup"),
    "sea_freight_settings": ("Sea Freight Settings", "Setup"),
    "air_freight_settings": ("Air Freight Settings", "Setup"),
    "transport_settings": ("Transport Settings", "Setup"),
    "warehouse_settings": ("Warehouse Settings", "Setup"),
    "customs_settings": ("Customs Settings", "Setup"),
    # Sea Freight
    "sea_booking": ("Sea Booking", "Sea Freight"),
    "sea_shipment": ("Sea Shipment", "Sea Freight"),
    "container_type": ("Container Type", "Sea Freight"),
    # Air Freight
    "air_booking": ("Air Booking", "Air Freight"),
    "air_shipment": ("Air Shipment", "Air Freight"),
    "uld_type": ("ULD Type", "Air Freight"),
    # Transport
    "transport_order": ("Transport Order", "Transport"),
    "transport_job": ("Transport Job", "Transport"),
    "transport_template": ("Transport Template", "Transport"),
    "load_type": ("Load Type", "Transport"),
    # Customs
    "declaration_order": ("Declaration Order", "Customs"),
    "declaration": ("Declaration", "Customs"),
    # Warehousing
    "inbound_order": ("Inbound Order", "Warehousing"),
    "release_order": ("Release Order", "Warehousing"),
    "transfer_order": ("Transfer Order", "Warehousing"),
    "vas_order": ("VAS Order", "Warehousing"),
    "stocktake_order": ("Stocktake Order", "Warehousing"),
    "warehouse_job": ("Warehouse Job", "Warehousing"),
    "warehouse_contract": ("Warehouse Contract", "Warehousing"),
    "storage_location": ("Storage Location", "Warehousing"),
    "handling_unit_type": ("Handling Unit Type", "Warehousing"),
    # Pricing Center
    "sales_quote": ("Sales Quote", "Pricing Center"),
    "one_off_quote": ("One Off Quote", "Pricing Center"),
    # Logistics (shared)
    "general_job": ("General Job", "Logistics"),
    "logistics_milestone": ("Logistics Milestone", "Logistics"),
    # Reports
    "reports_overview": ("Reports Overview", "Reports"),
}


def install_wiki_pages(wiki_space_route="welcome", update_existing=True):
    """
    Create or update CargoNext wiki pages from markdown files.

    Args:
        wiki_space_route: Route of the wiki space (e.g. 'welcome' for cargonext.io/welcome)
        update_existing: If True, update content of existing pages; if False, skip existing
    """
    if not frappe.db.exists("DocType", "Wiki Page"):
        frappe.msgprint(_("Wiki app is not installed. Please install the Wiki app first."))
        return {"success": False, "message": "Wiki app not installed"}

    wiki_content_dir = os.path.join(
        os.path.dirname(__file__), "..", "wiki_content"
    )
    if not os.path.isdir(wiki_content_dir):
        frappe.msgprint(_("Wiki content directory not found: {0}").format(wiki_content_dir))
        return {"success": False, "message": "Wiki content directory not found"}

    # Find wiki space by route
    wiki_space_name = frappe.db.get_value("Wiki Space", {"route": wiki_space_route}, "name")
    if not wiki_space_name:
        frappe.msgprint(_("Wiki Space with route '{0}' not found.").format(wiki_space_route))
        return {"success": False, "message": "Wiki space not found"}

    created = 0
    updated = 0
    skipped = 0

    for file_stem, (title, parent_label) in WIKI_PAGES_CONFIG.items():
        file_path = os.path.join(wiki_content_dir, file_stem + ".md")
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        route = f"{wiki_space_route}/{file_stem.replace('_', '-')}"
        existing = frappe.db.get_value("Wiki Page", {"route": route}, ["name", "content"], as_dict=True)

        if existing:
            if update_existing and existing.content != content:
                frappe.db.set_value("Wiki Page", existing.name, "content", content)
                frappe.db.set_value("Wiki Page", existing.name, "title", title)
                updated += 1
            else:
                skipped += 1
        else:
            wiki_page = frappe.get_doc(
                {
                    "doctype": "Wiki Page",
                    "title": title,
                    "route": route,
                    "content": content,
                    "published": 1,
                    "allow_guest": 1,
                }
            )
            wiki_page.insert(ignore_permissions=True)
            created += 1

            # Add to wiki space sidebar
            _add_to_sidebar(wiki_space_name, wiki_page.name, parent_label)

    frappe.db.commit()

    result = {
        "success": True,
        "message": _("Wiki pages: {0} created, {1} updated, {2} skipped").format(
            created, updated, skipped
        ),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }
    frappe.msgprint(result["message"])
    return result


def _add_to_sidebar(wiki_space_name, wiki_page_name, parent_label):
    """Add a wiki page to the wiki space sidebar if not already present."""
    space = frappe.get_doc("Wiki Space", wiki_space_name)
    existing = [s.wiki_page for s in space.wiki_sidebars if s.wiki_page == wiki_page_name]
    if existing:
        return

    space.append(
        "wiki_sidebars",
        {
            "wiki_page": wiki_page_name,
            "parent_label": parent_label,
        },
    )
    space.save(ignore_permissions=True)
