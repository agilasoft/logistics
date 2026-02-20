# Special Projects — Reports

## Current Status

**No report DocTypes exist** in the Special Projects module. The reports below are **designed** (see `SPECIAL_PROJECTS_MODULE_DESIGN.md` Section 14) and are categorized as **Operational**, **Cost Analysis**, or **Insights**. They are listed as a specification for implementation.

---

## Categorization Summary

| Category | Reports | Purpose |
|----------|---------|---------|
| **Operational** | Special Project Status, Special Project Delivery Status, Special Project Billing Status, Special Project Request Status | Day-to-day execution, milestones, fulfillment, and billing tracking |
| **Cost Analysis** | Special Project Cost Summary, Special Project Job Costing | Cost breakdown, planned vs actual, margins |
| **Insights** | Special Project Status (also), dashboard charts, number cards | Overview, trends, and at-a-glance metrics |

---

## Operational Reports

### 1. Special Project Status

| Attribute | Value |
|-----------|--------|
| **Category** | Operational (also used for Insights) |
| **Status** | Not implemented |
| **Description** | List of Special Projects with status, progress, and cost summary. |
| **Suggested filters** | Status, Customer, Date range (start_date / end_date), Priority |
| **Suggested columns** | Project name, Customer, Status, Priority, Start Date, End Date, Planned Start, Planned End, Linked ERPNext Project, (optional) % activities completed, (optional) total cost / revenue when costing roll-up exists |
| **Data source** | Special Project |
| **Notes** | Can be a simple List Report (query report) or a Report Builder report on Special Project. Progress and cost columns require computed/aggregate logic once Refresh Costs and project-level costing are implemented. |

---

### 2. Special Project Delivery Status

| Attribute | Value |
|-----------|--------|
| **Category** | Operational |
| **Status** | Not implemented |
| **Description** | Delivery milestones and status across projects. |
| **Suggested filters** | Special Project, Status (Pending / Scheduled / Completed / Delayed), Delivery Type, Date range |
| **Suggested columns** | Special Project, Sequence, Delivery Date, Delivery Type, Status, Description, Delivery Location, (optional) Proof of Delivery |
| **Data source** | Special Project Delivery (child of Special Project). |
| **Notes** | Can be a Report Builder report on **Special Project Delivery** (with parent Special Project in filters/columns), or a query report joining Special Project + Deliveries. |

---

### 3. Special Project Billing Status

| Attribute | Value |
|-----------|--------|
| **Category** | Operational |
| **Status** | Not implemented |
| **Description** | Billing milestones and invoice status per project. |
| **Suggested filters** | Special Project, Status (Pending / Invoiced / Paid), Bill Type, Date range |
| **Suggested columns** | Special Project, Sequence, Bill Type, Milestone Description, Planned Amount, Currency, Status, Sales Invoice, Invoice Date |
| **Data source** | Special Project Billing (child of Special Project). |
| **Notes** | Can be a Report Builder report on **Special Project Billing** with parent project in filters/columns, or a query report. |

---

### 4. Special Project Request Status

| Attribute | Value |
|-----------|--------|
| **Category** | Operational |
| **Status** | Not implemented |
| **Description** | Requests by project and fulfillment status (resource, product, equipment requests). |
| **Suggested filters** | Special Project, Request Status (Draft / Submitted / Approved / Partially Fulfilled / Fulfilled / Cancelled), Priority, Date range |
| **Suggested columns** | Request name, Special Project, Request Date, Required By, Requested By, Status, Priority, (optional) counts or status of Resource / Product / Equipment request lines |
| **Data source** | Special Project Request + optional roll-up from child tables (Resource Request, Product Request, Equipment Request) for fulfillment detail. |
| **Notes** | Can be a List Report or Report Builder on **Special Project Request**. For “unfulfilled requests” monitoring, filter status = Pending or Partially Fulfilled. |

---

## Cost Analysis Reports

### 5. Special Project Cost Summary

| Attribute | Value |
|-----------|--------|
| **Category** | Cost Analysis |
| **Status** | Not implemented |
| **Description** | Project-level cost breakdown: scoping costs (charged), resources, equipment, job costs, and total. |
| **Suggested filters** | Special Project, Customer, Date range |
| **Suggested columns** | Project, Customer, Scoping Cost (charged), Resource Cost, Equipment Cost, Job Cost (sum of linked jobs), Other/Ad-hoc, Total Cost, (optional) Total Revenue, (optional) Margin |
| **Data source** | Special Project + child tables (Scoping Activities where charged_to_project, Resources, Equipment, Jobs) and linked job charges. |
| **Notes** | Depends on **Project costing roll-up** (and optionally **Refresh Costs**) being implemented. Scoping cost = sum of Scoping Activity `cost` where `charged_to_project = 1`. Job cost = sum of actual costs from Special Project Job rows (from linked Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration charges). |

---

### 6. Special Project Job Costing

| Attribute | Value |
|-----------|--------|
| **Category** | Cost Analysis |
| **Status** | Not implemented |
| **Description** | Per-job cost and revenue for projects: each linked job (Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration) with planned vs actual cost and revenue. |
| **Suggested filters** | Special Project, Job Type, Date range |
| **Suggested columns** | Special Project, Job Type, Job (document name), Activity (if linked), Planned Cost, Actual Cost, Planned Revenue, Actual Revenue, Margin (actual revenue − actual cost) |
| **Data source** | Special Project Job (child of Special Project) + linked job doctypes and their charges; actual revenue from Sales Invoice linked to job/project. |
| **Notes** | Depends on **Refresh Costs** and **Refresh Revenue** (or equivalent) populating `actual_cost` and `actual_revenue` on Special Project Job. |

---

## Insights (Dashboard, Number Cards, Overview)

| Item | Type | Description |
|------|------|-------------|
| **Special Project Status** | Report | Same as Operational report; use as main overview list. |
| **Special Projects by Status** | Dashboard Chart | Count of Special Projects grouped by status (Bar or Donut). |
| **Active Projects** | Number Card | Count of projects in status In Progress, Planning, Approved, Booked, or Scoping. |
| **Open Requests** | Number Card | Count of Special Project Request not Fulfilled or Cancelled. |
| **Total Projects** | Number Card | Total count of Special Project (draft/submitted). |

---

## Implementation Notes

- **List reports / Report Builder:** Special Project Status, Delivery Status, Billing Status, and Request Status can start as Report Builder reports on the relevant DocTypes (Special Project, Special Project Delivery, Special Project Billing, Special Project Request), with filters and columns as above.
- **Query / script reports:** Special Project Cost Summary and Special Project Job Costing need aggregation from multiple doctypes and from job charges; implement as **Query Report** or **Script Report** in `logistics/special_projects/report/` once costing and refresh logic exist.
- **Placement:** Add report shortcuts to the **Special Projects** workspace under Operational, Cost Analysis, and Insights sections. Number cards and dashboard chart are added to the workspace for at-a-glance metrics.
