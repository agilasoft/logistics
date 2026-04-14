# Milestone Tracking

**Milestone Tracking** provides a visual timeline of key operational stages for Jobs, Shipments, and Declarations. It complements the Documents tab by surfacing execution progress in the **Milestones** tab. Dashboard and Milestones are separate tabs; document alerts are shown in the Dashboard tab.

Milestones are tracked via **Job Milestone** records linked to the parent document. Each milestone has a status (Planned, Started, Completed) and optional planned/actual start and end dates. The **Logistics Milestone** master defines which milestones apply to each product type (Sea Freight, Air Freight, Transport, Customs).

To access milestone configuration, go to:

**Home > Logistics > Logistics Milestone** (master)

## 1. Prerequisites

Before using Milestone Tracking, it is advised to set up the following:

- [Logistics Milestone](welcome/logistics-milestone) – Master list of milestones (e.g., SF-GATE-IN, SF-LOADED, AF-DEPARTED)
- Job Milestone is automatically available on supported doctypes

## 2. How to Use the Milestones Tab

1. Open a supported document (e.g., Air Shipment, Sea Shipment, Transport Job, Declaration).
2. Go to the **Milestones** tab (Dashboard tab shows status and alerts; Milestones tab shows the milestone flow).
3. The milestone flow is displayed with status indicators (Planned / Started / Completed).
4. Use **Capture Actual Start** or **Capture Actual End** on Job Milestone rows to record actual dates.
5. Document alerts (missing, overdue, expiring) are shown at the top of the milestone view when applicable.

### 2.1 Milestone Flow by Product

**Sea Freight:** Booking Received → Booking Confirmed → Cargo Not Ready → Pick-Up Scheduled → Gate-In at Port → Customs Clearance (Export) → Loaded on Vessel → Departed → In-Transit → Arrived → Discharged → Customs Clearance (Import) → Available for Pick-Up → Out for Delivery → Delivered → Closed

**Air Freight:** Similar flow; milestones filtered by air_freight flag.

**Transport:** Pick-Up → In-Transit → Delivered; milestones filtered by transport flag.

**Declaration (Customs):** Submitted → Under Review → Customs Clearance (Approved) → Released / Rejected

**Warehouse Job:** Uses operation-based flow (Start → Received → Putaway → Pick → Release → End) derived from posted operations on job items, not Job Milestone rows.

## 3. Features

### 3.1 Job Milestone Fields

- **Milestone** – Link to Logistics Milestone
- **Status** – Planned, Started, Completed
- **Planned Start**, **Planned End** – Planned dates
- **Actual Start**, **Actual End** – Captured via actions

### 3.2 Supported Doctypes

- Air Shipment
- Sea Booking
- Sea Shipment
- Sea Consolidation
- Transport Job
- Declaration
- Declaration Order


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocTypes **Job Milestone**, **Logistics Milestone** (subsections below) and their nested child tables, in form order. Columns: **Label** (`field name`), **Type**, **Description**._

### Job Milestone

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Job Type (`job_type`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |
| Job Number (`job_number`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **job_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Milestone (`milestone`) | Link | **Purpose:** Creates a controlled reference to **Logistics Milestone** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Milestone**. Create the master first if it does not exist. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Planned, Started, Completed. |
| `column_break_vxxu` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Planned Start (`planned_start`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Planned End (`planned_end`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `column_break_etry` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Actual Start (`actual_start`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Actual End (`actual_end`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |

### Logistics Milestone

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Icon (`icon`) | Icon | **Purpose:** Visual icon for milestones or workspace navigation. **What to enter:** Pick an icon from the selector. |
| `column_break_rydr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Air Freight (`air_freight`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Sea Freight (`sea_freight`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Transport (`transport`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Customs (`customs`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Document Management](welcome/document-management)
- [Sea Shipment](welcome/sea-shipment)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Declaration](welcome/declaration)
