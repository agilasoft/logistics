# Logistics App — Further Improvement Suggestions (Per Module)

**Date:** February 13, 2026  
**App:** CargoNext (logistics)  
**Companion to:** [LOGISTICS_INTEGRITY_AND_ANALYSIS_REPORT.md](./LOGISTICS_INTEGRITY_AND_ANALYSIS_REPORT.md)

---

## Overview

This document suggests further improvements for the logistics app, organized by module. Items are categorized as **Technical**, **Functional**, or **Process** improvements.

---

## 1. Air Freight Module

### 1.1 Technical

| Item | Description |
|------|-------------|
| **IATA Message Builder** | `message_builder.py:346` uses `"XXX"` as fallback for missing location codes. Replace with proper validation and user-facing error instead of silent fallback. |
| **Flight Schedule Aggregators** | Add retry logic and circuit-breaker pattern for external API calls (Aviation Edge, AviationStack, OpenSky) to improve resilience. |
| **Master Air Waybill** | Consider caching frequently accessed airline/port data for performance in bulk operations. |

### 1.2 Functional

| Item | Description |
|------|-------------|
| **Document Validation** | Strengthen `validate_documents()`: when `require_customs` is False, consider making export license/import permit/commercial invoice configurable (e.g. per route or per customer) rather than always soft. |
| **Consolidation Alerts** | Add alerts for impending penalties, delay milestones, and consolidation weight/volume limits per the Sea Shipment DEV notes. |
| **e-AWB Creation** | Add validation for required fields (shipper, consignee, etc.) before e-AWB creation with clearer error messages. |
| **Dangerous Goods** | Add DG compliance alerts based on `enable_dg_compliance_alerts` in Air Freight Settings. |
| **Module Onboarding** | Consolidate duplicate onboarding configs (`air_freight.json` vs `let's_set_up_the_air_freight_module!.json`); remove duplicate/legacy steps. |

### 1.3 Process

| Item | Description |
|------|-------------|
| **Booking → Shipment Flow** | Document and enforce SLA propagation from Air Booking to Air Shipment when service level is set. |
| **Air Consolidation** | Add validation to block incompatible ULD types or weight/volume combinations in consolidation packages. |

---

## 2. Sea Freight Module

### 2.1 Technical

| Item | Description |
|------|-------------|
| **Workspace Sync** | Reduce reliance on repeated patches (v1–v5) for Sea Freight workspace; use a single migration or fixture sync. |
| **Route Cost Analysis** | Restore orphaned report and ensure workspace links are correct after migrate. |

### 2.2 Functional

| Item | Description |
|------|-------------|
| **Impending Penalties** | Implement penalty alerts per Sea Shipment DEV notes (e.g. demurrage, detention). |
| **Delay Alerts** | Implement delay alerts for milestones (ETD, ETA, ATD, ATA). |
| **Bill of Lading** | Add validation for B/L consistency with container details and routing. |
| **Sea Consolidation** | Align consolidation rules with Air Consolidation (weight/volume limits, compatibility checks). |

### 2.3 Process

| Item | Description |
|------|-------------|
| **Booking → Shipment** | Ensure SLA target date and status propagate correctly from Sea Booking to Sea Shipment. |
| **Vessel/Voyage** | Add validation for vessel and voyage number when master bill is linked. |

---

## 3. Transport Module

### 3.1 Technical

| Item | Description |
|------|-------------|
| **Capacity Manager** | Implement time slot overlap logic (`capacity_manager.py:182` TODO). |
| **Constraint Validator** | Implement distance calculation for radius check and routing integration (`constraint_validator.py` TODOs). |
| **ODD Providers** | Implement NinjaVAN, GrabExpress, PandaGo clients and mappers (currently stubs). |
| **Status Fix** | Investigate root cause of `fix_submitted_job_status` and `fix_stuck_transport_job_statuses`; address race conditions instead of patching on load. |

