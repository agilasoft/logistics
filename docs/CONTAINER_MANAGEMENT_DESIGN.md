# Container Management Feature – Design Document

## 1. Overview

This document describes the design for a **Container Management** feature that provides centralized monitoring and tracking of containers across Sea Shipment, Transport Job, and related logistics operations. The feature consolidates container status, demurrage, detention, penalties, charges, deposits, returns, and other container lifecycle events into a single management layer.

### 1.1 Goals

- **Unified visibility**: Single view of each container’s status across all jobs and shipments
- **Cost control**: Track demurrage, detention, penalties, and charges per container
- **Deposit & return tracking**: Monitor container deposits and return status
- **Alerts & reporting**: Proactive alerts for approaching free-time limits and penalty thresholds
- **Integration**: Link to existing Sea Shipment, Transport Job, and charge doctypes

### 1.2 Scope

| In Scope | Out of Scope (Future) |
|----------|------------------------|
| Container status tracking | Container ownership/leasing lifecycle |
| Demurrage & detention calculation | Real-time carrier/EDI status sync |
| Penalty alerts & notifications | IoT/sensor integration |
| Container charges (demurrage, detention, deposit) | Container maintenance/repair |
| Deposit & return tracking | Container pool management |
| Reports & dashboards | Multi-company container transfers |

---

## 2. Current State

### 2.1 Where Containers Are Used

| DocType | Container Fields | Child Table | Notes |
|---------|------------------|-------------|-------|
| **Sea Shipment** | `containers` (child table) | Sea Freight Containers | container_no, seal_no, type, mode, delivery_modes |
| **Sea Booking** | `containers` (child table) | Sea Booking Containers | Same structure |
| **Sea Consolidation** | `containers` (child table) | Sea Consolidation Containers | container_number, container_type, seal_number, etc. |
| **Transport Order** | `container_type`, `container_no` | — | Single container per order |
| **Transport Job** | `container_type`, `container_no` | — | Single container per job |
| **Master Bill** | — | — | Links to Container Yard, Container Freight Station |

### 2.2 Existing Penalty Logic (Sea Shipment)

- **Sea Shipment** has `detention_days`, `demurrage_days`, `free_time_days`, `estimated_penalty_amount`, `penalty_alert_sent`, `last_penalty_check`
- **Sea Freight Settings** has `default_free_time_days`, `detention_rate_per_day`, `demurrage_rate_per_day`, `enable_penalty_alerts`
- **Scheduled tasks** (`check_sea_shipment_penalties`, `check_impending_penalties`) run penalty calculation and alerts
- **Sea Freight Charges** and **Sea Booking Charges** support charge types: Detention, Demurrage

### 2.3 Existing Master Data

- **Container Type** – master list of container types (20ft, 40ft, reefer, etc.)
- **Container Yard** – CY locations
- **Container Depot** – depot locations
- **Container Freight Station** – CFS locations

---

## 3. Target Architecture

### 3.1 Core Concept: Container Record

Introduce a **Container** doctype as the central entity. Each physical container (identified by `container_number`) gets one record that:

- Tracks current status and location
- Links to all jobs/shipments using it
- Aggregates demurrage, detention, charges, deposit, and return info

### 3.2 Data Flow

```
┌─────────────────┐     ┌─────────────────┐
│  Sea Shipment   │     │ Transport Job   │
│  (containers)   │     │ (container_no)  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Container (master)    │
                    │  - status, location    │
                    │  - demurrage, detention│
                    │  - deposit, return     │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ Container Movement     │
                    │ Container Charge       │
                    │ Container Deposit      │
                    └────────────────────────┘
```

---

## 4. Doctype Design

### 4.1 Container (New – Master)

**Module**: Logistics (or new Container Management module)

