# Special Projects Module

**Special Projects** manages complex, one-off logistics programs that span multiple modes (air, sea, transport, warehousing, customs) and require scoping, milestone-based delivery and billing, and a shared ERPNext **Project** for operational roll-up. It integrates with **Internal Job Detail** (same pattern as [General Job](welcome/general-job)), **Project Order** / **Project Job** for program-level tasks and charges, and links logistics jobs across the platform to one project.

To access the Special Projects workspace, go to:

**Home > Special Projects**

## 1. Prerequisites

Before using Special Projects, set up the following:

- [Special Project Settings](welcome/special-project-settings) – Default Project Type for ERPNext integration
- [Special Handling Type](welcome/special-handling-type) – Handling types for products (e.g. DG, temperature-controlled)
- [Special Handling Equipment Type](welcome/special-handling-equipment-type) – Equipment types for project equipment
- ERPNext **Project Type** – At least one Project Type (e.g. External) for auto-created projects
- Customer, Item, and User masters in ERPNext

## 2. Key Concepts

### 2.1 Special Project

A **Special Project** is the main programme document. On first insert, an ERPNext **Project** is auto-created (or you can link an existing one). The Special Project ID uses the ERPNext Project ID (e.g. PROJ-0001) when auto-created, or the fallback series SP-.#####. That same ID is what you set on operational documents’ **Project** field (Special Project name = ERPNext Project name).

### 2.2 Project Order and Project Job

