# Milestone Tracking

**Milestone Tracking** provides a visual timeline of key operational stages for Jobs, Shipments, and Declarations. It complements the Documents tab by surfacing execution progress in the **Milestones** (or Dashboard) tab, with document alerts rendered alongside the milestone flow.

Milestones are tracked via **Job Milestone** records linked to the parent document. Each milestone has a status (Planned, Started, Completed) and optional planned/actual start and end dates. The **Logistics Milestone** master defines which milestones apply to each product type (Sea Freight, Air Freight, Transport, Customs).

To access milestone configuration, go to:

**Home > Logistics > Logistics Milestone** (master)

## 1. Prerequisites

Before using Milestone Tracking, it is advised to set up the following:

- [Logistics Milestone](welcome/logistics-milestone) – Master list of milestones (e.g., SF-GATE-IN, SF-LOADED, AF-DEPARTED)
- Job Milestone is automatically available on supported doctypes

## 2. How to Use the Milestones Tab

1. Open a supported document (e.g., Air Shipment, Sea Shipment, Transport Job, Declaration).
2. Go to the **Milestones** tab (or Dashboard tab where milestones are shown).
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
- Sea Shipment
- Transport Job
- Declaration
- General Job (optional)

## 4. Related Topics

- [Document Management](welcome/document-management)
- [Sea Shipment](welcome/sea-shipment)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Declaration](welcome/declaration)