| Field | Type | Description |
|-------|------|-------------|
| `container_number` | Data, unique | Container number (e.g. MSCU1234567). Must pass ISO 6346 validation (see §4.6). |
| `container_type` | Link → Container Type | 20ft, 40ft, 40HC, reefer, etc. |
| `seal_number` | Data | Current seal (may change per leg) |
| `status` | Select | See §4.5 |
| `current_location` | Dynamic Link | Location (Container Yard, Depot, Shipper, etc.) |
| `current_location_name` | Data | Resolved location name |
| `owner_carrier` | Link → Carrier | Container owner/carrier (optional) |
| `column_break_1` | Column Break | |
| `free_time_days` | Float | Free time before penalties (from settings or override) |
| `free_time_until` | Datetime | Calculated: when free time ends |
| `demurrage_days` | Float | Days beyond free time at port/CY |
| `detention_days` | Float | Days beyond free time in possession |
| `estimated_penalty_amount` | Currency | Estimated demurrage + detention |
| `has_penalties` | Check | |
| `penalty_alert_sent` | Check | |
| `last_penalty_check` | Datetime | |
| `section_deposit` | Section Break | Deposit & Return |
| `deposit_amount` | Currency | Container deposit paid |
| `deposit_currency` | Link → Currency | |
| `deposit_paid_date` | Date | |
| `deposit_reference` | Data | Invoice/PO reference |
| `return_status` | Select | Not Returned / Returned / Overdue |
| `returned_date` | Date | |
| `return_location` | Dynamic Link | Where returned |
| `section_links` | Section Break | Linked Documents |
| `linked_shipments` | HTML | Virtual: list of Sea Shipments |
| `linked_transport_jobs` | HTML | Virtual: list of Transport Jobs |

**Permissions**: Standard (User can read, create, edit; Manager can delete)

**List view**: container_number, container_type, status, current_location_name, demurrage_days, detention_days, return_status

### 4.2 Container Movement (New – Child or Standalone)

Tracks each significant location change for a container.

| Field | Type | Description |
|-------|------|-------------|
| `container` | Link → Container | |
| `movement_type` | Select | Gate-In / Loaded / Discharged / Picked Up / Delivered / Returned / Other |
| `from_location` | Dynamic Link | |
| `to_location` | Dynamic Link | |
| `movement_date` | Datetime | |
| `reference_doctype` | Link → DocType | Sea Shipment, Transport Job, etc. |
| `reference_name` | Dynamic Link | |
| `notes` | Small Text | |

Can be a **child table** of Container, or a **standalone** doctype with `container` link. Standalone is preferred for reporting and audit.

### 4.3 Container Charge (New – Child Table)

Records charges specific to a container (demurrage, detention, per-container fees).

| Field | Type | Description |
|-------|------|-------------|
| `container` | Link → Container | |
| `charge_type` | Select | Demurrage / Detention / Storage / Per Container / Deposit Fee / Other |
| `charge_basis` | Select | Per Day / Fixed / Per TEU / Other |
| `quantity` | Float | Days, TEU, etc. |
| `unit_rate` | Currency | |
| `currency` | Link → Currency | |
| `total_amount` | Currency | |
| `reference_doctype` | Link → DocType | Sea Shipment, Sea Freight Charges, etc. |
| `reference_name` | Dynamic Link | |
| `invoice_status` | Select | Not Invoiced / Invoiced / Waived |
| `sales_invoice` | Link → Sales Invoice | |
| `purchase_invoice` | Link → Purchase Invoice | |

**Options**: Child table of Container, or standalone with `container` link. Standalone allows linking from Sea Freight Charges / Transport Job Charges when charge type is Demurrage/Detention.

### 4.4 Container Deposit (New – Child Table or Section on Container)

Tracks deposit payments and returns.

| Field | Type | Description |
|-------|------|-------------|
| `container` | Link → Container | |
| `deposit_amount` | Currency | |
| `deposit_currency` | Link → Currency | |
| `deposit_date` | Date | |
| `deposit_type` | Select | Customer Deposit / Carrier Deposit / Refund |
| `reference` | Data | Invoice/PO number |
| `refund_amount` | Currency | |
| `refund_date` | Date | |
| `reference_doctype` | Link → DocType | |
| `reference_name` | Dynamic Link | |

### 4.5 Container Status Options

| Status | Description |
|--------|--------------|
| In Transit | On vessel/truck, between locations |
| At Port (Origin) | At origin port/CY |
| Gate-In | Gate-in at port/CY |
| Loaded | Loaded on vessel |
| At Sea | On vessel |
| Discharged | Discharged at destination |
| At Port (Destination) | At destination port/CY |
| Customs Hold | Held for customs |
| Available for Pick-Up | Ready for delivery |
| Out for Delivery | With driver/carrier |
| Delivered | Delivered to consignee |
| Empty Returned | Empty container returned |
| At Depot | At container depot |
| Damaged | Damaged, requires repair |
| Lost | Lost or missing |
| Closed | Lifecycle complete |

