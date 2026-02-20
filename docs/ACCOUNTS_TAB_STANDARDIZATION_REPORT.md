# Accounts Tab Standardization Report

**Date:** February 13, 2026  
**Scope:** All logistics module doctypes with financial/accounts fields  
**Purpose:** Identify misalignment and propose standardization

---

## 1. Standard Accounts Tab Definition

### 1.1 Proposed Standard Structure

For **transaction/job doctypes** (orders, bookings, shipments, jobs):

| Element | Fieldname | Type | Label | Reqd | Notes |
|---------|-----------|------|-------|------|-------|
| Tab | `accounts_tab` | Tab Break | Accounts | — | Consistent naming |
| Company | `company` | Link → Company | Company | Yes | |
| Branch | `branch` | Link → Branch | Branch | Yes | |
| Cost Center | `cost_center` | Link → Cost Center | Cost Center | Yes | `link_filters`: company + is_group=0 |
| Profit Center | `profit_center` | Link → Profit Center | Profit Center | Yes | |
| Column Break | `column_break_accounts` | Column Break | — | — | |
| Job Costing Number | `job_costing_number` | Link → Job Costing Number | Job Costing Number | No | For recognition engine |
| Project | `project` | Link → Project | Project | No | Special Projects integration |

**Field order:** `company` → `branch` → `cost_center` → `profit_center` → `column_break_accounts` → `job_costing_number` → `project`

**Cost Center link_filters (standard):**
```json
[["Cost Center","is_group","=",0],["Cost Center","company","=","eval:doc.company"]]
```

---

## 2. Current State by DocType

### 2.1 Tab/Section Naming

| DocType | Tab/Section Fieldname | Label | Status |
|---------|----------------------|-------|--------|
| Sales Quote | accounts_tab | Accounts | ✅ Standard |
| One-Off Quote | accounts_tab | Accounts | ✅ Standard |
| Air Booking | accounts_tab | Accounts | ✅ Standard |
| Air Shipment | accounts_tab | Accounts | ✅ Standard |
| Sea Booking | accounts_tab | Accounts | ✅ Standard |
| Sea Shipment | accounts_tab | Accounts | ✅ Standard |
| Air Consolidation | accounts_tab | Accounts | ✅ Standard |
| Sea Consolidation | accounts_tab | Accounts | ✅ Standard |
| Transport Consolidation | accounts_tab | Accounts | ✅ Standard |
| Warehouse Contract | accounts_tab | Accounts | ✅ Standard |
| Declaration | accounts_tab | Accounts | ✅ Standard |
| General Job | accounts_tab | Accounts | ✅ Standard |
| Exemption Certificate | accounts_tab | Accounts | ✅ Standard |
| Permit Application | accounts_tab | Accounts | ✅ Standard |
| Transport Order | accounts_tab | Accounts | ✅ Fixed |
| Inbound Order | accounts_tab | Accounts | ✅ Fixed |
| Transport Job | accounts_tab | Accounts | ✅ Fixed |
| Release Order | accounts_tab | Accounts | ✅ Fixed |
| VAS Order | accounts_tab | Accounts | ✅ Fixed |
| Transfer Order | accounts_tab | Accounts | ✅ Fixed |
| Stocktake Order | accounts_tab | Accounts | ✅ Fixed |
| Warehouse Job | accounts_tab | Accounts | ✅ Fixed |
| Declaration Order | accounts_tab | Accounts | ✅ Fixed (tab + notes_section) |

### 2.2 Accounts Fields Present

| DocType | company | branch | cost_center | profit_center | job_costing_number | project |
|---------|:-------:|:------:|:-----------:|:------------:|:------------------:|:-------:|
| Sales Quote | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| One-Off Quote | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Air Booking | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| Air Shipment | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sea Booking | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| Sea Shipment | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Air Consolidation | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Sea Consolidation | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Transport Order | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| Transport Job | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Transport Consolidation | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Inbound Order | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| Release Order | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| Transfer Order | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| VAS Order | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| Stocktake Order | ✅ | ✅ | ✅ | ✅ | ❌ | ✅* |
| Warehouse Job | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Warehouse Contract | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Declaration Order | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Declaration | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Permit Application | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Exemption Certificate | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| General Job | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

*Project in main section, not accounts tab

### 2.3 Cost Center Link Filters

