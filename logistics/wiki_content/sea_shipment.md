# Sea Shipment

**Sea Shipment** is the operational shipment document for sea freight. It is created from a [Sea Booking](welcome/sea-booking) and tracks execution, milestones, charges, containers, and documents. Supports Dashboard and Milestones tabs.

To access: **Home > Sea Freight > Sea Shipment**

## 1. Prerequisites

- [Sea Booking](welcome/sea-booking)
- [Logistics Milestone](welcome/logistics-milestone) (for milestone tracking)
- [Document List Template](welcome/document-list-template) (for documents)

## 2. Key Features

- **Dashboard Tab** – Document alerts (missing, overdue, expiring), status summary
- **Milestones Tab** – Visual timeline of operational stages (Gate-In, Loaded, Departed, etc.)
- **Charges** – Selling and cost charges; supports weight and quantity breaks (unified calculation engine). Each charge row has **Estimated Revenue** and **Estimated Cost** (from the booking, used for WIP and accrual) and **Actual Revenue** and **Actual Cost** (calculated on the shipment; used for Sales Invoice and Purchase Invoice when present). Use **Recalculate All Charges** to refresh actual amounts from the calculation method; estimated amounts are not changed.
- **Containers** – Container assignments for FCL
- **Documents** – Job Document child table; Populate from Template
- **Create Change Request** – Add additional charges via [Change Request](welcome/change-request)
- **Profitability (from GL)** – Revenue, cost, gross profit, WIP, accrual from General Ledger when Job Costing Number and Company are set (see [Job Management Module](welcome/job-management-module))

## 3. Workflow

1. Create Sea Shipment from Sea Booking.
2. Track milestones (Gate-In at Port, Loaded on Vessel, Departed, etc.).
3. Upload documents in Documents tab.
4. Create [Sea Consolidation](welcome/sea-consolidation) if House Type = Consolidation.
5. Create [Master Bill](welcome/master-bill) for consolidation.
6. Create Sales Invoice for billing.

## 4. Related Topics

- [Sea Booking](welcome/sea-booking)
- [Sea Consolidation](welcome/sea-consolidation)
- [Master Bill](welcome/master-bill)
- [Milestone Tracking](welcome/milestone-tracking)
- [Document Management](welcome/document-management)
- [Change Request](welcome/change-request)
- [Job Management Module](welcome/job-management-module)