### 4.6 Container Number Validation

Container numbers must conform to **ISO 6346**. Validation applies when creating or updating a Container, and when entering `container_no` / `container_number` on Sea Freight Containers, Sea Booking Containers, Sea Consolidation Containers, Transport Order, and Transport Job.

**Format (11 characters):**

| Part | Length | Allowed | Example |
|------|--------|---------|---------|
| Owner code | 3 | A–Z (letters) | MSC |
| Category identifier | 1 | U (freight), J (equipment), Z (trailer/chassis) | U |
| Serial number | 6 | 0–9 (digits) | 123456 |
| Check digit | 1 | 0–9 (calculated) | 7 |

**Example**: `MSCU1234567` → Owner MSC, Category U, Serial 123456, Check digit 7

**Validation rules:**

1. **Length**: Exactly 11 characters (no spaces, hyphens, or other separators; strip before validate).
2. **Owner code**: First 3 characters must be uppercase letters (A–Z).
3. **Category identifier**: 4th character must be U, J, or Z.
4. **Serial number**: Characters 5–10 must be digits (0–9).
5. **Check digit**: 11th character must match the ISO 6346 check digit algorithm.

**Check digit algorithm (ISO 6346):**

- Assign numeric values: A=10, B=12, C=13, D=14, E=15, F=16, G=17, H=18, I=19, J=20, K=21, L=23, M=24, N=25, O=26, P=27, Q=28, R=29, S=30, T=31, U=32, V=34, W=35, X=36, Y=37, Z=38. (Letters I, O, Q omitted; multiples of 11 skipped.)
- For each of the first 10 characters, multiply its value by 2^position (position 0–9).
- Sum all products, divide by 11, take remainder. If remainder is 10, check digit is 0; otherwise check digit equals remainder.

**Configuration:**

- **Strict validation** (default): Reject if format or check digit fails.
- **Lenient validation** (optional setting): Validate format only (length, pattern); skip check digit. Use for legacy data or non-ISO containers.
- **Validation bypass** (admin): Allow override for special cases (e.g. temp/domestic containers); log when used.

**Where to validate:**

- **Container** doctype: `validate()` on `container_number`
- **Sea Freight Containers**, **Sea Booking Containers**: `validate()` on parent when `container_no` is set
- **Sea Consolidation Containers**: `validate()` on `container_number`
- **Transport Order**, **Transport Job**: `validate()` when `container_no` is set and `transport_job_type` = Container
- **API**: `create_container_from_shipment`, `get_container_by_number` – validate before create/lookup

---

## 5. Integration with Existing Doctypes

### 5.1 Sea Shipment

- **On Save**: For each row in `containers`, ensure a **Container** record exists (create if not). Update Container status from `shipping_status` and link to Sea Shipment.
- **Container links**: Add `container` (Link → Container) to **Sea Freight Containers** child table. On save, resolve by `container_no` and set link.
- **Penalties**: Option A – keep penalty logic on Sea Shipment, sync to Container. Option B – move penalty calculation to Container, aggregate from milestones. **Recommendation**: Phase 1 keep on Sea Shipment, add sync to Container for unified view.
- **Charges**: When Sea Freight Charges has `charge_type` = Detention/Demurrage, create or update **Container Charge** linked to the Container.

### 5.2 Transport Job / Transport Order

- **On Save**: If `transport_job_type` = Container and `container_no` is set, ensure **Container** exists. Link Transport Job to Container.
- **New link**: Add `container` (Link → Container) to Transport Job and Transport Order. Resolve by `container_no`.
- **Status**: When Transport Job status changes (e.g. Delivered, Empty Returned), update Container status.

### 5.3 Sea Consolidation

- **Containers**: Sea Consolidation Containers has `container_number`. Link to Container; create Container if not exists.

---

## 6. Demurrage & Detention Logic

### 6.1 Definitions (from Glossary)

