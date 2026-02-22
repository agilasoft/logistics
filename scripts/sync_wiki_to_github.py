#!/usr/bin/env python3
"""
Sync wiki content from logistics/wiki_content/ to GitHub Wiki format.
Converts filenames and internal links for GitHub Wiki compatibility.

Run from repo root. Output goes to wiki-output/ for copying to the wiki repo.
"""

import os
import re
from pathlib import Path

# Map source file (stem) to GitHub Wiki page name
# Order follows ERPNext structure: Getting Started, Settings, Transactions, Masters, Reports
PAGE_MAP = {
    # Introduction
    "getting_started": "Getting-Started",
    "document_management": "Document-Management",
    "milestone_tracking": "Milestone-Tracking",
    "document_list_template": "Document-List-Template",
    "logistics_document_type": "Logistics-Document-Type",
    "customer_portal": "Customer-Portal",
    # Settings
    "logistics_settings": "Logistics-Settings",
    "sea_freight_settings": "Sea-Freight-Settings",
    "air_freight_settings": "Air-Freight-Settings",
    "transport_settings": "Transport-Settings",
    "warehouse_settings": "Warehouse-Settings",
    "customs_settings": "Customs-Settings",
    # Sea Freight
    "sea_booking": "Sea-Booking",
    "sea_shipment": "Sea-Shipment",
    # Air Freight
    "air_booking": "Air-Booking",
    "air_shipment": "Air-Shipment",
    # Transport
    "transport_order": "Transport-Order",
    "transport_job": "Transport-Job",
    "transport_template": "Transport-Template",
    "load_type": "Load-Type",
    # Customs
    "declaration_order": "Declaration-Order",
    "declaration": "Declaration",
    # Warehousing
    "inbound_order": "Inbound-Order",
    "release_order": "Release-Order",
    "transfer_order": "Transfer-Order",
    "vas_order": "VAS-Order",
    "stocktake_order": "Stocktake-Order",
    "warehouse_job": "Warehouse-Job",
    "warehouse_contract": "Warehouse-Contract",
    "storage_location": "Storage-Location",
    "handling_unit_type": "Handling-Unit-Type",
    # Pricing Center
    "sales_quote": "Sales-Quote",
    "one_off_quote": "One-Off-Quote",
    # Logistics (shared masters)
    "general_job": "General-Job",
    "container_type": "Container-Type",
    "uld_type": "ULD-Type",
    "logistics_milestone": "Logistics-Milestone",
    # Reports
    "reports_overview": "Reports-Overview",
}

# Link conversion: welcome/kebab-case -> Kebab-Case (GitHub Wiki page name)
def kebab_to_title(kebab: str) -> str:
    return "-".join(w.capitalize() for w in kebab.split("-"))

def convert_links(content: str) -> str:
    """Convert (welcome/xxx-yyy) links to (Xxx-Yyy) for GitHub Wiki."""
    def replace_link(match):
        path = match.group(1)
        if "/" in path:
            path = path.split("/")[-1]  # take last part if nested
        return f"({kebab_to_title(path)})"
    return re.sub(r'\(welcome/([^)]+)\)', replace_link, content)

