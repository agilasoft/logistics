# Logistics App — Comprehensive Integrity Report

**Date:** February 13, 2026  
**App:** CargoNext (logistics)  
**Scope:** Module interconnections, ERPNext integration, reports, dashboards, per-module settings, functional inconsistencies

---

## 1. Executive Summary

| Category | Status | Critical Issues |
|----------|--------|-----------------|
| Module Interconnections | ✅ Fixed | Declaration doctype mismatch fixed |
| ERPNext Integration | ✅ Good | Uses Company, Customer, Item, Sales Invoice, Warehouse; custom Warehouse Stock Ledger |
| Reports | ⚠️ Partial | Duplicate report names fixed; Route Cost Analysis orphan risk remains |
| Dashboards | ✅ Good | 5 dashboard charts; workspaces linked |
| Per-Module Settings | ✅ Good | 16 settings doctypes across modules |
| Functional Inconsistencies | ⚠️ Several | Air/Sea parity gaps; Job Management doctype mismatch fixed |

---

## 2. Module Structure and Interconnections

### 2.1 Modules (12 total)

| Module | Workspace | Primary DocTypes | Settings |
|--------|-----------|------------------|----------|
| Logistics | — | Logistics Settings (global) | Logistics Settings |
| Transport | Transport | Transport Order, Transport Job, Run Sheet | Transport Settings, Transport Capacity Settings, ODDS Settings |
| Warehousing | Warehousing | Warehouse Job, Inbound/Release/Transfer Order | Warehouse Settings |
| Customs | Customs | Declaration, Declaration Order | Customs Settings, Manifest Settings |
| Global Customs | — | Global Manifest, US AMS, CA eManifest, JP AFR | — |
| Sea Freight | Sea Freight | Sea Booking, Sea Shipment, Sea Consolidation | Sea Freight Settings |
| Air Freight | Air Freight | Air Booking, Air Shipment, Air Consolidation | Air Freight Settings, IATA Settings, Flight Schedule Settings |
| Job Management | Job Management | Job Costing Number, Recognition Policy | Recognition Policy Settings |
| Pricing Center | Pricing | Sales Quote, One-Off Quote | — |
| Sustainability | Sustainability | Carbon Footprint, Energy Consumption | Sustainability Settings |
| Netting | — | Settlement Entry | — |
| Special Projects | Special Projects | Special Project, Special Project Request | Special Project Settings |

### 2.2 Module Integration Flow (from `module_integration.py`)

**Propagate-from-shipment flows:**
- Air Shipment → Declaration Order, Declaration, Transport Order, Transport Job, Inbound Order, Release Order, Warehouse Job
- Sea Shipment → Same targets
- Transport Job → Inbound Order, Warehouse Job
- Transport Order → Declaration, Release Order

**Create-from actions:**
- Air/Sea Shipment → Transport Order
- Air/Sea Shipment, Transport Job → Inbound Order

### 2.3 Critical Bug: Customs Declaration vs Declaration — ✅ FIXED

| Severity | **HIGH** (was) |
|----------|----------------|
| **Issue** | Job Management `doc_events` and recognition engine used doctype **"Customs Declaration"**, but the actual doctype is **"Declaration"**. |
| **Fix applied** | Replaced `"Customs Declaration"` with `"Declaration"` and `"Customs Declaration Charges"` with `"Declaration Charges"` in hooks, doc_events, recognition_engine, patches, recognition_status report, migrate_existing_jobs, sales_quote, change_request. |

---

## 3. ERPNext Core Integration

### 3.1 DocTypes Used from ERPNext

| ERPNext DocType | Usage |
|-----------------|-------|
| Company | All job/shipment doctypes; costing, billing |
| Customer | Sales Quote, Shipments, Transport, Warehouse, Declaration |
| Item | Warehouse Item, Inbound/Release Order items, VAS BOM |
| Sales Invoice | Billing from jobs; transport status validation hook |
| Address, Contact | Shipper, Consignee, facilities |
| Warehouse | Referenced in some reports; logistics uses custom Warehouse Stock Ledger |
| UOM | Measurements, packages, charges |
| Project | Special Projects; optional on Air/Sea Shipment, Transport Job |
| Branch, Cost Center, Profit Center | Financial scope on jobs |

### 3.2 Stock / Inventory

- **Logistics does NOT use ERPNext Stock Entry** for warehousing.
- Uses custom **Warehouse Stock Ledger** for putaway/pick/release movements.
- `Warehouse Item` links to ERPNext `Item` for charge items and storage types.

### 3.3 Document Hooks (from `hooks.py`)

| DocType | Event | Handler |
|---------|-------|---------|
| Report | onload | Fuel Consumption Analysis (Transport Leg) |
| Warehouse Job | before_submit, on_update | Validation; Job Management |
| Customer | after_save, on_update | Portal user permissions |
| Air Shipment, Sea Shipment, Transport Job | on_update, on_submit | Job Management (recognition) |
| **Declaration** | on_update, on_submit | Job Management (fixed) |
| General Job | on_update, on_submit | Job Management |
| Sales Invoice | validate | Transport job status validation |