- **Demurrage**: Charge for container held at port/CY beyond free time.
- **Detention**: Charge for container held by customer (off port) beyond free time.

### 6.2 Calculation Basis

| Metric | Start Date | End Date | Source |
|--------|------------|----------|--------|
| Demurrage | Gate-in at port | Empty returned or today | Milestone: Gate-In at Port / CY |
| Detention | Discharge from vessel | Empty returned or today | Milestone: Discharged from Vessel |

### 6.3 Free Time

- Default from **Sea Freight Settings** (`default_free_time_days`)
- Overridable per **Container** or per **Sea Shipment** (if shipment-specific terms)
- Per-carrier free time (future): **Carrier** or **Container** `owner_carrier` with free time rules

### 6.4 Penalty Calculation (Container-Level)

1. Resolve `gate_in_date` and `discharge_date` from linked Sea Shipment milestones (or Transport Job).
2. `free_time_until` = discharge_date + free_time_days (for detention) or gate_in_date + free_time_days (for demurrage).
3. If today > free_time_until:
   - `detention_days` = days from discharge_date to min(returned_date, today) minus free_time_days
   - `demurrage_days` = days from gate_in_date to min(returned_date, today) minus free_time_days
4. `estimated_penalty_amount` = (detention_days × detention_rate) + (demurrage_days × demurrage_rate) from Sea Freight Settings.

### 6.5 Scheduled Task

- Extend or add task: `check_container_penalties`
- For each Container with status in (Discharged, At Port, Available for Pick-Up, Out for Delivery, Delivered):
  - Run penalty calculation
  - Update `demurrage_days`, `detention_days`, `estimated_penalty_amount`, `has_penalties`, `last_penalty_check`
  - Send alert if `has_penalties` and not `penalty_alert_sent` (reuse Sea Shipment alert pattern)

---

## 7. Container Deposit & Return

### 7.1 Deposit Tracking

- **Container** has `deposit_amount`, `deposit_currency`, `deposit_paid_date`, `deposit_reference`
- **Container Deposit** child table for multiple deposits/refunds (e.g. customer deposit, carrier deposit)
- Link to Sales Invoice / Purchase Invoice when invoiced

### 7.2 Return Tracking

- **return_status**: Not Returned / Returned / Overdue
- **returned_date**: When empty container was returned
- **return_location**: Container Yard, Depot, etc.
- **Overdue**: `returned_date` is null and today > `free_time_until` (or expected return date)

### 7.3 Status Transitions

- When milestone "Empty Container Returned" is completed → set Container `return_status` = Returned, `returned_date` = actual_end, `status` = Empty Returned
- Update `demurrage_days` / `detention_days` to stop at `returned_date`

---

## 8. Reports & Dashboards

### 8.1 Container Status Report

- Filters: status, container_type, current_location, date range
- Columns: container_number, container_type, status, current_location, linked_shipment, demurrage_days, detention_days, return_status, estimated_penalty_amount
- Group by: status, location

### 8.2 Container Penalty Report

- Containers with `has_penalties` = 1
- Columns: container_number, demurrage_days, detention_days, estimated_penalty_amount, free_time_until, linked_shipment
- Export for billing

### 8.3 Container Deposit Report

- Containers with outstanding deposits (deposit paid, not returned)
- Columns: container_number, deposit_amount, deposit_date, return_status, days_outstanding

### 8.4 Container Utilization (Existing)

- **Container Utilization Report** exists. Extend to optionally filter by Container record or show Container link.

### 8.5 Dashboard / Workspace

- **Container Management** workspace with:
  - Number cards: Containers at Risk (approaching free time), Containers with Penalties, Outstanding Deposits
  - Shortcuts: Container List, Container Status Report, Container Penalty Report
  - Chart: Containers by Status

---

## 9. Implementation Phases

### Phase 1: Foundation (MVP)

1. Create **Container** doctype with core fields (container_number, container_type, status, current_location, demurrage_days, detention_days, deposit, return_status)
2. Implement container number validation (ISO 6346) on Container and Sea Freight Containers
3. Add `container` link to **Sea Freight Containers** (child of Sea Shipment); auto-create/link Container on save
4. Sync penalty fields from Sea Shipment to Container (read-only on Container, calculated from Shipment)
5. Container list view and simple filters
6. **Container Status Report** (basic)