def main():
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "logistics" / "wiki_content"
    out_dir = repo_root / "wiki-output"
    out_dir.mkdir(exist_ok=True)

    for stem, page_name in PAGE_MAP.items():
        src = src_dir / f"{stem}.md"
        if not src.exists():
            continue
        content = src.read_text(encoding="utf-8")
        content = convert_links(content)
        (out_dir / f"{page_name}.md").write_text(content, encoding="utf-8")
        print(f"  {stem}.md -> {page_name}.md")

    # Home.md - ERPNext style structure
    home = """# Welcome to CargoNext

CargoNext is a comprehensive, integrated logistics management platform designed for freight forwarders, customs brokers, truckers, warehouse operators, and supply chain managers. Built on the Frappe framework, CargoNext brings all your logistics operations under one powerful system.

## Getting Started

- [Getting Started](Getting-Started) – Initial setup and configuration

## Setup and Settings

- [Logistics Settings](Logistics-Settings)
- [Sea Freight Settings](Sea-Freight-Settings)
- [Air Freight Settings](Air-Freight-Settings)
- [Transport Settings](Transport-Settings)
- [Warehouse Settings](Warehouse-Settings)
- [Customs Settings](Customs-Settings)

## Sea Freight

- [Sea Booking](Sea-Booking)
- [Sea Shipment](Sea-Shipment)
- [Container Type](Container-Type)

## Air Freight

- [Air Booking](Air-Booking)
- [Air Shipment](Air-Shipment)
- [ULD Type](ULD-Type)

## Transport

- [Transport Order](Transport-Order)
- [Transport Job](Transport-Job)
- [Transport Template](Transport-Template)
- [Load Type](Load-Type)

## Customs

- [Declaration Order](Declaration-Order)
- [Declaration](Declaration)

## Warehousing

- [Inbound Order](Inbound-Order)
- [Release Order](Release-Order)
- [Transfer Order](Transfer-Order)
- [VAS Order](VAS-Order)
- [Stocktake Order](Stocktake-Order)
- [Warehouse Job](Warehouse-Job)
- [Warehouse Contract](Warehouse-Contract)
- [Storage Location](Storage-Location)
- [Handling Unit Type](Handling-Unit-Type)

## Pricing Center

- [Sales Quote](Sales-Quote)
- [One Off Quote](One-Off-Quote)

## Features

- [Document Management](Document-Management)
- [Milestone Tracking](Milestone-Tracking)
- [General Job](General-Job)
- [Logistics Document Type](Logistics-Document-Type)
- [Document List Template](Document-List-Template)
- [Logistics Milestone](Logistics-Milestone)
- [Customer Portal](Customer-Portal)

## Reports

- [Reports Overview](Reports-Overview)

## Resources

- [Repository](https://github.com/agilasoft/logistics)
- [Documentation](https://docs.cargonext.com)
- [Website](https://www.agilasoft.com)
"""
    (out_dir / "Home.md").write_text(home, encoding="utf-8")
    print("  Home.md")

    # _sidebar.md - ERPNext style organization
    sidebar = """- [Home](Home)

**Getting Started**
- [Getting Started](Getting-Started)

**Setup and Settings**
- [Logistics Settings](Logistics-Settings)
- [Sea Freight Settings](Sea-Freight-Settings)
- [Air Freight Settings](Air-Freight-Settings)
- [Transport Settings](Transport-Settings)
- [Warehouse Settings](Warehouse-Settings)
- [Customs Settings](Customs-Settings)

**Sea Freight**
- [Sea Booking](Sea-Booking)
- [Sea Shipment](Sea-Shipment)
- [Container Type](Container-Type)

**Air Freight**
- [Air Booking](Air-Booking)
- [Air Shipment](Air-Shipment)
- [ULD Type](ULD-Type)

**Transport**
- [Transport Order](Transport-Order)
- [Transport Job](Transport-Job)
- [Transport Template](Transport-Template)
- [Load Type](Load-Type)

**Customs**
- [Declaration Order](Declaration-Order)
- [Declaration](Declaration)

**Warehousing**
- [Inbound Order](Inbound-Order)
- [Release Order](Release-Order)
- [Transfer Order](Transfer-Order)
- [VAS Order](VAS-Order)
- [Stocktake Order](Stocktake-Order)
- [Warehouse Job](Warehouse-Job)
- [Warehouse Contract](Warehouse-Contract)
- [Storage Location](Storage-Location)
- [Handling Unit Type](Handling-Unit-Type)

**Pricing Center**
- [Sales Quote](Sales-Quote)
- [One Off Quote](One-Off-Quote)

**Features**
- [Document Management](Document-Management)
- [Milestone Tracking](Milestone-Tracking)
- [General Job](General-Job)
- [Logistics Document Type](Logistics-Document-Type)
- [Document List Template](Document-List-Template)
- [Logistics Milestone](Logistics-Milestone)
- [Customer Portal](Customer-Portal)

**Reports**
- [Reports Overview](Reports-Overview)
"""
    (out_dir / "_sidebar.md").write_text(sidebar, encoding="utf-8")
    print("  _sidebar.md")

    print(f"\nOutput in {out_dir}/")

if __name__ == "__main__":
    main()
