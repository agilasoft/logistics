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
PAGE_MAP = {
    "sea_booking": "Sea-Booking",
    "air_booking": "Air-Booking",
    "declaration_order": "Declaration-Order",
    "inbound_order": "Inbound-Order",
    "release_order": "Release-Order",
    "transfer_order": "Transfer-Order",
    "document_management": "Document-Management",
    "milestone_tracking": "Milestone-Tracking",
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

    # Home.md
    home = """# Welcome to CargoNext

CargoNext is a comprehensive, integrated logistics management platform designed for freight forwarders, customs brokers, truckers, warehouse operators, and supply chain managers. Built on the Frappe framework, CargoNext brings all your logistics operations under one powerful system.

## User Guide

### Sea Freight
- [Sea Booking](Sea-Booking)

### Air Freight
- [Air Booking](Air-Booking)

### Customs
- [Declaration Order](Declaration-Order)

### Warehousing
- [Inbound Order](Inbound-Order)
- [Release Order](Release-Order)
- [Transfer Order](Transfer-Order)

### Features
- [Document Management](Document-Management)
- [Milestone Tracking](Milestone-Tracking)

## Resources

- [Repository](https://github.com/agilasoft/logistics)
- [Documentation](https://docs.cargonext.com)
- [Website](https://www.agilasoft.com)
"""
    (out_dir / "Home.md").write_text(home, encoding="utf-8")
    print("  Home.md")

    # _sidebar.md
    sidebar = """- [Home](Home)

**Sea Freight**
- [Sea Booking](Sea-Booking)

**Air Freight**
- [Air Booking](Air-Booking)

**Customs**
- [Declaration Order](Declaration-Order)

**Warehousing**
- [Inbound Order](Inbound-Order)
- [Release Order](Release-Order)
- [Transfer Order](Transfer-Order)

**Features**
- [Document Management](Document-Management)
- [Milestone Tracking](Milestone-Tracking)
"""
    (out_dir / "_sidebar.md").write_text(sidebar, encoding="utf-8")
    print("  _sidebar.md")

    print(f"\nOutput in {out_dir}/")

if __name__ == "__main__":
    main()
