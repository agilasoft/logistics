# CargoNext Wiki User Guide Setup

This document describes the wiki user guide content and installation for the CargoNext documentation at [cargonext.io/welcome](https://cargonext.io/welcome).

## Overview

The logistics app includes wiki content and an installer to populate or update the CargoNext wiki with user-focused documentation. The content follows **ERPNext documentation style**:

- **H1 heading**: DocType or feature name
- **Bold one-line definition** with introductory paragraphs
- **Navigation**: Home > Module > Page
- **Prerequisites**: Links to setup and master data
- **How to Create**: Numbered step-by-step instructions
- **Features**: Subsections for key capabilities
- **Related Topics**: Cross-links to related pages

## New Pages Added

The following pages have been added to align the wiki with current app functionality:

| Page | Module | Description |
|------|--------|-------------|
| Sea Booking | Sea Freight | Ocean freight booking/order before Sea Shipment |
| Air Booking | Air Freight | Air cargo booking/order before Air Shipment |
| Declaration Order | Customs | Customs declaration order before Declaration |
| Inbound Order | Warehousing | Warehouse receipt order |
| Release Order | Warehousing | Warehouse dispatch/release order |
| Transfer Order | Warehousing | Internal warehouse transfer |
| Document Management | Introduction | Documents tab and template system |
| Milestone Tracking | Introduction | Milestones tab and Job Milestone flow |

## Installation

### Prerequisites

- Wiki app installed on the site
- Wiki Space with route `welcome` (or your custom route)

### Run the Installer

From your bench directory:

```bash
bench --site cargonext.io execute logistics.setup.install_wiki_pages.install_wiki_pages
```

This will:

1. Create new wiki pages from the markdown files in `logistics/wiki_content/`
2. Update existing pages if content has changed
3. Add new pages to the wiki sidebar under the appropriate groups (Sea Freight, Air Freight, Customs, Warehousing, Introduction)

### Optional Parameters

```bash
# Use a different wiki space (e.g., "docs")
bench --site cargonext.io execute logistics.setup.install_wiki_pages.install_wiki_pages --kwargs '{"wiki_space_route": "docs"}'

# Only create new pages; do not update existing ones
bench --site cargonext.io execute logistics.setup.install_wiki_pages.install_wiki_pages --kwargs '{"update_existing": false}'
```

## Managing the Wiki

- **Public wiki**: https://cargonext.io/welcome
- **Admin (Desk)**: https://cargonext.io/desk/wiki
- **Wiki Settings**: Configure default space, sidebar, navbar, search
- **Wiki Pages**: Create, edit, and organize pages
- **Wiki Space**: Manage sidebar groups and page order

## Content Source

Markdown source files are in `logistics/wiki_content/`. To add or modify pages:

1. Edit the `.md` file
2. If adding a new page, register it in `WIKI_PAGES_CONFIG` in `logistics/setup/install_wiki_pages.py`
3. Run the installer again

## Alignment with App Functionality

The wiki content reflects the current CargoNext app, including:

- **Documents tab** on Air/Sea Booking, Transport Order, Declaration Order, Inbound/Release/Transfer Order, Air/Sea Shipment, Transport Job, Warehouse Job, General Job, Declaration
- **Milestones tab** on Air/Sea Shipment, Transport Job, Declaration
- **Document List Template** and **Logistics Document Type** masters
- **Job Milestone** and **Logistics Milestone** for milestone tracking