---

## 4. Reports

### 4.1 Report Inventory by Module

| Module | Reports |
|--------|---------|
| Air Freight | Air Shipment Status, Air Consolidation, On-Time Performance, Dangerous Goods Compliance, Air Freight Revenue/Cost Analysis, Billing Status, Route Analysis, Airline Performance |
| Sea Freight | Sea Shipment Status, Sea Consolidation, Container Utilization, On-Time Performance, Sea Freight Revenue/Cost/Billing, Sea Freight Performance Dashboard, Route Analysis, Shipping Line Performance |
| Transport | Vehicle Utilization, On-Time Delivery, Fuel Consumption, Driver Performance, Route Cost Analysis, Consolidation Savings, Transport Cost per Job, Fleet Capacity Utilization, Road Compliance |
| Customs | Declaration Status, Manifest Status, Customs Dashboard, Global Customs Dashboard, Customs Compliance, Filing Compliance, Declaration Value |
| Warehousing | Warehouse Stock Balance, Warehouse Stock Ledger, Batch Expiry Risk, Storage Location Usage, Handling Unit Capacity, Capacity Forecasting, ABC Report, Energy Efficiency, Carbon Footprint Dashboard, Labor/Machine Productivity, Sustainability, Waste Management |
| Job Management | Recognition Status |
| Sustainability | Sustainability Metrics, Sustainability Dashboard, Carbon Footprint, Energy Consumption, Cross Module Summary, Trend Analysis, Sustainability Goals, Sustainability Compliance |

### 4.2 Duplicate Report Name: On-Time Performance Report — ✅ FIXED

| Severity | **HIGH** (was) |
|----------|----------------|
| **Issue** | Both **Air Freight** and **Sea Freight** modules defined a report named **"On-Time Performance Report"**. |
| **Fix applied** | Renamed to "Air Freight On-Time Performance Report" and "Sea Freight On-Time Performance Report". Workspace links updated. |

### 4.3 Route Cost Analysis — Orphan Risk

| Severity | **MEDIUM** |
|----------|------------|
| **Issue** | Report was removed as orphan during migrate (per prior report). Patch `v1_0_restore_route_cost_analysis_report` restores it. Transport workspace links to it. |
| **Status** | Report files exist; patch in patches.txt. If migrate runs before patch or path is wrong, report can be orphaned again. |
| **Recommendation** | Ensure report JSON path is correct; consider exporting report as fixture for reliable sync. |

### 4.4 Workspace → Report Links

All workspace report links were verified. Sustainability workspace references: Sustainability Metrics Report, Sustainability Dashboard Report, Carbon Footprint Report, Energy Consumption Report, Cross Module Summary Report, Trend Analysis Report, Sustainability Goals Report, Sustainability Compliance Report — all exist.

---

## 5. Dashboards

### 5.1 Dashboard Charts

| Chart | Module | Ref DocType |
|-------|--------|-------------|
| Booking Heatmap | Transport | — |
| Sea Freight Jobs | Sea Freight | Sea Shipment |
| Special Projects by Status | Special Projects | Special Project |
| Transport Orders Trend | Transport | Transport Order |
| Warehouse Utilization | Warehousing | — |

### 5.2 Number Cards (Workspaces)

- **Air Freight:** Open Air Shipments, Pending Consolidations, Unbilled Shipments
- **Sea Freight:** Open Jobs, Unbilled Jobs, On Hold Jobs
- **Special Projects:** Active Projects, Total Projects, Open Requests

### 5.3 Inconsistency: Air vs Sea Number Cards

- Air: "Open Air Shipments", "Unbilled Shipments"
- Sea: "Open Jobs", "Unbilled Jobs"
- Terminology differs (Shipments vs Jobs) — consider aligning for UX consistency.

---

## 6. Per-Module Settings

### 6.1 Settings DocTypes

| Settings | Module | Type |
|----------|--------|------|
| Logistics Settings | Logistics | Single |
| Transport Settings | Transport | Single |
| Transport Capacity Settings | Transport | Single |
| ODDS Settings | Transport | Single |
| Transport Settings Adhoc Factor Impact | Transport | Child of Transport Settings |
| Warehouse Settings | Warehousing | Single |
| Customs Settings | Customs | Single |
| Manifest Settings | Customs | Single |
| Sea Freight Settings | Sea Freight | Single |
| Air Freight Settings | Air Freight | Single |
| IATA Settings | Air Freight | Single |
| Flight Schedule Settings | Air Freight | Single |
| Recognition Policy Settings | Job Management | Single |
| Sustainability Settings | Sustainability | Single |
| Special Project Settings | Special Projects | Single |
| Lalamove Settings | (root) | Single |

### 6.2 Settings Dependencies

