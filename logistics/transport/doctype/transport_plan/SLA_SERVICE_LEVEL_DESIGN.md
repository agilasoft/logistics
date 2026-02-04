# Service Level Functions Guide

This guide describes how **Logistics Service Level** works across the application: where it applies, how SLA target dates are set, and how SLA is monitored at job level in Transport, Sea Freight, Air Freight, Warehousing, Customs, and Pricing Center.

---

## 1. Overview

### 1.1 What is Logistics Service Level?

**Logistics Service Level** is a master that defines:

- A service product (e.g. "Express 2-day", "Standard 5-day") with a **service code** and **service name**.
- **SLA rules per module** in the **Service Level by Module** child table (**Logistics Service Level Module**): for each module (Transport, Sea Freight, Air Freight, Warehousing, Customs) you set which job date to use as the base, how many days to add, and when the job is considered "At Risk" or "Breached".

Service level is **applicable** (selected) on **Sales Quote**, **Orders** (e.g. Transport Order, Sea Booking, Air Booking), and **Jobs** (Transport Job, Sea Shipment, Air Shipment, Warehouse Job). **Monitoring** (SLA target date, SLA status, and automatic status updates) happens **only on Jobs**. Quote and Order carry the service level for propagation; they do not have SLA target or status fields.

### 1.2 Key principles

| Principle | Description |
|-----------|-------------|
| **Target date from job date** | The SLA target date is always based on a **date on the job**. When setting up a Service Level, you choose which job date to use (e.g. Job Open Date, Recognition Date, Invoice Date, Booking Date, ETD, ETA). Target = **that job date** + **days to add** (from the service level). |
| **Applicable vs monitoring** | **Applicable:** Service level can be **selected** on Quote, Order, and Job. **Monitoring:** SLA target date, SLA status (On Track / At Risk / Breached), and scheduler updates exist **only on Job** doctypes. |
| **One master, settings per module** | The same **Logistics Service Level** master has a **Service Level by Module** child table: one row per module (Transport, Sea Freight, Air Freight, Warehousing, Customs). Each row defines that module’s SLA base date, days to add, and At Risk / Breach thresholds. Sales Quote carries service level into Orders and Jobs. |

---

## 2. Master: Logistics Service Level

### 2.1 Basic fields

| Field | Purpose |
|-------|---------|
| **Service Code** | Unique code (e.g. used in naming). |
| **Service Name** | Display name (e.g. "Express 2-day", "Standard 5-day"). |
| **Description** | Free-form description (text editor). |
| **Escalation Contact** | Optional User link for future alerts when status becomes At Risk or Breached. |
| **SLA Notes** | Optional notes (e.g. escalation process). |

### 2.2 SLA Monitoring section: Service Level by Module

In the **SLA Monitoring** section you define SLA rules **per module** in the **Service Level by Module** table (child table **Logistics Service Level Module**). Add one row per module you want to support (Transport, Sea Freight, Air Freight, Warehousing, Customs). Each row applies to jobs in that module only.

**Table columns (per module row):**

| Field | Purpose |
|-------|---------|
| **Module** | Transport, Sea Freight, Air Freight, Warehousing, or Customs. Required; one row per module. |
| **Enabled** | Check to apply this service level to this module; uncheck to skip. |
| **SLA Target Base Date** | **Which job date** to use as the base for this module. Options: Job Open Date, Recognition Date, Invoice Date, Booking Date, ETD, ETA, ATD, ATA, Scheduled Date, Due Date, Manual on Job. |
| **Days to Add** | Number of days to add to the base date to get the SLA target (e.g. transit days). If blank, derivation uses 0. |
| **Business Day End Hour** | When the base is date-only, the target time is set to this hour (0–23, e.g. 17 = 5 PM). |
| **At Risk (hours before target)** | Hours before the SLA target at which status becomes **At Risk** (e.g. 24). Default 24. |
| **Breach Grace (minutes after target)** | Minutes after the SLA target before status becomes **Breached** (e.g. 0 or 60). Default 0. |

