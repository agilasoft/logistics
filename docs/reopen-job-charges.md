# Reopen Job (charge editing on submitted shipments and jobs)

**Action → Reopen Job** and **Action → Close Job** are driven by a single concept: **Job Status** (same Select options on every main-service job/shipment DocType). When Job Status is **Completed** or **Closed** on a **submitted** document, the **charges** child table is locked until you reopen.

## Job Status options (all DocTypes below)

`Draft` → `Submitted` → `In Progress` → `Completed` → `Closed` — plus `Reopened` (temporary, for charge edits) and `Cancelled`.

Transport Job already used this set on field `status` (labeled **Job Status** in the form). Sea/Air shipments, Warehouse Job, and Declaration use a dedicated field **`job_status`** with the **same options**.

## Scope (DocTypes)

| DocType | Field | Who sets Job Status |
|--------|--------|---------------------|
| **Transport Job** | `status` | Existing server logic (legs, submit, etc.) + reopen/close |
| **Sea Shipment** | `job_status` | Synced from **Shipping Status** (read-only); reopen/close skip sync |
| **Air Shipment** | `job_status` | Synced from **Tracking Status** (Delivered → Completed); reopen/close skip sync |
| **Warehouse Job** | `job_status` | Editable; defaults to **Submitted** when submitted — set **Completed** / **Closed** when appropriate |
| **Declaration** | `job_status` | Synced from customs **Status** (read-only); reopen/close skip sync |

**General Job** is not in this flow (no `CHARGE_REOPEN_CONFIG` entry / validate hook).

### Charge lock rule (server + desk)

- **Locked:** submitted and Job Status ∈ {**Completed**, **Closed**}
- **Reopen Job:** allowed only in those states → sets Job Status to **Reopened**
- **Close Job:** allowed only when Job Status is **Reopened** → sets Job Status to **Closed**

## Implementation

### Python

| Piece | Path |
|--------|------|
| Shared options + sync helpers | `logistics/job_management/logistics_job_status.py` |
| Whitelist + validate hook | `logistics/job_management/charge_reopen.py` |
| Sea sync | `sea_shipment.py` `validate` → `sync_sea_shipment_job_status` |
| Air sync | `air_shipment.py` `validate` → `sync_air_shipment_job_status` |
| Declaration sync | `declaration.py` `validate` → `sync_declaration_job_status` |
| Warehouse defaults | `warehouse_job.py` `validate` → `validate_warehouse_job_defaults` |

`reopen_job_for_charges` / `close_job_for_charges` set `doc.flags.skip_job_status_sync = True` for that save so operational fields do not overwrite **Reopened** / **Closed**.

### Hooks

`validate_submitted_charges_not_locked` is registered in `logistics/hooks.py` for: Transport Job, Sea Shipment, Air Shipment, Warehouse Job, Declaration.

### Desk JS

`logistics/job_management/job_charge_reopen.js` — reads **Job Status** from `status` (Transport Job) or `job_status` (others), toggles **charges** read-only, **Action** buttons.

**Sea Shipment** and **Air Shipment** call a **deferred** `job_charge_reopen.setup(frm)` from `sea_shipment.js` / `air_shipment.js` (after `setTimeout`) so the Action menu is built in a stable order.

### Data backfill

Patch `logistics.patches.v1_0_backfill_logistics_job_status` runs after migrate and fills `job_status` from existing operational fields / defaults.

### Legacy fields

**Charges Locked** / **charges_reopen_mode** may still exist on some forms; **charge reopen no longer uses them**. Prefer **Job Status** for lock/reopen behaviour.

## API

| Action | Method |
|--------|--------|
| Reopen | `logistics.job_management.charge_reopen.reopen_job_for_charges` |
| Close | `logistics.job_management.charge_reopen.close_job_for_charges` |

Args: `doctype`, `name` (requires write permission on the document).
