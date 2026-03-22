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
# Order follows ERPNext structure: Getting Started, Settings, Modules, Transactions, Masters, Pages, Reports, Glossary
PAGE_MAP = {
    # Introduction
    "getting_started": "Getting-Started",
    "document_management": "Document-Management",
    "milestone_tracking": "Milestone-Tracking",
    "document_list_template": "Document-List-Template",
    "logistics_document_type": "Logistics-Document-Type",
    "customer_portal": "Customer-Portal",
    "recent_platform_updates": "Recent-Platform-Updates",
    "cargonext_v1_astraea_press_release": "Cargonext-V1-Astraea-Press-Release",
    # Settings
    "logistics_settings": "Logistics-Settings",
    "sea_freight_settings": "Sea-Freight-Settings",
    "air_freight_settings": "Air-Freight-Settings",
    "transport_settings": "Transport-Settings",
    "warehouse_settings": "Warehouse-Settings",
    "customs_settings": "Customs-Settings",
    "default_details_and_relationships": "Default-Details-And-Relationships",
    # Module Intros
    "sea_freight_module": "Sea-Freight-Module",
    "air_freight_module": "Air-Freight-Module",
    "transport_module": "Transport-Module",
    "customs_module": "Customs-Module",
    "warehousing_module": "Warehousing-Module",
    # Sea Freight
    "sea_booking": "Sea-Booking",
    "sea_shipment": "Sea-Shipment",
    "sea_consolidation": "Sea-Consolidation",
    "master_bill": "Master-Bill",
    "shipper": "Shipper",
    "consignee": "Consignee",
    # Air Freight
    "air_booking": "Air-Booking",
    "air_shipment": "Air-Shipment",
    "air_consolidation": "Air-Consolidation",
    "master_air_waybill": "Master-Air-Waybill",
    # Transport
    "transport_order": "Transport-Order",
    "transport_job": "Transport-Job",
    "transport_consolidation": "Transport-Consolidation",
    "transport_leg": "Transport-Leg",
    "transport_plan": "Transport-Plan",
    "transport_order_intermodule_field_copy": "Transport-Order-Intermodule-Field-Copy",
    "run_sheet": "Run-Sheet",
    "proof_of_delivery": "Proof-of-Delivery",
    "transport_template": "Transport-Template",
    "load_type": "Load-Type",
    # Customs
    "declaration_order": "Declaration-Order",
    "declaration": "Declaration",
    "customs_workflow_guide": "Customs-Workflow-Guide",
    "commodity": "Commodity",
    "customs_authority": "Customs-Authority",
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
    "gate_pass": "Gate-Pass",
    "periodic_billing": "Periodic-Billing",
    # Pricing Center
    "sales_quote": "Sales-Quote",
    "sales_quote_separate_billings_and_internal_job": "Sales-Quote-Separate-Billings-And-Internal-Job",
    "change_request": "Change-Request",
    "sales_quote_calculation_method": "Sales-Quote-Calculation-Method",
    "charges_tariff_revenue_cost_pattern": "Charges-Tariff-Revenue-Cost-Pattern",
    # Logistics (shared masters)
    "general_job": "General-Job",
    "container_type": "Container-Type",
    # Job Management
    "job_management_module": "Job-Management-Module",
    "revenue_recognition_policy_accounts_and_dates": "Revenue-Recognition-Policy-Accounts-And-Dates",
    "proforma_gl_entries": "Proforma-Gl-Entries",
    "wip_accrual_reversal_on_invoicing_design": "Wip-Accrual-Reversal-On-Invoicing-Design",
    # Sustainability
    "sustainability_module": "Sustainability-Module",
    # Intercompany
    "intercompany_module": "Intercompany-Module",
    "internal_and_intercompany_billing": "Internal-And-Intercompany-Billing",
    # Special Projects
    "special_projects_module": "Special-Projects-Module",
    "uld_type": "ULD-Type",
    "logistics_milestone": "Logistics-Milestone",
    # Pages
    "pages_overview": "Pages-Overview",
    # Reports
    "reports_overview": "Reports-Overview",
    # Glossary
    "glossary": "Glossary",
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

    # Home.md - ERPNext style structure, aligned with workspace design
    home = """# Welcome to CargoNext

CargoNext is a comprehensive, integrated logistics management platform designed for freight forwarders, customs brokers, truckers, warehouse operators, and supply chain managers. Built on the Frappe framework, CargoNext brings all your logistics operations under one powerful system.

## Getting Started

- [Getting Started](Getting-Started) – Initial setup and configuration
- [Recent Platform Updates](Recent-Platform-Updates) – release-line behaviour and upgrade notes
- [CargoNext v1 — Astraea Press Release](Cargonext-V1-Astraea-Press-Release)
- [Document Management](Document-Management)
- [Milestone Tracking](Milestone-Tracking)
- [Customer Portal](Customer-Portal)

## Setup and Settings

- [Logistics Settings](Logistics-Settings)
- [Default Details and Relationships](Default-Details-And-Relationships) – Shipper, Consignee, Freight Agent, Carrier defaults
- [Sea Freight Settings](Sea-Freight-Settings)
- [Air Freight Settings](Air-Freight-Settings)
- [Transport Settings](Transport-Settings)
- [Warehouse Settings](Warehouse-Settings)
- [Customs Settings](Customs-Settings)

## Sea Freight

- [Sea Freight Module](Sea-Freight-Module) – Module overview and workflow
- [Sea Booking](Sea-Booking) | [Sea Shipment](Sea-Shipment) | [Sea Consolidation](Sea-Consolidation) | [Master Bill](Master-Bill)
- [Shipper](Shipper) | [Consignee](Consignee)
- [Container Type](Container-Type)

## Air Freight

- [Air Freight Module](Air-Freight-Module) – Module overview and workflow
- [Air Booking](Air-Booking) | [Air Shipment](Air-Shipment) | [Air Consolidation](Air-Consolidation) | [Master Air Waybill](Master-Air-Waybill)
- [ULD Type](ULD-Type)

## Transport

- [Transport Module](Transport-Module) – Module overview and workflow
- [Transport Order](Transport-Order) | [Transport Job](Transport-Job) | [Transport Consolidation](Transport-Consolidation)
- [Transport Leg](Transport-Leg) | [Transport Plan](Transport-Plan) | [Run Sheet](Run-Sheet)
- [Proof of Delivery](Proof-of-Delivery)
- [Transport Template](Transport-Template) | [Load Type](Load-Type)
- [Transport Order — Inter-module Field Copy](Transport-Order-Intermodule-Field-Copy)

## Customs

- [Customs Module](Customs-Module) – Module overview and workflow
- [Declaration Order](Declaration-Order) | [Declaration](Declaration)
- [Commodity](Commodity) | [Customs Authority](Customs-Authority)

## Warehousing

- [Warehousing Module](Warehousing-Module) – Module overview and workflow
- [Inbound Order](Inbound-Order) | [Release Order](Release-Order) | [Transfer Order](Transfer-Order)
- [VAS Order](VAS-Order) | [Stocktake Order](Stocktake-Order) | [Warehouse Job](Warehouse-Job)
- [Warehouse Contract](Warehouse-Contract) | [Gate Pass](Gate-Pass) | [Periodic Billing](Periodic-Billing)
- [Storage Location](Storage-Location) | [Handling Unit Type](Handling-Unit-Type)

## Pricing Center

- [Sales Quote](Sales-Quote)
- [Sales Quote — Separate Billings and Internal Job](Sales-Quote-Separate-Billings-And-Internal-Job)
- [Change Request](Change-Request)
- [Sales Quote – Calculation Method](Sales-Quote-Calculation-Method)

## Job Management

- [Job Management Module](Job-Management-Module) – Job costing, recognition policies, cost centers
- [Revenue Recognition Policy — Accounts, Dates, and Charges](Revenue-Recognition-Policy-Accounts-And-Dates)
- [Proforma GL Entries](Proforma-Gl-Entries)
- [WIP and Accrual Reversal on Invoicing](Wip-Accrual-Reversal-On-Invoicing-Design)

## Sustainability

- [Sustainability Module](Sustainability-Module) – Carbon footprint, energy consumption, environmental metrics

## Intercompany

- [Intercompany Module](Intercompany-Module) – Intercompany invoicing and reconciliation
- [Internal and Intercompany Billing](Internal-And-Intercompany-Billing) – logistics module billing rules

## Special Projects

- [Special Projects Module](Special-Projects-Module) – Complex multi-mode projects, scoping, resources, and milestone billing

## Pages (Mobile & Field)

- [Pages Overview](Pages-Overview) – Run Sheet Scan, Warehouse Job Card, Count Sheet, Plate Scanner

## Features

- [General Job](General-Job)
- [Logistics Document Type](Logistics-Document-Type)
- [Document List Template](Document-List-Template)
- [Logistics Milestone](Logistics-Milestone)

## Reports

- [Reports Overview](Reports-Overview) – All module reports

## Glossary

- [Glossary](Glossary) – Industry terms (FCL, LCL, AWB, HS Code, TEU, POD, Incoterms, etc.)

## Resources

- [Repository](https://github.com/agilasoft/logistics)
- [Documentation](https://docs.cargonext.com)
- [Website](https://www.agilasoft.com)
"""
    (out_dir / "Home.md").write_text(home, encoding="utf-8")
    print("  Home.md")

    # _sidebar.md - ERPNext style organization, aligned with workspace design
    sidebar = """- [Home](Home)

**Getting Started**
- [Getting Started](Getting-Started)
- [Recent Platform Updates](Recent-Platform-Updates)
- [CargoNext v1 — Astraea Press Release](Cargonext-V1-Astraea-Press-Release)
- [Document Management](Document-Management)
- [Milestone Tracking](Milestone-Tracking)
- [Customer Portal](Customer-Portal)

**Setup and Settings**
- [Logistics Settings](Logistics-Settings)
- [Default Details and Relationships](Default-Details-And-Relationships)
- [Sea Freight Settings](Sea-Freight-Settings)
- [Air Freight Settings](Air-Freight-Settings)
- [Transport Settings](Transport-Settings)
- [Warehouse Settings](Warehouse-Settings)
- [Customs Settings](Customs-Settings)

**Sea Freight**
- [Sea Freight Module](Sea-Freight-Module)
- [Sea Booking](Sea-Booking)
- [Sea Shipment](Sea-Shipment)
- [Sea Consolidation](Sea-Consolidation)
- [Master Bill](Master-Bill)
- [Shipper](Shipper)
- [Consignee](Consignee)
- [Container Type](Container-Type)

**Air Freight**
- [Air Freight Module](Air-Freight-Module)
- [Air Booking](Air-Booking)
- [Air Shipment](Air-Shipment)
- [Air Consolidation](Air-Consolidation)
- [Master Air Waybill](Master-Air-Waybill)
- [ULD Type](ULD-Type)

**Transport**
- [Transport Module](Transport-Module)
- [Transport Order](Transport-Order)
- [Transport Job](Transport-Job)
- [Transport Consolidation](Transport-Consolidation)
- [Transport Leg](Transport-Leg)
- [Transport Plan](Transport-Plan)
- [Run Sheet](Run-Sheet)
- [Proof of Delivery](Proof-of-Delivery)
- [Transport Template](Transport-Template)
- [Load Type](Load-Type)
- [Transport Order — Inter-module Field Copy](Transport-Order-Intermodule-Field-Copy)

**Customs**
- [Customs Module](Customs-Module)
- [Declaration Order](Declaration-Order)
- [Declaration](Declaration)
- [Commodity](Commodity)
- [Customs Authority](Customs-Authority)

**Warehousing**
- [Warehousing Module](Warehousing-Module)
- [Inbound Order](Inbound-Order)
- [Release Order](Release-Order)
- [Transfer Order](Transfer-Order)
- [VAS Order](VAS-Order)
- [Stocktake Order](Stocktake-Order)
- [Warehouse Job](Warehouse-Job)
- [Warehouse Contract](Warehouse-Contract)
- [Gate Pass](Gate-Pass)
- [Periodic Billing](Periodic-Billing)
- [Storage Location](Storage-Location)
- [Handling Unit Type](Handling-Unit-Type)

**Pricing Center**
- [Sales Quote](Sales-Quote)
- [Sales Quote — Separate Billings and Internal Job](Sales-Quote-Separate-Billings-And-Internal-Job)
- [Change Request](Change-Request)
- [Sales Quote – Calculation Method](Sales-Quote-Calculation-Method)

**Job Management**
- [Job Management Module](Job-Management-Module)
- [Revenue Recognition Policy — Accounts, Dates, and Charges](Revenue-Recognition-Policy-Accounts-And-Dates)
- [Proforma GL Entries](Proforma-Gl-Entries)
- [WIP and Accrual Reversal on Invoicing](Wip-Accrual-Reversal-On-Invoicing-Design)

**Sustainability**
- [Sustainability Module](Sustainability-Module)

**Intercompany**
- [Intercompany Module](Intercompany-Module)
- [Internal and Intercompany Billing](Internal-And-Intercompany-Billing)

**Special Projects**
- [Special Projects Module](Special-Projects-Module)

**Pages**
- [Pages Overview](Pages-Overview)

**Features**
- [General Job](General-Job)
- [Logistics Document Type](Logistics-Document-Type)
- [Document List Template](Document-List-Template)
- [Logistics Milestone](Logistics-Milestone)

**Reports**
- [Reports Overview](Reports-Overview)

**Glossary**
- [Glossary](Glossary)
"""
    (out_dir / "_sidebar.md").write_text(sidebar, encoding="utf-8")
    print("  _sidebar.md")

    print(f"\nOutput in {out_dir}/")

if __name__ == "__main__":
    main()
