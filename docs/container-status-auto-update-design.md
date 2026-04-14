# Container status: current auto-update design and improvement proposals

This document describes how **Container** `status` and **return** fields are updated automatically today, why reuse in a new **Sea Shipment** can still require manual steps, and concrete improvement directions.

## Scope and prerequisites

- **Feature flag:** Container sync runs only when **Logistics Settings → enable_container_management** is enabled (`logistics.container_management.api.is_container_management_enabled`).
- **Primary code:** `logistics/container_management/api.py` (create/link, status mapping, penalty sync).
- **Reuse validation:** `logistics/sea_freight/doctype/sea_shipment/sea_shipment.py` (`_container_returned_for_shipment` and duplicate-container checks in `validate`).

---

## Current design: how status gets updated

### 1. Sea Shipment → Container (main path)

**Trigger:** `Sea Shipment.before_save` calls `sync_shipment_containers_and_penalties(self)`.

**Behaviour:**

- For each row in **Sea Freight Containers** with a `container_no`, the system resolves or creates a **Container** via `get_or_create_container(...)`.
- **Status** passed into `get_or_create_container` is derived from the shipment’s **`shipping_status`** using `_shipping_status_to_container_status`:

| Sea Shipment `shipping_status` | Container `status` |
|-------------------------------|---------------------|
| Gate-In at Port / CY | Gate-In |
| Loaded on Vessel | Loaded |
| Departed | At Sea |
| In-Transit | At Sea |
| Arrived | At Port (Destination) |
| Discharged from Vessel | Discharged |
| Customs Clearance (Import) | Customs Hold |
| Available for Pick-Up | Available for Pick-Up |
| Out for Delivery | Out for Delivery |
| Delivered | Delivered |
| Empty Container Returned | Empty Returned |
| Detention / Demurrage Ongoing | At Port (Destination) |

- Any `shipping_status` **not** in this map yields **no container status update** (existing `Container.status` is preserved; new containers still default to **In Transit** on create).
- When status is **Empty Returned** or **Closed** (see gaps below), `_apply_status_with_return_sync` also sets **`return_status`** to **Returned** and **`returned_date`**.
- Penalty-related fields are copied from the **Sea Shipment** to the **Container** unless `penalty_manual_override` is set (`_sync_penalty_to_container`).

**Important:** Updates happen when the **Sea Shipment document is saved**. There is no separate scheduler or message queue that pushes container status independently of saving the shipment.

### 2. Transport Job → Container

**Trigger:** `Transport Job.before_save`, when `transport_job_type == "Container"` and `container_no` is set, calls `sync_transport_job_container(self)`.

**Behaviour:** `get_or_create_container` is called with status from `_transport_status_to_container_status(job.status)`:

| Transport Job `status` | Container `status` |
|------------------------|---------------------|
| Delivered | Delivered |
| Completed | **Empty Returned** |
| In Progress | Out for Delivery |
| (anything else) | In Transit |

So a container job that reaches **Completed** can mark the equipment as **Empty Returned** without the user editing the Sea Shipment—**provided** the transport job is saved with that status while container management is enabled.

### 3. Transport Order → Container

**Trigger:** `Transport Order.before_save` for container-type orders with `container_no`.

**Behaviour:** `get_or_create_container` is called with a **fixed** status **`In Transit`**. There is **no** ongoing sync from order or job lifecycle beyond this initial link; status evolution is expected from **Sea Shipment** and/or **Transport Job** paths above.

### 4. Manual / API

**`update_container_status(container_name, status, movement_date)`** (whitelisted) calls `_apply_status_with_return_sync`. This is the explicit escape hatch when automation does not match reality.

**Container Movement (save):** On insert/update of **Container Movement**, `movement_type` is mapped to **Container** `status` (e.g. **Returned** → **Empty Returned** with return fields). **Other** does not change status.

### 5. Internal helper: `_apply_status_with_return_sync`

When applying a status, if the status is **Empty Returned** or **Closed**, the code sets **`return_status = Returned`** and **`returned_date`** (using `movement_date` when provided). This aligns the Container with the **Sea Shipment** reuse rules that treat “returned” as allowing another shipment to use the same number.

---

## How “reuse in another shipment” is decided

Duplicate container numbers across non-cancelled **Sea Shipment** documents are blocked **unless** the equipment is considered returned (`Sea Shipment.validate`).

When container management is enabled, reuse is allowed if **`get_container_by_number`** resolves a Container where:

- `return_status == "Returned"`, or  
- `status` is **Empty Returned** or **Closed**.

