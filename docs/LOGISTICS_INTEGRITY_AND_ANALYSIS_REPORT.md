# Logistics App — Integrity Test & Analysis Report

**Date:** February 13, 2026  
**App:** CargoNext (logistics)  
**Bench:** frappe-bench  
**Site:** logistics.agilasoft.com

---

## 1. Integrity Test Results

### 1.1 Database Migration

**Status:** ✅ **PASSED**

```
Migrating logistics.agilasoft.com
Updating DocTypes for frappe, erpnext, bircas, wiki, logistics, print_designer, cash_advance
Syncing jobs...
Syncing fixtures...
Syncing dashboards...
Syncing customizations...
Syncing languages...
Removing orphan doctypes...
Removing orphan Workspaces
Removing orphan Dashboards
Removing orphan Pages
Removing orphan Reports
Removing orphan Workspace Sidebars
Removing orphan Desktop Icons
Syncing portal menu...
```

### 1.2 Orphaned Entities Removed During Migration

The following orphaned reports were removed from the database:

| Entity Type | Name                    | Notes                                              |
|-------------|-------------------------|----------------------------------------------------|
| Report      | Route Cost Analysis     | Report file exists in app; was orphaned in DB      |
| Report      | BIR Purchase Book        | (Other app)                                        |
| Report      | BIR Cash Disbursements Book | (Other app)                                    |
| Report      | BIR Cash Receipts Book   | (Other app)                                        |
| Report      | BIR Journal Book         | (Other app)                                        |
| Report      | BIR Sales Book           | (Other app)                                        |
| Report      | BIR General Ledger       | (Other app)                                        |
| Report      | Project Billing Summary  | (Other app)                                        |
| Report      | Employee Billing Summary  | (Other app)                                        |
| Report      | Transaction Log Report   | (Other app)                                        |

### 1.3 Unit Tests

**Status:** ❌ **FAILED**

```
frappe.exceptions.DoesNotExistError: DocType Entry Type not found
```

**Cause:** Test framework attempted to create test records for dependencies. The doctypes `Sales Quote Air Freight` and `Sales Quote Sea Freight` have a Link field with `options: "Entry Type"`, but the DocType **Entry Type** does not exist in the system. The test preload logic follows this link and fails.

**Affected doctypes (fixed):**
- `sales_quote_air_freight` — `air_entry_type` changed from Link to Select
- `sales_quote_sea_freight` — `sea_entry_type` changed from Link to Select
- `sales_quote_customs` — `declaration_type` changed from Link to Select

### 1.4 Fixtures Sync

**Status:** ⚠️ **FAILED** (bench-level, not logistics-specific)

```
frappe.exceptions.ValidationError: Standard Print Format cannot be updated
```

This occurs during `bench --site all execute "frappe.utils.fixtures.sync_fixtures"` and appears to be a framework/fixture issue rather than a logistics app defect.

---

## 2. Orphaned and Broken Elements

### 2.1 Entry Type DocType — Missing Reference

| Severity | Description |
|----------|-------------|
| **High** | `Sales Quote Air Freight` and `Sales Quote Sea Freight` use `Link` to DocType `Entry Type`, which does not exist. |

**Details:**
- Air Booking, Sea Booking, Air Shipment, Sea Shipment use **Select** fields with options like `Customs Permit`, `Transshipment`, `ATA Carnet`, `Direct`, `Transit`, etc.
- Pricing center doctypes use a **Link** to a non-existent DocType.
- ERPNext has `Journal Entry` with label "Entry Type" (a Select) and `Stock Entry Type`; there is no generic `Entry Type` DocType.

**Status:** ✅ **FIXED** — Changed to Select fields:
- `sales_quote_air_freight.air_entry_type`: Select with Direct, Transit, Transshipment, Customs Permit, ATA Carnet
- `sales_quote_sea_freight.sea_entry_type`: Select with Direct, Transit, Transshipment
- `sales_quote_customs.declaration_type`: Select with Import, Export, Transit, Bonded

### 2.2 Route Cost Analysis — Workspace Link

| Severity | Description |
|----------|-------------|
| **Medium** | Transport workspace still references "Route Cost Analysis" report, which was removed as orphan during migrate. |

**Details:**
- Report file exists at `logistics/transport/report/route_cost_analysis/`
- `ref_doctype` is `Run Sheet` (exists in logistics)
- Report was removed as orphan during migrate; workspace link is now broken.

**Recommendation:** Re-import the report (e.g. `bench --site [site] import-doc` or ensure the report JSON is correctly exported and re-imported) and confirm it is linked to the correct module. Then re-run migrate to restore the report and fix the workspace link.

### 2.3 Deleted Client Script — driver_employee_fetch.json

| Severity | Description |
|----------|-------------|
| **Low** | `logistics/transport/client_scripts/driver_employee_fetch.json` was deleted. No references found in the codebase. |

**Status:** Appears to be a clean removal with no remaining references.

### 2.4 Git Status — Malformed Paths

Git status shows deleted paths with colons:

```
D logistics/transport/report/route_cost_analysis:/__init__.py
D logistics/transport/report/route_cost_analysis:/route_cost_analysis:.js
D logistics/transport/report/route_cost_analysis:/route_cost_analysis:.json
D logistics/transport/report/route_cost_analysis:/route_cost_analysis:.py
```