If **Days to Add** is left blank in a module row, the derivation uses 0 (target = base date + 0 days). Thresholds for At Risk / Breach come from this child table; if a value is blank, the scheduler uses defaults (24 hours, 0 minutes).

### 2.3 Base date options (job-level dates)

| Option | Meaning | Typical job fields (by module) |
|--------|---------|--------------------------------|
| Job Open Date | When the job was opened | Warehouse Job: `job_open_date`; others: equivalent. |
| Recognition Date | Revenue / recognition date | Sea Shipment, Warehouse Job: `recognition_date`. |
| Invoice Date | Billing / invoice date | From linked Sales Invoice or job-level invoice date. |
| Booking Date | Booking / order date | Transport Job, Sea/Air Shipment: `booking_date`. |
| ETD / ETA / ATD / ATA | Estimated/actual departure/arrival | Sea/Air Shipment: `etd`, `eta`, `atd`, `ata`. |
| Scheduled Date | Scheduled execution date | Transport Job: `scheduled_date`. |
| Due Date | Order due date | Warehouse Job: from reference order `due_date`. |
| Manual on Job | No auto-calculation | User sets SLA target date on the job only. |

Each **module row** in Service Level by Module uses the base date option for that module’s jobs. The system looks up the row where **Module** matches the job’s module.

**Module name used for each job doctype:**

| Job doctype    | Module (row in Service Level by Module) |
|----------------|----------------------------------------|
| Transport Job  | Transport                              |
| Sea Shipment   | Sea Freight                            |
| Air Shipment   | Air Freight                            |
| Warehouse Job  | Warehousing                            |
| Declaration    | Customs (optional; for reporting)      |

### 2.4 How target date is calculated

For a job with a **Logistics Service Level** (or **service_level**) set:

1. The system finds the **Service Level by Module** row where **Module** = the job’s module (Transport, Sea Freight, Air Freight, Warehousing) and **Enabled** = 1.
2. If no such row exists, SLA target is not derived automatically.
3. Otherwise: **SLA Target Date** = **[value of that row’s base date on the job]** + **Days to Add** (from that row), with time set to **Business Day End Hour** if the base is date-only.

If the job does not have the selected base date field or the value is null, the SLA target date is left empty until that date is set.

---

## 3. Where Service Level Applies vs Where It Is Monitored

### 3.1 Applicable (selection only)

Service level can be **selected** on:

| Level | Doctypes |
|-------|----------|
| **Quote** | Sales Quote |
| **Order** | Transport Order, Sea Booking, Air Booking; optionally Warehousing orders (Inbound, Release, Transfer, VAS, Stocktake). |
| **Job** | Transport Job, Sea Shipment, Air Shipment, Warehouse Job. |

Quote and Order store the service level link so it can propagate to the Job. The Job can also have the service level set or overridden directly.

### 3.2 Monitoring (job level only)

SLA **target date**, **status** (On Track / At Risk / Breached / Not Applicable), and **automatic status updates** exist **only on Job** doctypes:

| Module | Job doctype (monitoring) |
|--------|--------------------------|
| Transport | **Transport Job** |
| Sea Freight | **Sea Shipment** |
| Air Freight | **Air Shipment** |
| Warehousing | **Warehouse Job** |

Quote and Order do **not** have SLA target date, SLA status, or scheduler updates; they only carry the service level for applicability and propagation.

---

## 4. Job-Level SLA Fields and Behaviour

### 4.1 Fields on the job (Service Level tab)

| Field | Purpose |
|-------|---------|
| **Logistics Service Level** | Link to the master. Set from Order/Quote when the job is created from an order; can be set or overridden on the job. |
| **SLA Target Source** | "From Service Level" or "Manual". Indicates how the SLA target date was set. |
| **SLA Target Date** | When the job is due (derived from service level or set manually). |
| **SLA Status** | On Track / At Risk / Breached / Not Applicable. Updated by the scheduler when a target is set. |
| **SLA Notes** | Free-form notes (e.g. reason for breach, mitigation). |

### 4.2 Derivation rules