| DocType | Has link_filters | Filter includes is_group |
|---------|:----------------:|:------------------------:|
| Air Shipment | ✅ | ✅ |
| Sea Shipment | ✅ | ❌ (company only) |
| Transport Order | ✅ | ✅ |
| Transport Job | ✅ | ❌ (company only) |
| Transport Consolidation | ✅ | ❌ |
| Inbound Order | ✅ | ✅ |
| Release Order | ✅ | ✅ |
| Transfer Order | ✅ | ✅ |
| VAS Order | ✅ | ✅ |
| Stocktake Order | ✅ | ✅ |
| Warehouse Job | ✅ | ✅ |
| Warehouse Contract | ✅ | ❌ |
| Declaration | ✅ | ✅ |
| Air Consolidation | ✅ | ❌ |
| Sea Consolidation | ✅ | ❌ |
| **Sales Quote** | ❌ | — |
| **One-Off Quote** | ❌ | — |
| **Air Booking** | ❌ | — |
| **Sea Booking** | ❌ | — |
| **Declaration Order** | ❌ | — |
| **General Job** | ❌ | — |
| **Permit Application** | ❌ | — |
| **Exemption Certificate** | ❌ | — |

### 2.4 Required (reqd) Flags

| DocType | company | branch | cost_center | profit_center |
|---------|:-------:|:------:|:-----------:|:------------:|
| Sea Booking | ✅ | ❌ | ❌ | ❌ |
| Declaration Order | ❌ | ❌ | ❌ | ❌ |
| Warehouse Contract | ❌ | ❌ | ❌ | ❌ |
| Transport Consolidation | ❌ | ❌ | ❌ | ❌ |
| Permit Application | ❌ | ❌ | — | — |
| Exemption Certificate | ❌ | — | — | — |
| *Most others* | ✅ | ✅ | ✅ | ✅ |

### 2.5 Field Order Inconsistency

| DocType | Order |
|---------|-------|
| General Job | company, branch, **profit_center**, **cost_center** |
| *Standard* | company, branch, cost_center, profit_center |

---

## 3. Misalignment Summary

### 3.1 Critical (P0)

| Issue | Affected DocTypes | Impact |
|-------|-------------------|--------|
| Non-standard tab fieldname | Transport Order, Inbound Order, Transport Job, Release Order, VAS Order, Transfer Order, Stocktake Order, Warehouse Job | Inconsistent code references; client scripts may break if they target `accounts_tab` |
| Declaration Order uses Section Break | Declaration Order | Accounts mixed with notes; no dedicated tab |

### 3.2 High (P1)

| Issue | Affected DocTypes | Impact |
|-------|-------------------|--------|
| Missing job_costing_number | Air Booking, Sea Booking, Transport Order, Inbound Order, Release Order, Transfer Order, VAS Order, Stocktake Order, Warehouse Contract, Declaration Order, Sales Quote, One-Off Quote | Recognition engine cannot link; job costing reports incomplete |
| Missing cost_center link_filters | Sales Quote, One-Off Quote, Air Booking, Sea Booking, Declaration Order, General Job, Permit Application, Exemption Certificate | Users can select cost centers from wrong company |
| Sea Shipment cost_center filter | Sea Shipment | Missing `is_group=0` — leaf cost centers only |

### 3.3 Medium (P2)

| Issue | Affected DocTypes | Impact |
|-------|-------------------|--------|
| Missing reqd on branch/cost_center/profit_center | Sea Booking, Declaration Order, Warehouse Contract, Transport Consolidation | Incomplete data for reporting |
| Field order (profit before cost) | General Job | Inconsistent UX |
| Permit/Exemption minimal accounts | Permit Application, Exemption Certificate | May be intentional for lightweight docs |

---

## 4. Proposed Fixes

### 4.1 Rename Tab Fieldnames to accounts_tab

| DocType | Current | Proposed |
|---------|---------|----------|
| Transport Order | tab_5_tab | accounts_tab |
| Inbound Order | tab_5_tab | accounts_tab |
| Transport Job | entity_tab | accounts_tab |
| Release Order | entity_tab | accounts_tab |
| VAS Order | entity_tab | accounts_tab |
| Transfer Order | entity_tab | accounts_tab |
| Stocktake Order | entity_tab | accounts_tab |
| Warehouse Job | transaction_entity_tab | accounts_tab |

**Note:** Renaming tab fieldnames requires a **migration patch** to update `field_order` and `fields` in the DocType JSON. A codebase search found **no Python or JS references** to these fieldnames — rename is safe from a code perspective.

### 4.2 Declaration Order — Add Proper Accounts Tab