If that check fails, the code falls back to the **other** shipment’s **`shipping_status`** being **Empty Container Returned** or **Closed**.

So automatic reuse requires the **Container** record (or the other shipment’s status) to reach a **terminal returned/closed** state. Intermediate states such as **Delivered** alone do **not** unlock reuse.

---

## Why status often does not feel “automatic”

1. **Sea Shipment drives status only on save**  
   If users do not advance **`shipping_status`** to **Empty Container Returned** (or **Closed**), the Container may remain in **Delivered** or earlier—**not** in a returned state—so reuse stays blocked.

2. **Transport Job path may not run**  
   If there is no container **Transport Job**, or it never reaches **Completed**, the **Completed → Empty Returned** shortcut never runs.

3. **Transport Order does not advance lifecycle**  
   Orders only set **In Transit** at link time; they do not close the loop.

4. **Default mapping for unknown `shipping_status`**  
   *(Addressed in code:)* Unlisted values no longer force **In Transit**; they skip a status update on existing containers.

5. **“Closed” on Sea Shipment**  
   *(Addressed in code:)* **Closed** maps to Container **Closed** and syncs return fields like other terminal states.

6. **Container Movement**  
   *(Addressed in code:)* **Container Movement** `on_update` calls the container-management sync when enabled.

---

## Proposed improvements

### A. Align lifecycle and reuse (quick wins)

- **Map `Closed`** in `_shipping_status_to_container_status` to **`Closed`** (or **Empty Returned**, per business rule) so Container and shipment terminal states stay consistent.
- **Review the default** for unmapped `shipping_status`: consider **no change** (skip status update) instead of forcing **In Transit**, to avoid regressions when new milestone values are introduced.
- **Document in-app** (e.g. Sea Shipment or Container form): “To allow this container on a new shipment, set shipping status to Empty Container Returned, complete the Transport Job, or update the Container manually.”

### B. Stronger automation options

1. **On Transport Job Completed**  
   Ensure container sync runs on **submit** or **on_update** after status changes (not only `before_save` paths you already rely on), if any code path sets **Completed** without a full save cycle through the same hooks.

2. **Derive “returned” from business facts**  
   Optionally treat **Delivered** + empty return milestone / depot scan / **Container Movement** “empty return” as **Empty Returned** if policy allows—reduces dependence on a single dropdown.

3. **Container Movement → Container status**  
   On submit of **Container Movement**, update **Container** `status` / `return_status` from movement type or location (with idempotency and permission checks).

4. **Background reconciliation**  
   Scheduled job: for Containers linked to submitted Sea Shipments whose **`shipping_status`** is terminal but Container is not **Returned**, fix or notify.

### C. Data model / UX

- **`Available` / `Idle`** (or similar) explicit state for equipment ready for the next booking, if **Empty Returned** is too freight-specific.
- **Audit trail:** link last-updating document (Sea Shipment, Transport Job, manual) on Container for support.

---

## File reference (implementation)

| Concern | Location |
|--------|----------|
| Status mapping, `get_or_create_container`, sync entry points | `logistics/container_management/api.py` |
| Sea Shipment → sync | `logistics/sea_freight/doctype/sea_shipment/sea_shipment.py` (`before_save`) |
| Transport Job → sync | `logistics/transport/doctype/transport_job/transport_job.py` (`before_save`) |
| Transport Order → sync | `logistics/transport/doctype/transport_order/transport_order.py` (`before_save`) |
| Duplicate container / reuse rules | `logistics/sea_freight/doctype/sea_shipment/sea_shipment.py` (`validate`, `_container_returned_for_shipment`) |
| Container DocType fields | `logistics/logistics/doctype/container/container.json` |

---

*Generated from codebase review; adjust proposals after product confirmation on the canonical “returned” definition and whether **Closed** applies per shipment or per equipment lifecycle.*

---

## Implemented (follow-up)

- **`_shipping_status_to_container_status`:** Maps **Closed** and **Customs Hold**; unmapped → `None` (no overwrite on existing Container).
- **`_transport_status_to_container_status`:** Unmapped job statuses → `None` (no overwrite).
- **`Transport Job.after_submit`:** Calls `sync_transport_job_container` after status is finalized (covers **Completed** → **Empty Returned** when submit drives status without a prior save through `before_save`).
- **`Container Movement.on_update`:** `sync_container_from_movement` via `movement_type_to_container_status`.
- **Daily scheduler:** `reconcile_containers_from_terminal_sea_shipments` re-runs shipment→container sync for submitted shipments in **Empty Container Returned** / **Closed**.
- **Sea Shipment** `shipping_status` field description: short reuse guidance for users.