### 3.2 Functional

| Item | Description |
|------|-------------|
| **Vehicle Type Compatibility** | Consider blocking save/submit when `validate_vehicle_type_compatibility()` detects incompatible vehicle types in consolidation, if business rules require it. |
| **Run Sheet** | Add route optimization suggestions based on stops and vehicle capacity. |
| **Telematics** | Add dashboard for fuel consumption, trip duration, and driver performance from Remora integration. |

### 3.3 Process

| Item | Description |
|------|-------------|
| **Transport Order → Job** | Document SLA propagation and ensure job SLA target is set from Order. |
| **Portal** | Add customer-facing job status updates and ETA notifications. |

---

## 4. Warehousing Module

### 4.1 Technical

| Item | Description |
|------|-------------|
| **Milestone Tracking** | Implement actual milestone tracking based on operations (`warehouse_job.py:3169` TODO). |
| **Milestone Details** | Implement actual milestone details based on operations (`warehouse_job.py:3194` TODO). |
| **Putaway Logic** | Add unit tests for putaway rules and allocation strategies. |
| **Bare Excepts** | Replace remaining bare `except:` in `warehouse_job.py`, `warehousing/api.py`, `warehousing/billing.py`, `warehousing/count_sheet.py`. |

### 4.2 Functional

| Item | Description |
|------|-------------|
| **_skip_validation** | Document and restrict `_skip_validation` in `warehouse_job_before_submit`; add role-based access if needed. |
| **Capacity Management** | Add capacity forecasting alerts when utilization approaches thresholds. |
| **Storage Locations** | Add location overflow handling with configurable rules (e.g. nearest overflow zone). |

### 4.3 Process

| Item | Description |
|------|-------------|
| **Order → Job** | Ensure service level and due date propagate correctly from Inbound/Release/Transfer/VAS/Stocktake orders to Warehouse Job. |
| **Billing** | Add periodic billing reconciliation report for storage and VAS charges. |

---

## 5. Customs Module

### 5.1 Technical

| Item | Description |
|------|-------------|
| **API Integration** | Replace placeholder TODOs in `us_ams_api.py`, `jp_afr_api.py`, `us_isf_api.py`, `ca_emanifest_api.py` with actual API calls or mock implementations for testing. |
| **Base API** | Replace bare `except:` in `base_api.py` with specific exception handling. |

### 5.2 Functional

| Item | Description |
|------|-------------|
| **Declaration Status** | Expand `handle_status_changes()` with workflow automation (e.g. notifications, approval routing, SLA checks). |
| **Declaration from Sales Quote** | Support creation from Sales Quote (not only One-Off) when customs is required. |
| **Commodity HS Codes** | Add HS code validation and lookup against customs authority reference data. |

### 5.3 Process

| Item | Description |
|------|-------------|
| **Declaration → Shipment** | Ensure Declaration links correctly to Air/Sea Shipment and Transport Order for end-to-end tracking. |
| **Compliance Alerts** | Implement document expiry alerts per `document_expiry_alert_days` in Customs Settings. |

---

## 6. Pricing Center Module

### 6.1 Technical

| Item | Description |
|------|-------------|
| **Pricing Engine** | Extend `PricingEngine` to support Air, Sea, Customs, and Warehousing amounts (currently only Transport lanes). |
| **Rate Calculation** | Add unit tests for rate calculation mixins across all quote types. |

### 6.2 Functional

| Item | Description |
|------|-------------|
| **Quote Consolidation** | Add validation when mixing incompatible modes (e.g. FCL + LCL in same quote) in child rows. |
| **Tariff Integration** | Improve tariff lookup and application when multiple tariffs match (e.g. by agent, route, weight break). |
| **Change Request** | Add workflow for approval and propagation of change requests to linked orders. |

### 6.3 Process