- When the job is created from an Order (or when the order link is set) and the Order has a service level, the job's **Logistics Service Level** is set from the Order.
- When the job has **Logistics Service Level** set, the system looks up the **Service Level by Module** row for that job’s module (e.g. Transport Job → module "Transport"). If that row exists, is **Enabled**, and **SLA Target Base Date** is not "Manual on Job":
  - The system reads the job's date field for that base (e.g. Job Open Date → `job_open_date`, Booking Date → `booking_date`).
  - It adds that row’s **Days to Add** and sets time to **Business Day End Hour** → stores result in **SLA Target Date** and sets **SLA Target Source** = "From Service Level".
  - If the job does not have that date field or the value is null, SLA Target Date is left empty.
- When the user edits SLA Target Date manually (or the module row has base date "Manual on Job"), **SLA Target Source** is set to "Manual".

### 4.3 SLA status update (scheduler)

A scheduled task updates **SLA Status** on jobs that have an SLA target date and are not completed/cancelled:

- **At Risk:** Current time is within **At Risk (hours before target)** of the SLA target date.
- **Breached:** Current time is past the SLA target date plus **Breach Grace (minutes after target)**.
- **On Track:** Otherwise.

Thresholds (hours before target, minutes after target) come from the **Service Level by Module** row for that job’s module (Transport, Sea Freight, Air Freight, Warehousing). If no enabled row exists for that module, application defaults (e.g. 24 hours, 0 minutes) are used.

---

## 5. Module-by-Module

### 5.1 Transport

- **Applicable:** Transport Order, Transport Job (service level can be selected).
- **Monitoring:** **Transport Job** only (SLA target date, SLA status, scheduler).
- **Flow:** Order has `service_level` → when a Transport Job is created from the Order, job gets `logistics_service_level`. SLA target is derived from the **Service Level by Module** row where Module = "Transport" (if enabled and base date ≠ Manual on Job): job date + days.
- **Job dates:** e.g. booking_date, scheduled_date; Invoice Date from Sales Invoice; Job Open Date from creation.

### 5.2 Sea Freight

- **Applicable:** Sea Booking, Sea Shipment (job) have `service_level` (Link).
- **Monitoring:** **Sea Shipment** (job) only. Sea Booking does not have SLA target/status; it only carries service level for propagation.
- **Flow:** Booking has `service_level` → Shipment (job) gets service level. SLA target is derived from the **Service Level by Module** row where Module = "Sea Freight" (if enabled): job date + days.
- **Job dates:** booking_date, etd, eta, atd, ata, recognition_date, etc.

### 5.3 Air Freight

- **Applicable:** Air Booking, Air Shipment (job) have `service_level` (Link).
- **Monitoring:** **Air Shipment** (job) only. Air Booking does not have SLA target/status.
- **Flow:** Same as Sea. Target = job date from the **Service Level by Module** row where Module = "Air Freight" + days; scheduler updates SLA status on Air Shipment.

### 5.4 Warehousing

- **Applicable:** Optional `logistics_service_level` on orders (Inbound, Release, Transfer, VAS, Stocktake) and on **Warehouse Job** (job).
- **Monitoring:** **Warehouse Job** only. Orders do not have SLA target/status.
- **Flow:** Order (optional service level, due_date) → Warehouse Job gets service level. SLA target from the **Service Level by Module** row where Module = "Warehousing" (if enabled): job date (e.g. job_open_date, recognition_date) or reference order due_date (if base = "Due Date") + days.
- **Job dates:** job_open_date, recognition_date; reference order due_date.

### 5.5 Customs

- **Applicable:** Customs does not use Logistics Service Level for applicability.
- **Monitoring:** Customs Authority has its own SLA (standard/express/urgent days). Optional: **Declaration** can have a link to **Logistics Service Level** for **cross-module reporting** only (e.g. group declarations by service level in an SLA report). Authority SLA remains the source for customs deadlines.

### 5.6 Pricing Center (Sales Quote)

- **Applicable:** Sales Quote has `service_level` (Link → Logistics Service Level). Quote is the **source** for downstream orders and jobs.
- **Monitoring:** None on Quote. Ensure that when creating Transport Order, Sea Booking, or Air Booking from a Quote, `service_level` is copied so Jobs receive the service level and SLA is derived and monitored there.