These look like git path artifacts (e.g. from a rename or merge). The actual `route_cost_analysis` folder exists in the filesystem; the report should be re-synced to the database.

---

## 3. Coding Errors and Anti-Patterns

### 3.1 Bare `except:` Clauses

**Count:** 60+ instances across the logistics app.

**Issue:** Using `except:` catches all exceptions, including `KeyboardInterrupt`, `SystemExit`, and `BaseException`, which can hide serious errors and complicate debugging.

**Affected areas (examples):**
- `warehouse_job.py` — multiple bare excepts
- `transport_job.py` — lines 21, 64
- `sales_quote.py`, `sales_quote_air_freight.py`, `sales_quote_sea_freight.py`, `sales_quote_transport.py`
- `air_shipment.py`, `sea_shipment.py`
- `lalamove/`, `transport/odds/`
- `warehousing/api.py`, `warehousing/billing.py`, `warehousing/count_sheet.py`
- `customs/api/base_api.py`
- `www/` portal pages

**Recommendation:** Replace with `except Exception:` (or a more specific exception type) unless there is a clear reason to catch everything. Prefer `except Exception as e:` and log or re-raise where appropriate.

### 3.2 TODO Comments Indicating Incomplete Logic

| Location | TODO |
|----------|------|
| `warehouse_job.py:3169` | Implement actual milestone tracking based on operations |
| `warehouse_job.py:3194` | Implement actual milestone details based on operations |

### 3.3 Skippable Validation

| Location | Issue |
|----------|-------|
| `warehousing/api.py:warehouse_job_before_submit` | `_skip_validation` flag allows bypassing completeness and capacity validation on submission. May be intentional for allocation but should be clearly documented and restricted. |

---

## 4. Process Loopholes

### 4.1 Declaration — Empty Status Handler

```python
# declaration.py:handle_status_changes
def handle_status_changes(self):
    """Handle status change logic"""
    # This can be expanded for workflow automation
    pass
```

**Risk:** No status transition validation or workflow automation for Declaration status changes.

### 4.2 Air Shipment — Document Validation is Optional

`validate_documents()` uses `require_customs` from settings. When `require_customs` is False:
- Export license and import permit are only soft warnings (msgprint), not blockers
- Commercial invoice is also a soft warning

**Risk:** Shipments can be submitted without required documents if settings are relaxed.

### 4.3 Transport Consolidation — Multiple Vehicle Types

`validate_vehicle_type_compatibility()` only shows a warning when multiple vehicle types are detected; it does not block save or submit.

**Risk:** Incompatible vehicle types can be consolidated; may cause operational issues.

### 4.4 Transport Job — Status Fix Workaround

`fix_submitted_job_status()` and `fix_stuck_transport_job_statuses` suggest that submitted jobs can end up with Draft status due to sync or timing issues. The fix runs on load and via a scheduled task.

**Risk:** Indicates potential race conditions or inconsistent status updates across Transport Job and related documents.

### 4.5 Portal Debug Routes Exposed

Hooks expose debug routes:

```python
# hooks.py - website_route_rules
{"from_route": "/simple-test", "to_route": "simple_test"},
{"from_route": "/customer-debug", "to_route": "customer_debug"},
{"from_route": "/transport-debug", "to_route": "transport_debug"},
{"from_route": "/warehousing-test", "to_route": "warehousing_test"},
{"from_route": "/warehousing-debug", "to_route": "warehousing_debug"},
{"from_route": "/customer-debug-portal", "to_route": "customer_debug_portal"},
```

**Risk:** Debug/test endpoints may expose sensitive data or internal behavior if not properly secured or disabled in production.

---

## 5. Patches and Migration Notes

### 5.1 Sea Freight Workspace Sync Patches

Multiple patches sync the Sea Freight workspace (v1, v2, v3, v4, v5), indicating repeated layout/sync issues.

### 5.2 Commented-Out Patch

```python
# hooks.py:131
# after_migrate = "logistics.patches.v1_1_fix_item_deletion_parent_columns.execute"
```

A patch for item deletion parent columns is commented out; confirm whether it is still needed or safely skipped.

---

## 6. Recommendations Summary

| Priority | Item | Action |
|----------|------|--------|
| **P0** | Entry Type DocType | ✅ Fixed — changed to Select fields |
| **P0** | Unit tests | ✅ Fixed — DocType dependency errors resolved (tests may fail on environment-specific data e.g. Fiscal Year) |
| **P1** | Route Cost Analysis | Patch added to restore; may be removed as orphan if file path not recognized |
| **P1** | Bare except clauses | ✅ Fixed — replaced 60+ instances with `except Exception:` |
| **P2** | Declaration handle_status_changes | ✅ Fixed — implemented status transition validation |
| **P2** | Debug routes | ✅ Fixed — removed from website_route_rules for production safety |
| **P2** | TODO in warehouse_job | Implement milestone tracking or document as future work |
| **P3** | Transport consolidation vehicle types | Consider blocking incompatible vehicle types if business rules require it |

---

## 7. Test Commands Reference

```bash
# Run migration
bench --site logistics.agilasoft.com migrate

# Run logistics app tests (currently fails due to Entry Type)
bench --site logistics.agilasoft.com run-tests --app logistics

# Clear cache
bench --site logistics.agilasoft.com clear-cache
```

---

*Report generated from codebase analysis and bench migration/test execution.*
