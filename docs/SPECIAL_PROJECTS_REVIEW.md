# Special Projects Module – Review & Recommendations

## 1. Module Review

### 1.1 Overview

The **Special Projects** module manages complex, one-off logistics projects spanning multiple modes (air, sea, transport, warehousing, customs). It provides:

- **Special Project** – Main document with scoping, activities, resources, products, equipment, jobs, deliveries, and billings
- **Special Project Request** – Internal requests for resources, products, and equipment with fulfillment tracking
- **ERPNext Project integration** – Auto-creation of projects for task management and billing
- **Cross-module job linking** – Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration linked via Project field

### 1.2 Current Structure

| Component | Current State |
|-----------|---------------|
| **Workspace** | Number cards (Active, Total, Open Requests), chart (by Status), shortcuts (Project, Request), Settings link |
| **Sidebar** | Home, Settings (2 items only) |
| **Masters** | Special Project Settings, Special Handling Type, Special Handling Equipment Type |
| **Request API** | Create Inbound/Release/Transfer Order, Transport Order, Air/Sea Booking from Product Requests |

### 1.3 Gaps vs. Other Modules

Compared to Transport, Air Freight, and Warehousing:

- **Sidebar** – Minimal (2 items vs. 15–30+ in other modules)
- **Masters** – Special Handling Type and Special Handling Equipment Type not in sidebar
- **Reports** – No dedicated reports
- **Dashboard** – No separate Dashboard link
- **Section grouping** – No collapsible sections (Job Management, Setup, Reports, Settings)

---

## 2. Suggested Added Features

### 2.1 Documents Tab Integration

**Rationale:** Special Projects involve complex documentation (permits, DG certs, customs docs, contracts). Per [DOCUMENTS_FEATURE_DESIGN.md](DOCUMENTS_FEATURE_DESIGN.md), the Documents tab is available on bookings, jobs, and shipments.

**Recommendation:** Add a **Documents** tab to Special Project:

- Use `Job Document` child table (or equivalent) for project-level documents
- Template: "Special Project Standard" – Commercial Invoice, Packing List, DG Declaration, Customs docs, etc.
- Link to Document List Template for Special Projects product type
- Surface document alerts (missing, overdue) in a Dashboard/Summary section on the project form

### 2.2 Milestone Tracking

**Rationale:** Per [MILESTONE_TRACKING_DESIGN.md](MILESTONE_TRACKING_DESIGN.md), milestones provide a visual timeline of key stages. Special Projects span multiple jobs; a project-level milestone view would show overall progress.

**Recommendation:** Add **Milestones** tab to Special Project:

- Aggregate milestones from linked jobs (Transport Job, Air/Sea Shipment, Declaration) into a project-level timeline
- Or define project-specific milestones (Scoping Done → Planning Approved → Jobs Booked → In Progress → Delivered → Invoiced)
- Reuse `Logistics Milestone` and `Job Milestone` where applicable; add project-level milestone model if needed

### 2.3 Cost & Revenue Summary

**Rationale:** Projects track planned vs. actual cost/revenue per job, but there is no consolidated view.

**Recommendation:** Add **Cost & Revenue Summary** section or tab:

- Totals: Planned Cost, Actual Cost, Planned Revenue, Actual Revenue, Margin
- Breakdown by job type (Transport, Air, Sea, Warehouse, Customs)
- Variance indicators (planned vs. actual)
- Link to ERPNext Project for timesheet and expense costs

### 2.4 Project Timeline / Gantt View

**Rationale:** Activities, resources, and equipment have planned/actual dates. A visual timeline would improve planning.

**Recommendation:** Add **Timeline** or **Gantt** view:

- Show activities, scoping activities, and key milestones on a timeline
- Use Frappe Gantt or similar; or a simplified HTML timeline in a tab
- Filter by status (planned vs. actual)

### 2.5 Request Fulfillment Dashboard

**Rationale:** Open Requests number card exists, but there is no drill-down or fulfillment overview.

**Recommendation:** Add **Request Fulfillment** report or workspace block:

- List open requests with status, required-by date, fulfillment %
- Filter by project, status, priority
- Quick actions: Create Order, Link Order, Mark Fulfilled

### 2.6 Project Templates

**Rationale:** Similar projects (e.g. DG shipments, temperature-controlled) repeat the same structure.

**Recommendation:** Add **Special Project Template** doctype:

- Define default activities, resource types, equipment types, document requirements
- "Create from Template" on Special Project – pre-populate tabs
- Reduces data entry for recurring project types

### 2.7 Notifications & Alerts

**Rationale:** Projects have status changes, delivery dates, billing milestones. Users need reminders.

**Recommendation:** Add notification rules:

- Status change (e.g. Scoping → Booked) – notify project owner
- Delivery due – remind X days before
- Billing milestone due – remind when delivery completed
- Overdue scoping activities – alert project manager

### 2.8 Project Reports

**Rationale:** Other modules have dedicated reports (e.g. Air Shipment Status, Vehicle Utilization).