---

## 6. Monitoring and Reporting

### 6.1 List views

- On **Job** list views (Transport Job, Sea Shipment, Air Shipment, Warehouse Job), show columns: Logistics Service Level (or service_level), SLA Target Source, SLA Target Date, SLA Status.
- Use filters: by Logistics Service Level, SLA Status, date range, customer, etc.

### 6.2 Reports

- **SLA compliance by Logistics Service Level:** Group by Logistics Service Level; count (or percentage) of jobs by SLA Status (On Track, At Risk, Breached) per module and time period.
- **On Time Delivery Report** (Transport): Optionally add filter/column for Logistics Service Level to analyse delivery performance by service level.
- **Cross-module:** One report can show SLA compliance grouped by service level and by module (Transport, Sea, Air, Warehousing).

### 6.3 Transport Plan context

Jobs in a Transport Plan are those linked via Plan → Run Sheets → Legs → Transport Job. To monitor SLA in plan context: list or report on those jobs and filter/group by Logistics Service Level and SLA Status. See **SLA_MONITORING.md** for the Plan → Job relationship.

### 6.4 Defaults and settings

- **Air Freight Settings / Sea Freight Settings:** `default_service_level` can be used when creating Booking/Shipment without an explicit service level (e.g. from Quote).
- **Warehouse Settings:** Optional `default_logistics_service_level` for new orders/jobs.
- **Transport:** Default can come from Order's service level or Transport Settings if configured.

---

## 7. Quick Reference

### 7.1 Where is service level used?

| Where | Role |
|-------|------|
| Sales Quote | Select service level; flows to Order/Booking → Job. |
| Transport Order, Sea Booking, Air Booking, (optional) Warehousing orders | Select service level; propagates to Job. |
| Transport Job, Sea Shipment, Air Shipment, Warehouse Job | Select service level; **SLA target and status live here only**. |

### 7.2 How is SLA target date set?

1. On **Logistics Service Level**, open **SLA Monitoring** and add rows in **Service Level by Module** for each module (Transport, Sea Freight, Air Freight, Warehousing, Customs). In each row set **Module**, **Enabled**, **SLA Target Base Date**, **Days to Add**, **Business Day End Hour**.
2. On the **Job**, the system finds the row where **Module** = that job’s module (e.g. Transport Job → "Transport"). It reads the job date for that base, adds the days, sets time to Business Day End Hour → **SLA Target Date**. If base date is "Manual on Job" or no enabled row for that module, the user sets SLA Target Date on the job (or it stays empty).
3. **SLA Target Source** on the job is "From Service Level" or "Manual".

### 7.3 How is SLA status updated?

- A **scheduler** runs periodically (hourly).
- For each job with an SLA target date and not completed/cancelled, it finds the **Service Level by Module** row for that job’s module and uses that row’s **At Risk (hours before target)** and **Breach Grace (minutes after target)**. It compares current time to the target → sets **SLA Status** to On Track, At Risk, or Breached. If no enabled row for that module, defaults (24 hours, 0 minutes) are used.

### 7.4 Summary by module

| Module | Applicable (service_level selected) | Monitoring (job only) |
|--------|-------------------------------------|------------------------|
| Transport | Transport Order, Transport Job | **Transport Job** |
| Sea Freight | Sea Booking, Sea Shipment (job) | **Sea Shipment** (job) |
| Air Freight | Air Booking, Air Shipment (job) | **Air Shipment** (job) |
| Warehousing | Optional orders, Warehouse Job | **Warehouse Job** |
| Customs | — | Optional link on Declaration for reporting |
| Pricing Center | Sales Quote | — (source only) |

---

This guide describes the full set of Service Level functions: master setup with **Service Level by Module** (one row per module), applicability on Quote/Order/Job, target date from job date per module, SLA status and scheduler (thresholds per module), and monitoring and reporting across Transport, Sea, Air, Warehousing, Customs, and Pricing Center.