| Item | Description |
|------|-------------|
| **Sales Quote → Orders** | Document and validate propagation of all charge parameters from child rows (Transport, Air, Sea, Customs, Warehousing) to respective orders. |
| **One-Off vs Contract** | Align One-Off Quote and Contract Quote design per `ONE_OFF_QUOTE_AND_CONTRACT_QUOTE_DESIGN.md`. |

---

## 7. Job Management Module

### 7.1 Technical

| Item | Description |
|------|-------------|
| **Cross-Module Links** | Ensure job costing and project links are consistent across Transport Job, Air Shipment, Sea Shipment, Warehouse Job. |

### 7.2 Functional

| Item | Description |
|------|-------------|
| **Unified Job View** | Add a dashboard or report showing all jobs (Transport, Air, Sea, Customs, Warehousing) with status and SLA. |
| **Job Costing** | Add reconciliation between Job Costing and linked Sales Invoices. |

---

## 8. Logistics (Core) Module

### 8.1 Technical

| Item | Description |
|------|-------------|
| **Shared Masters** | Ensure Shipper, Consignee, Freight Agent are consistently used across modules (no Supplier/Customer fallbacks). |
| **SLA Service Level** | Add unit tests for SLA target date calculation across modules. |

### 8.2 Functional

| Item | Description |
|------|-------------|
| **Documentation** | Add inline docs for Logistics Service Level and SLA monitoring per `SLA_SERVICE_LEVEL_DESIGN.md`. |

---

## 9. Sustainability Module

### 9.1 Functional

| Item | Description |
|------|-------------|
| **Carbon Footprint** | Integrate warehouse energy consumption and transport fuel data into carbon footprint calculations. |
| **Reporting** | Add sustainability dashboard (emissions by mode, facility, customer). |

---

## 10. Netting Module

### 10.1 Functional

| Item | Description |
|------|-------------|
| **Settlement Integration** | Ensure settlement entries correctly link to logistics invoices (Air, Sea, Transport, Warehousing). |

---

## 11. Special Projects Module

### 11.1 Functional

| Item | Description |
|------|-------------|
| **Project Integration** | Ensure Project links correctly to Air/Sea Shipment and Transport Job for special project tracking. |

---

## 12. Global Customs Module

### 12.1 Functional

| Item | Description |
|------|-------------|
| **Manifest Generation** | Add validation for required fields before generating manifests. |
| **Country-Specific** | Document US AMS, US ISF, JP AFR, CA eManifest requirements and differences. |

---

## 13. Cross-Module Improvements

| Item | Description |
|------|-------------|
| **End-to-End Tracking** | Add a unified tracking view: Sales Quote → Order(s) → Job(s) → Shipment(s) → Billing. |
| **Exception Handling** | Replace remaining bare `except:` across all modules with `except Exception as e:` and log. |
| **Unit Tests** | Add tests for critical paths: create from quote, order → job propagation, charge calculation. |
| **Fixtures Sync** | Resolve `Standard Print Format cannot be updated` fixture error (bench-level). |
| **Commented Patch** | Evaluate `v1_1_fix_item_deletion_parent_columns`; either run or remove from hooks. |

---

## 14. Priority Matrix

| Priority | Module | Item |
|----------|--------|------|
| **P0** | Customs | Replace API placeholder TODOs with real implementations or mocks |
| **P0** | Warehousing | Implement milestone tracking |
| **P1** | Transport | Fix status fix workaround root cause |
| **P1** | Pricing Center | Extend Pricing Engine for all modes |
| **P1** | All | Replace bare except clauses |
| **P2** | Air/Sea | Consolidation validation |
| **P2** | Customs | Expand handle_status_changes |
| **P2** | Job Management | Unified job view |
| **P3** | Transport | ODD providers (NinjaVAN, GrabExpress, PandaGo) |
| **P3** | Transport | Vehicle type blocking |
| **P3** | Sustainability | Carbon footprint integration |

---

*Report generated from codebase analysis and module structure review.*