**Implemented** – Reports are categorized in the workspace:

- **Operational:** Projects Report, Request Fulfillment, Delivery Status, Billing Status
- **Cost Analysis:** Cost vs Revenue, Profitability (group by Customer/Status/None)
- **Strategic Planning:** By Customer, Pipeline (projects by stage)

### 2.9 Quick Filters on Workspace

**Rationale:** Workspace shortcuts open full lists. Power users need filtered views.

**Recommendation:** Add shortcut variants with `stats_filter`:

- "My Projects" – assigned to me
- "Active Projects" – status In Progress, Planning, Approved
- "Overdue Deliveries" – deliveries with status Delayed
- "Pending Billings" – billings with status Pending

### 2.10 Link Existing Order to Request

**Rationale:** API has `link_existing_order_to_request` – useful when orders are created outside the request flow.

**Recommendation:** Ensure UI exposes this clearly (e.g. "Link Existing Order" button with order type selector). Document in user guide.

---

## 3. Workspace Organization

### 3.1 Current Workspace Content

```
[Active Projects] [Total Projects] [Open Requests]
[Chart: Special Projects by Status]
---
Quick Access
[Project] [Request]
---
Links: Settings
```

### 3.2 Recommended Workspace Layout

| Block | Content |
|-------|---------|
| **Row 1** | Number cards: Active Projects, Total Projects, Open Requests, Overdue Deliveries (new) |
| **Row 2** | Chart: Special Projects by Status |
| **Row 3** | Header: Quick Access |
| **Row 4** | Shortcuts: Project, Request, My Projects (filtered), Pending Billings (filtered) |
| **Row 5** | Header: Masters |
| **Row 6** | Shortcuts: Special Handling Type, Special Handling Equipment Type |
| **Row 7** | Header: Reports |
| **Row 8** | Shortcuts: Special Projects Report, Request Fulfillment Report (when added) |
| **Links** | Settings (Special Project Settings) |

### 3.3 New Number Card (Optional)

- **Overdue Deliveries** – Count of Special Project Delivery where status = Delayed and delivery_date < today

---

## 4. Sidebar Organization

### 4.1 Current Sidebar

```
Home → Special Projects
Settings → Special Project Settings
```

### 4.2 Recommended Sidebar Structure

Follow the pattern used by Transport, Air Freight, and Warehousing: **Home**, **Section groups**, **Settings**.

```
Home                    → Special Projects (Workspace)
---
Project Management       [Section Break]
  Special Project       → Special Project
  Request               → Special Project Request
---
Setup                    [Section Break]
  Handling Type         → Special Handling Type
  Equipment Type        → Special Handling Equipment Type
---
Reports                  [Section Break]
  Projects Report       → Special Projects Report (when added)
  Request Fulfillment   → Request Fulfillment Report (when added)
---
Settings                 [Section Break]
  Special Project Settings → Special Project Settings
```

### 4.3 Sidebar JSON Structure (Reference)

Use `child: 1` for items under a section, `child: 0` for section headers. Use `indent: 1` for Section Break, `indent: 0` for top-level items.

Example items:

| Label | Type | link_to | link_type |
|-------|------|---------|-----------|
| Home | Link | Special Projects | Workspace |
| Project Management | Section Break | - | - |
| Special Project | Link | Special Project | DocType |
| Request | Link | Special Project Request | DocType |
| Setup | Section Break | - | - |
| Handling Type | Link | Special Handling Type | DocType |
| Equipment Type | Link | Special Handling Equipment Type | DocType |
| Reports | Section Break | - | - |
| Settings | Section Break | - | - |
| Special Project Settings | Link | Special Project Settings | DocType |

### 4.4 Icon Suggestions

- Home: `home`
- Project Management: `folder` or `grid`
- Setup: `database`
- Reports: `sheet`
- Settings: `settings`

---

## 5. Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P1 | Sidebar reorganization (add sections, masters) | Low | High – improves discoverability |
| P1 | Workspace: add Masters shortcuts, Overdue Deliveries card | Low | Medium |
| P2 | Documents tab on Special Project | Medium | High |
| P2 | Project reports (list + summary) | Medium | High |
| P3 | Cost & Revenue Summary section | Medium | Medium |
| P3 | Milestone aggregation/timeline | High | Medium |
| P4 | Project Templates | High | Medium |
| P4 | Notifications & alerts | Medium | Medium |
| P5 | Gantt/Timeline view | High | Low–Medium |

---

## 6. Summary

The Special Projects module is functionally rich but under-exposed in the UI. The sidebar and workspace are minimal compared to other logistics modules. Recommended next steps:

1. **Immediate:** Reorganize sidebar with sections (Project Management, Setup, Reports, Settings) and add masters (Special Handling Type, Special Handling Equipment Type).
2. **Short-term:** Add Documents tab, project reports, and Cost & Revenue Summary.
3. **Medium-term:** Milestone tracking, project templates, and notifications.

*Document Version: 1.0*  
*Last Updated: 2025-02-22*
