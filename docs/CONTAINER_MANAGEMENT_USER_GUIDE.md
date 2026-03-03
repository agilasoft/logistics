# Container Management – User Guide

## Overview

Container Management provides centralized tracking of containers across Sea Shipment, Transport Job, and Transport Order. It monitors container status, demurrage, detention, penalties, charges, deposits, and returns.

---

## 1. Enabling Container Management

1. Go to **Logistics Settings** (search in the Awesome Bar).
2. Open the **Container Management** tab.
3. Check **Enable Container Management**.
4. Configure options:
   - **Auto Create Container** – Create Container records when container numbers appear in Shipments/Jobs (default: on).
   - **Strict Container Validation (ISO 6346)** – Enforce full ISO 6346 check digit validation (default: on). Turn off for format-only validation.
   - **Enable Container Penalty Alerts** – Allow penalty alerts at container level (default: on).

---

## 2. Container Number Format (ISO 6346)

Container numbers must follow ISO 6346:

- **11 characters**: 3 letters (owner) + 1 letter (U/J/Z) + 6 digits (serial) + 1 digit (check digit)
- **Example**: `MSCU1234567` → Owner MSC, Category U, Serial 123456, Check digit 7

**Validation applies to:**
- Sea Shipment → containers child table
- Sea Booking → containers child table
- Sea Consolidation → containers
- Transport Order → container_no (when job type is Container)
- Transport Job → container_no (when job type is Container)

---

## 3. How Containers Are Created and Linked

### From Sea Shipment

1. Create or edit a **Sea Shipment**.
2. Add rows in the **Containers** tab with `Container No`, `Type`, `Seal No`, etc.
3. On save, the system:
   - Validates each container number (ISO 6346).
   - Creates a **Container** record if it does not exist.
   - Links the Container to the child row.
   - Syncs penalty fields (demurrage, detention, estimated amount) from the shipment.

### From Transport Job

1. Create or edit a **Transport Job**.
2. Set **Transport Job Type** = **Container**.
3. Enter **Container No** and **Container Type**.
4. On save, the system:
   - Validates the container number.
   - Creates or links the Container.
   - Sets the Container status from the job status.

### From Transport Order

1. Create or edit a **Transport Order**.
2. Set **Transport Job Type** = **Container**.
3. Enter **Container No** and **Container Type**.
4. On save, the system creates or links the Container.

---

## 4. Container Record

Each Container record shows:

- **Container Number** – Unique identifier (ISO 6346).
- **Container Type** – Link to Container Type master.
- **Status** – In Transit, Gate-In, Loaded, Discharged, Delivered, Empty Returned, etc.
- **Current Location** – Location type and name.
- **Demurrage Days** / **Detention Days** – Calculated from linked Sea Shipment.
- **Estimated Penalty Amount** – From Sea Freight Settings rates.
- **Deposit & Return** – Deposit amount, paid date, return status, returned date.

**Linked Documents** – Lists linked Sea Shipments and Transport Jobs.

---

## 5. Container Movement

Use **Container Movement** to log location changes:

- **Movement Type**: Gate-In, Loaded, Discharged, Picked Up, Delivered, Returned, Other
- **From/To Location** – Dynamic Link to Container Yard, Depot, etc.
- **Movement Date** – When the event occurred.
- **Reference** – Link to Sea Shipment or Transport Job.

---

## 6. Container Charge

Use **Container Charge** for container-specific charges:

- **Charge Type**: Demurrage, Detention, Storage, Per Container, Deposit Fee, Other
- **Charge Basis**: Per Day, Fixed, Per TEU, Other
- **Quantity**, **Unit Rate**, **Total Amount**
- **Invoice Status**: Not Invoiced, Invoiced, Waived
- **Sales Invoice** / **Purchase Invoice** – Link when invoiced.

---

## 7. Container Deposit

Use the **Deposits** child table on Container:

- **Deposit Amount**, **Deposit Currency**, **Deposit Date**
- **Deposit Type**: Customer Deposit, Carrier Deposit, Refund
- **Refund Amount**, **Refund Date** – When returned

---

## 8. Reports

| Report | Purpose |
|--------|---------|
| **Container Status Report** | All containers with filters (status, type, return status). |
| **Container Penalty Report** | Containers with penalties (demurrage/detention). |
| **Container Deposit Report** | Containers with outstanding deposits (not returned). |

---

## 9. Container Management Workspace

Access via **Sea Freight** sidebar → **Container Management**, or search **Container Management**.

**Includes:**
- Number cards: **Containers with Penalties**, **Outstanding Deposits**
- Shortcuts: Container, Container Status Report, Container Penalty Report, Container Deposit Report, Container Movement, Container Charge

---

## 10. Penalty Calculation

- **Source**: Sea Shipment (milestones, discharge date, gate-in date).
- **Settings**: Sea Freight Settings → `default_free_time_days`, `detention_rate_per_day`, `demurrage_rate_per_day`.
- **Sync**: Container penalty fields are updated when the linked Sea Shipment is saved.
- **Scheduled task**: `check_container_penalties` (in Sea Freight tasks) can be run hourly to check for penalties.

---

## 11. API Methods (for integrations)

| Method | Description |
|--------|-------------|
| `logistics.container_management.api.get_container_by_number_api` | Get Container by number. |
| `logistics.container_management.api.create_container_from_shipment` | Create Container from Sea Shipment. |
| `logistics.container_management.api.update_container_status` | Update Container status. |
| `logistics.container_management.api.calculate_container_penalties` | Recalculate penalties. |

---

## 12. Quick Reference

| Task | Where |
|------|-------|
| Enable feature | Logistics Settings → Container Management |
| Add containers to shipment | Sea Shipment → Containers tab |
| Add container to transport job | Transport Job → Container No (when type = Container) |
| View all containers | Container list |
| View penalties | Container Penalty Report |
| View deposits | Container Deposit Report |
| Log movement | Container Movement |