- **Project Order** – Programme-level order under a Special Project (series e.g. SPOR-.#####). Holds resources, charges, milestones, and documents; used to spawn **Project Job** records for execution.
- **Project Job** – Operational-style job document for special-project work, with charge lines and profitability tooling aligned with other logistics jobs. Links to **Special Project** and optionally to a **Project Order**.

Use these when work is scoped and billed as programme tasks rather than only as Air/Sea/Transport/Customs/Warehouse legs.

### 2.3 Integration with Logistics Doctypes

Logistics documents (Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, etc.) have a **Project** field. Set it to the programme’s ERPNext **Project** (same name as the **Special Project** document) so milestones, costing, and reporting roll up to one portfolio.

**Sales Quote** can link to a **Special Project** on the Projects tab. When the quote is saved, empty fields on the linked programme are filled from the quote where appropriate (customer and back-link to the quote), similar in spirit to copying **Project** from the quote when creating a [Declaration Order](welcome/declaration-order) from a Sales Quote.

## 3. Typical Workflow

### 3.1 Create and Scope a Project

1. Go to **Special Projects > Project > New** (DocType list label **Special Project**)
2. Enter **Project Name**, **Customer**, **Sales Quote** (optional)
3. Set **Status** (Draft → Scoping → Booked → Planning → Approved → In Progress → Completed)
4. Add **Scoping Activities** (Ocular Inspection, Road Inspection, Technical Consultation) with dates, costs, and status
5. **Save** – an ERPNext Project is auto-created and linked

### 3.2 Services tab

The **Services** tab holds programme legs and resource lines (virtual **Services** grid backed by **Special Project Service** records):

1. **Linked operational legs** — Rows with **Service Type** Air, Sea, Transport, Customs, or Warehousing reference the relevant order/booking (**Job Type** / **Order No**) and, after execution, the shipment or job (**Job No**). Planned and actual cost and revenue roll up per row.
2. **Special Project resource rows** — Rows with **Service Type = Special Project** capture site, manpower, equipment, handling, and notes for programme-only resources (these rows do not resolve to a shipment/declaration job for milestone maps).
3. Alternatively, set the **Project** field on operational documents directly; milestones from those jobs are aggregated on the **Milestones** tab when rows resolve to shipments/jobs.

Use **Create → Booking / Order** to spawn planning documents from **Services** rows. See [Special Project — Delivery Workflow](welcome/special-project-delivery-workflow).

### 3.3 Programme tasks (optional)

1. On **Services**, add a row with **Service Type = Special Project** (leave **Order No** / **Job No** empty until created).
2. On the Special Project form, use **Create → Booking / Order**. In the dialog, open the card for that row and click **Create**, then enter **Order Title**. The system creates a **Project Order**, links it on **Order No**, and opens the order.
3. Add milestones and documents on the order if needed, then create a **Project Job** from the Project Order (or create a **Project Job** standalone linked to the programme).

### 3.4 Track Billing

1. **Charges** tab – Programme charge lines (same pattern as Sea Shipment charges); link Sales Invoice when invoiced
2. When charges are brought in from a linked [Sales Quote](welcome/sales-quote), each row is tagged to the correct programme leg — see [§3.5 Programme charges: Linked Service and Service Line](#35-programme-charges-linked-service-and-service-line) below

### 3.5 Programme charges: Linked Service and Service Line

When you populate charges on a **Special Project** from a **Sales Quote**, each charge row can show two related fields on the **Charges** tab:

| Column | What it means |
| --- | --- |
| **Scope** | Whether the charge belongs to the **main programme** or a **linked leg** (Air, Sea, Transport, Customs, etc.) |
| **Linked Service** | The **original service leg from the Sales Quote** (traceability back to the quote) |
| **Service Line** | The **matching service leg on this Special Project** (used for planning, tagging, and execution on the programme) |

Think of it this way:

- **Linked Service** = where this charge came from on the quote
- **Service Line** = which programme leg this charge belongs to now

Both can be filled at the same time. They answer different questions.

#### How charges flow from Sales Quote to Special Project

**On the Sales Quote**

1. Define **Linked Services** on the quote (Air, Sea, Transport, Customs, etc.).
2. On the **Charges** tab, each charge has **Scope** (`Linked` or `Main`) and, for linked charges, **Linked Service** pointing to the quote leg.

Example on quote **PQ00232**:

| Charge | Scope | Linked Service | Service Type |
| --- | --- | --- | --- |
| Freight (Air) | Linked | IJ-2026-005944 | Air |
| Freight (Sea) | Linked | IJ-2026-005945 | Sea |
| Delivery | Linked | IJ-2026-005946 | Transport |
| Brokerage | Linked | IJ-2026-005947 | Customs |
| PM Fee | Main | *(empty)* | Special Project |

**On the Special Project**

When charges are populated from the quote (for example on **PROJ-0147**):

1. The system creates **Special Project Service** rows on the **Services** tab — one per linked leg, plus any main programme leg.
2. Each charge on the **Charges** tab is tagged to the correct programme leg.

Result on **PROJ-0147**:

| Charge | Scope | Linked Service | Service Line | Service Type |
| --- | --- | --- | --- | --- |
| Freight (Air) | Linked | IJ-2026-005944 | SPS-2026-000052 | Air |
| Freight (Sea) | Linked | IJ-2026-005945 | SPS-2026-000053 | Sea |
| Delivery | Linked | IJ-2026-005946 | SPS-2026-000054 | Transport |
| Brokerage | Linked | IJ-2026-005947 | SPS-2026-000055 | Customs |
| PM Fee | Main | *(empty)* | SPS-2026-000056 | Special Project |

#### What each field is for

**Linked Service (quote reference)** — use when you need to know which **Sales Quote** leg the charge came from, how it was priced on the quote, or for audit traceability. **Linked Service** keeps the quote’s service ID (for example `IJ-2026-005944`). It does not replace the programme’s own service rows.

**Service Line (programme reference)** — use when you plan and execute work on the **Special Project**, link charges to the correct leg on the **Services** tab, create bookings and jobs, or roll up cost and revenue per leg. **Service Line** points to a **Special Project Service** record (for example `SPS-2026-000052`).

#### Scope: Main vs Linked

| Scope | Meaning | Linked Service | Service Line |
| --- | --- | --- | --- |
| **Linked** | Charge belongs to a supporting leg (Air, Sea, Transport, Customs, Warehousing, etc.) | Filled from the quote | Filled with the matching programme service |
| **Main** | Charge belongs to core Special Project work (for example project management fee, site work) | Usually empty | Filled with the main Special Project service row |

If **Scope = Main**, it is normal for **Linked Service** to be blank.

#### What to check on the Charges tab

After populating charges from a Sales Quote, confirm:

1. **Scope** matches the quote (Linked vs Main).
2. **Linked Service** is filled for **Linked** charges (shows the quote leg).
3. **Service Line** is filled for every charge (shows the programme leg).
4. **Service Type** and **Lifecycle Stage** look correct for each row.

If **Service Line** is filled but **Linked Service** is empty on a **Linked** charge, re-populate charges from the quote or ask an administrator to backfill older programmes.

#### Common questions

**Why are Linked Service and Service Line different IDs?**

They refer to different documents:

- **Linked Service** (`IJ-…`) lives on the **Sales Quote**
- **Service Line** (`SPS-…`) lives on the **Special Project**

When the programme is created, the system copies the *relationship* from quote to project. The IDs differ because each document has its own service records.

**I only see Scope = Linked on the quote — where is Linked Service?**

On the Sales Quote **Charges** grid, **Linked Service** may not appear in the default list view. Open the charge row to see it, or add the column to the grid. The value is stored even when the column is hidden.

**Should I edit Linked Service on the Special Project?**

Usually **no**. It is set automatically from the quote for traceability. For programme work, use **Service Line** and the **Services** tab.

**Which field do I use when creating bookings?**

Use the **Services** tab and **Service Line** on charges — not **Linked Service**. Bookings and execution documents are created from programme services (`SPS-…`), not from quote linked services (`IJ-…`).

#### Quick reference

```
Sales Quote                          Special Project
───────────                          ───────────────
Linked Service (IJ-…)    ──────────►  Linked Service (same IJ-…)
       │                                      │
       │ (mapped to)                          ▼
       └──────────────────────────►  Service Line (SPS-…)
                                              │
                                              ▼
                                     Services tab / bookings / jobs
```

## 4. Features

### 4.1 Dashboard Tab

The Dashboard tab provides a compact overview of project status, resources, jobs, billings, and costs:

- **Status** – Current status (Draft, Scoping, Booked, Planning, Approved, In Progress, On Hold, Completed, Cancelled) with color-coded badge
- **Resources** – Count, planned vs actual hours (where applicable)
- **Jobs** – Count, planned/actual cost and revenue
- **Billings** – Items count, planned amount, pending vs invoiced/paid
- **Site materials** – Requirement count, shortfall, on-site fill
- **Summary** – Budget (cost), actual cost, budget (revenue), actual revenue

Use the Dashboard to monitor project health, resource utilization, and cost vs budget at a glance.

### 4.2 Milestones Tab

Same pattern as **Sea Shipment** milestones: optional **Milestone Template**, editable **Milestones** child table (**Special Project Milestone** rows with planned/actual dates and automation metadata from the template), and a graphical timeline from **Get Milestones** / template population. The **Dashboard** tab still shows a read-only rollup of milestones from linked logistics jobs (via **Services** rows); programme-level milestones live on the Milestones tab.

### 4.3 ERPNext Project Integration

- **Auto-creation** – ERPNext Project is created on first insert of Special Project (unless an existing Project is linked)
- **Project Type** – Default from [Special Project Settings](welcome/special-project-settings) when creating the Project
- **Status sync** – Special Project status maps to ERPNext Project (Draft/Scoping/Booked/etc. → Open; Completed → Completed; Cancelled → Cancelled)
- **Task management** – Use ERPNext Project for tasks, timesheets, and project billing

### 4.4 Scoping Activities

- **Types** – Ocular Inspection, Road Inspection, Technical Consultation
- **Cost tracking** – Record cost per activity; mark **Charged to Project** when booked
- **Auto-charge** – When status changes to Booked/Approved/Planning/In Progress, completed scoping activities can be auto-marked as charged

### 4.5 Services tab and Cost & Revenue

- **Services** — One grid for multimodal legs and programme resource lines; each saved row is a **Special Project Service** record
- **Resolution** — Standard service rows resolve to operational jobs for dashboard milestone rollup and maps; **Special Project** service rows are resource-only
- **Cost & Revenue Summary** — Collapsible HTML summary for totals and breakdown (under **Services** tab)

### 4.6 Documents Tab

- **Document Checklist** – Project-level documents (permits, DG certs, customs docs, contracts)
- **Document Template** – Override default [Document List Template](welcome/document-list-template); leave empty to use product default
- Uses **Job Document** child table; supports document status and attachments
- See [Document Management](welcome/document-management) for document types and templates

### 4.7 Fulfillment tab

Programme-level **Packages** and **Deliveries** (tracked requirements, always-along packages, and automatic receipt posting from execution jobs). Partial shipment picks use **Create → Booking / Order** and the **Shipment lines** dialog. See [Special Project — Fulfillment (Packages & Deliveries)](welcome/special-project-packages) and [Special Project — Delivery Workflow](welcome/special-project-delivery-workflow).

### 4.8 Billings Tab

- **Bill types** – Milestone, Interim, Final, Ad-hoc
- **Status** – Pending, Invoiced, Paid
- **Sales Invoice** – Link when invoiced; invoice date tracked

### 4.9 Charges Tab

- Programme charge lines aligned with other logistics jobs (revenue, cost, invoice status)
- **Scope**, **Linked Service**, and **Service Line** when charges come from a [Sales Quote](welcome/sales-quote) — see [§3.5 Programme charges: Linked Service and Service Line](#35-programme-charges-linked-service-and-service-line)
- **Billing Status** at programme level (Not Billed, Partially Billed, Fully Billed)

### 4.10 More Info Tab

- **Client Notes** – Notes visible to customer
- **Internal Notes** – Internal-only notes (also available on Details flow per form layout)
- **Terms and Conditions** – Link to Terms and Conditions master
- **Service Level Agreement** – Link to Logistics Service Level for project-level commitments

## 5. Workspace Structure

### 5.1 Number Cards and Chart

- **Active Projects** – Programmes in In Progress, Planning, Approved, Booked, or Scoping
- **Total Projects** – All Special Project records
- **Early Stage Programs** – Count in Draft or Scoping (early pipeline)
- **Chart** – Special Projects by Status

### 5.2 Quick Access

- **Project** – Special Project list
- **Project Order** / **Project Job** – Programme task order and job documents
- **Active Projects** – Filtered list (status: In Progress, Planning, Approved, Booked, Scoping)

### 5.3 Reports

**Operational**

- **Projects Report** – Project list with filters
- **Delivery Status** – Delivery status by project
- **Billing Status** – Billing status by project

**Cost Analysis**

- **Cost vs Revenue** – Planned vs actual cost and revenue
- **Profitability** – Group by Customer, Status, or none

**Strategic Planning**

- **By Customer** – Projects grouped by customer
- **Pipeline** – Projects by stage

### 5.4 Masters

- **Handling Type** – [Special Handling Type](welcome/special-handling-type) (e.g. DG, temperature-controlled)
- **Equipment Type** – [Special Handling Equipment Type](welcome/special-handling-equipment-type)

### 5.5 Sidebar

The sidebar is organized into sections:

- **Home** – Special Projects workspace
- **Special Project** – Programme list
- **Project Order**, **Project Job** – Task execution DocTypes
- **Operational** – Projects Report, Delivery Status, Billing Status
- **Cost Analysis** – Cost vs Revenue, Profitability
- **Strategic Planning** – By Customer, Pipeline
- **Setup** – Handling Type, Equipment Type
- **Settings** – Special Project Settings


<!-- wiki-field-reference:start -->

## Complete field reference

_Special projects use [General Job](welcome/general-job) and the same **Internal Job Detail** child pattern as other multimodal jobs; open the relevant doc wiki page for the full field table._

<!-- wiki-field-reference:end -->

## 6. Related Topics

- [Getting Started](welcome/getting-started)
- [Sales Quote](welcome/sales-quote)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- [Air Shipment](welcome/air-shipment)
- [Sea Shipment](welcome/sea-shipment)
- [Declaration](welcome/declaration)
- [Document Management](welcome/document-management)
- [Document List Template](welcome/document-list-template)
- [Milestone Tracking](welcome/milestone-tracking)
- [Special Project — Delivery Workflow](welcome/special-project-delivery-workflow)
- [Special Project — Fulfillment (Packages & Deliveries)](welcome/special-project-packages)