### Phase 2: Transport

1. Add `container` link to **Transport Job** and **Transport Order**; resolve by container_no
2. Extend container number validation to Transport Order and Transport Job
3. Update Container status from Transport Job status changes
4. **Container Movement** doctype (standalone) – manual or event-driven entries

### Phase 3: Charges & Deposits

1. **Container Charge** doctype – link from Sea Freight Charges when charge_type = Detention/Demurrage
2. **Container Deposit** child table on Container
3. Deposit & return tracking workflow
4. **Container Penalty Report**, **Container Deposit Report**

### Phase 4: Alerts & Dashboard

1. Scheduled task `check_container_penalties` (container-level)
2. Impending penalty alerts (reuse Sea Shipment pattern)
3. Container Management workspace with number cards and charts
4. Optional: Email notifications for penalty alerts

### Phase 5: Enhancements

1. Per-container free time override
2. Carrier-specific free time rules
3. Integration with carrier/EDI for status updates
4. Container Movement auto-population from milestones

---

## 10. Configuration

### 10.1 Logistics Settings (or new Container Management Settings)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_container_management` | Check | 0 | Enable Container doctype and linking |
| `auto_create_container` | Check | 1 | Create Container when container_no appears in Shipment/Job |
| `strict_container_validation` | Check | 1 | Enforce ISO 6346 check digit; if unchecked, validate format only |
| `container_penalty_source` | Select | Sea Shipment | Where to calculate penalties: Sea Shipment / Container |
| `default_free_time_days` | Int | 7 | (May already exist in Sea Freight Settings) |
| `enable_container_penalty_alerts` | Check | 1 | Send penalty alerts at container level |

### 10.2 Sea Freight Settings (Existing)

- `default_free_time_days`
- `detention_rate_per_day`
- `demurrage_rate_per_day`
- `enable_penalty_alerts`

---

## 11. API Considerations

### 11.1 Whitelisted Methods

- `get_container_by_number(container_number)` → Container doc or None
- `create_container_from_shipment(sea_shipment_name, container_no, ...)` → Container
- `update_container_status(container_name, status, location, movement_date)` → success
- `calculate_container_penalties(container_name)` → {demurrage_days, detention_days, estimated_amount}
- `link_container_to_job(container_name, reference_doctype, reference_name)` → success

### 11.2 Permissions

- Container: User can read/create/edit own; Manager can delete
- Container Charge, Container Movement, Container Deposit: Same as parent or standard child permissions

---

## 12. Migration

- **No data migration** required for Phase 1 if Container is created on-demand when Shipment/Job is saved
- Existing Sea Shipments: Containers will be created when document is next edited/saved, or via a one-time script that iterates Sea Shipment → containers and creates Container records
- Transport Jobs: Same – create Container on next save or via migration script

---

## 13. Glossary

| Term | Definition |
|------|-------------|
| **Demurrage** | Charge for container held at port/CY beyond free time |
| **Detention** | Charge for container held by customer beyond free time |
| **Free time** | Days allowed before demurrage/detention charges apply |
| **Container deposit** | Refundable deposit paid for container use |
| **TEU** | Twenty-foot equivalent unit (1×20ft = 1 TEU, 1×40ft ≈ 2 TEU) |
| **CY** | Container Yard |
| **CFS** | Container Freight Station |
| **Gate-in** | When container enters port/CY |

---

## 14. References

- `logistics/sea_freight/doctype/sea_shipment/sea_shipment.py` – penalty calculation
- `logistics/sea_freight/tasks.py` – penalty scheduled tasks
- `logistics/sea_freight/doctype/sea_freight_settings/sea_freight_settings.json` – penalty settings
- `logistics/sea_freight/doctype/sea_freight_charges/` – charge types Detention, Demurrage
- `logistics/transport/doctype/transport_job/` – container_type, container_no
- `logistics/transport/doctype/transport_order/` – container_type, container_no
- `docs/CHARGE_CALCULATION_DESIGN.md` – charge calculation pattern
- `docs/MILESTONES_IMPLEMENTATION_DESIGN.md` – milestone structure