- **Logistics Settings:** Base UOMs (dimension, volume, weight), routing (OSRM, Mapbox, Google), temperature limits.
- **Transport Capacity Settings:** Vehicle type capacity, UOM conversions — required for capacity management.
- **Warehouse Settings:** Default inbound item, storage types.
- **Air/Sea Freight Settings:** Billing, document validation, customs requirements.

---

## 7. Functional Inconsistencies

### 7.1 Air vs Sea Freight Parity

| Feature | Air Freight | Sea Freight |
|---------|-------------|-------------|
| Booking → Shipment flow | ✅ | ✅ |
| Consolidation | ✅ | ✅ |
| On-Time Performance Report | ✅ (duplicate name) | ✅ (duplicate name) |
| Route Analysis Report | ✅ Route Analysis Report | ✅ Sea Freight Route Analysis |
| Performance Dashboard | ✅ Air Freight Performance Dashboard | ✅ Sea Freight Performance Dashboard |
| Billing Status Report | ✅ Billing Status Report | ✅ Sea Freight Billing Status Report |
| Cost Analysis Report | ✅ | ✅ |
| Revenue Analysis Report | ✅ | ✅ |

**Gap:** Air Freight has "Route Analysis Report"; Sea has "Sea Freight Route Analysis". Naming is inconsistent.

### 7.2 Job Management — Charges Table Mapping

| DocType | Charges Table | Child DocType |
|---------|---------------|---------------|
| Air Shipment | charges | Air Shipment Charges |
| Sea Shipment | charges | Sea Freight Charges |
| Transport Job | charges | Transport Job Charges |
| Warehouse Job | charges | Warehouse Job Charges |
| **Declaration** | charges | Declaration Charges |
| General Job | charges | General Job Charges |

Fixed: Job Management now correctly uses Declaration and Declaration Charges.

### 7.3 Transport Consolidation — Vehicle Type Validation

- `validate_vehicle_type_compatibility()` only **warns** when multiple vehicle types are detected; does not block save/submit.
- Risk: Incompatible vehicle types can be consolidated.

### 7.4 Declaration — Empty Status Handler

```python
# declaration.py
def handle_status_changes(self):
    """Handle status change logic"""
    pass  # No implementation
```

No status transition validation or workflow automation for Declaration status changes.

### 7.5 Warehousing — Skippable Validation

- `_skip_validation` flag in `warehouse_job_before_submit` allows bypassing completeness and capacity validation.
- Should be documented and restricted to allocation scenarios.

---

## 8. Patches and Migration

### 8.1 Patches (patches.txt)

- Warehousing: WSL indexes, putaway indexes, roles
- Transport: Telematics indexes, roles
- Logistics: Dimensions, master data, recognition fix, report restore, Sea Freight workspace sync (v1–v5)
- Pricing: Copy dimensions, backfill quote type
- Special Projects: Add project fields, fix chart type, remove custom fields

### 8.2 Repeated Workspace Sync

- **Sea Freight workspace** has 5 sync patches (v1–v5), indicating repeated layout/sync issues.
- **Recommendation:** Consolidate into a single migration or use fixture-based workspace sync.

### 8.3 Commented-Out Patch

```python
# hooks.py
# after_migrate = "logistics.patches.v1_1_fix_item_deletion_parent_columns.execute"
```

Confirm whether still needed or safely skipped.

---

## 9. Portal and Website Routes

### 9.1 Portal Menu Items

- Warehousing Portal, Transport Jobs, Stock Balance, Warehouse Jobs, Wiki & Documentation

### 9.2 Website Routes

- `/transport-jobs`, `/stock-balance`, `/warehouse-jobs`, `/warehousing-portal`
- Order views: release, inbound, VAS, transfer, stocktake
- Wiki routes
- Debug routes removed for production (per prior report)

---

## 10. Recommendations Summary

| Priority | Item | Action |
|----------|------|--------|
| **P0** | Customs Declaration vs Declaration | ✅ Fixed |
| **P0** | On-Time Performance Report duplicate | ✅ Fixed |
| **P1** | Route Cost Analysis | Ensure patch runs; verify report sync after migrate |
| **P2** | Declaration handle_status_changes | Implement status transition validation or document as future work |
| **P2** | Transport consolidation vehicle types | Consider blocking incompatible vehicle types if business rules require |
| **P2** | Sea Freight workspace patches | Consolidate v1–v5 into single migration |
| **P3** | Air/Sea terminology | Align "Shipments" vs "Jobs" in number cards and reports |
| **P3** | Warehousing _skip_validation | Document and restrict usage |

---

## 11. Test Commands Reference

```bash
# Run migration
bench --site [site] migrate

# Run logistics app tests
bench --site [site] run-tests --app logistics

# Clear cache
bench --site [site] clear-cache
```

---

*Report generated from codebase analysis. Supersedes and extends LOGISTICS_INTEGRITY_AND_ANALYSIS_REPORT.md.*