- Add `accounts_tab` (Tab Break, label "Accounts") before `section_break_accounts`
- Move company, branch, cost_center, profit_center into accounts_tab
- Keep `section_break_accounts` for "Notes" only, or rename to `notes_section`
- Add job_costing_number, project to accounts tab (optional)

### 4.3 Add job_costing_number Where Missing

Add to: Air Booking, Sea Booking, Transport Order, Inbound Order, Release Order, Transfer Order, VAS Order, Stocktake Order, Warehouse Contract, Declaration Order.

**Exclude:** Sales Quote, One-Off Quote (quotes are pre-job; job_costing_number applies at order/job level).

### 4.4 Add cost_center link_filters

Apply standard filter to all doctypes with cost_center:
```json
[["Cost Center","is_group","=",0],["Cost Center","company","=","eval:doc.company"]]
```

**Affected:** Sales Quote, One-Off Quote, Air Booking, Sea Booking, Declaration Order, General Job, Permit Application (if cost_center added), Exemption Certificate (if cost_center added).

**Sea Shipment, Air Consolidation, Sea Consolidation, Transport Consolidation, Transport Job:** Add `is_group=0` to existing filter.

### 4.5 Standardize Field Order

- **General Job:** Change order to company, branch, cost_center, profit_center (swap cost_center and profit_center).

### 4.6 Add reqd Flags (Optional)

Consider making company, branch, cost_center, profit_center required on:
- Sea Booking
- Declaration Order (if used for billing)
- Warehouse Contract (if used for billing)
- Transport Consolidation

---

## 5. Doctypes With Non-Accounts "Entity" Tabs

The following use `entity_tab` or `transaction_entity_tab` with label "Entity" or "Transaction Entity" — these are **not** accounts tabs and should remain as-is:

| DocType | Tab | Label | Purpose |
|---------|-----|-------|---------|
| Storage Location | entity_tab | Entity | company, branch for storage scope |
| Warehouse Stock Ledger | entity_tab | Entity | company, branch for ledger |
| Handling Unit | entity_tab | Entity | company, branch for HU scope |
| Periodic Billing | entity_tab | Entity | company, branch, cost_center, etc. |
| Carbon Footprint | transaction_entity_tab | Transaction Entity | company, branch, cost_center |
| Energy Consumption | transaction_entity_tab | Transaction Entity | company, branch, cost_center |
| Gate Pass | transaction_entity_tab | Transaction Entity | company, branch |

**Recommendation:** For consistency, consider renaming these to `accounts_tab` only if they contain the full accounts field set. Otherwise keep as-is (they serve different purposes).

---

## 6. Implementation Phases

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | Rename tab fieldnames (tab_5_tab, entity_tab, transaction_entity_tab → accounts_tab) for job/order doctypes | Medium — requires patch + script references |
| **Phase 2** | Add cost_center link_filters to all doctypes missing them | Low |
| **Phase 3** | Add job_costing_number to order-level doctypes | Low |
| **Phase 4** | Declaration Order: add accounts tab, separate from notes | Low |
| **Phase 5** | Standardize field order (General Job), add reqd flags | Low |

---

## 7. Reference: Standard Accounts Tab JSON Template

```json
{
  "fieldname": "accounts_tab",
  "fieldtype": "Tab Break",
  "label": "Accounts"
},
{
  "fieldname": "company",
  "fieldtype": "Link",
  "label": "Company",
  "options": "Company",
  "reqd": 1
},
{
  "fieldname": "branch",
  "fieldtype": "Link",
  "label": "Branch",
  "options": "Branch",
  "reqd": 1
},
{
  "fieldname": "cost_center",
  "fieldtype": "Link",
  "label": "Cost Center",
  "link_filters": "[[\"Cost Center\",\"is_group\",\"=\",0],[\"Cost Center\",\"company\",\"=\",\"eval:doc.company\"]]",
  "options": "Cost Center",
  "reqd": 1
},
{
  "fieldname": "profit_center",
  "fieldtype": "Link",
  "label": "Profit Center",
  "options": "Profit Center",
  "reqd": 1
},
{
  "fieldname": "column_break_accounts",
  "fieldtype": "Column Break"
},
{
  "fieldname": "job_costing_number",
  "fieldtype": "Link",
  "label": "Job Costing Number",
  "options": "Job Costing Number",
  "description": "For revenue/cost recognition"
},
{
  "fieldname": "project",
  "fieldtype": "Link",
  "label": "Project",
  "options": "Project",
  "description": "ERPNext Project for Special Projects integration"
}
```

---

*Report generated from codebase analysis.*
