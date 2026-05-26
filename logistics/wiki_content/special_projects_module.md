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

### 3.2 Jobs Tab – Internal Job Detail

The **Jobs** tab uses the shared **Internal Job Detail** child table (not legacy per-mode activity tabs on the Special Project form):

1. **Linked operational legs** – Rows with service type Air, Sea, Transport, Customs, or Warehousing reference the relevant order/booking (**Job Type** / **Job No**). Planned and actual cost and revenue can be tracked per row.
2. **Special Project resource rows** – Rows with service type **Special Project** capture site, manpower, equipment, handling, and notes for programme-only resources (these rows do not resolve to a shipment/declaration job for milestone maps).
3. Alternatively, set the **Project** field on operational documents directly; milestones from those jobs are aggregated on the **Milestones** tab when rows resolve to shipments/jobs.

### 3.3 Programme Tasks (Optional)

1. On the **Lifecycle** tab, add a **Lifecycle Jobs** row with **Service Type = Special Project** (leave **Job No** empty until created).
2. On the Special Project form, use **Create > Booking / Order**. In the dialog, open the card for that line and click **Create**, then enter **Order Title**. The system creates a **Project Order** (programme header and Special Project charge lines copied), links it on **Job No**, and opens the order.
3. Add milestones and documents on the order if needed, then use **Create > Project Job** on the Project Order to create the execution job (or create a **Project Job** standalone linked to the programme).

### 3.4 Track Billing

1. **Charges** tab – Programme charge lines (same pattern as Sea Shipment charges); link Sales Invoice when invoiced

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

Same pattern as **Sea Shipment** milestones: optional **Milestone Template**, editable **Milestones** child table (**Special Project Milestone** rows with planned/actual dates and automation metadata from the template), and a graphical timeline from **Get Milestones** / template population. The **Dashboard** tab still shows a read-only rollup of milestones from linked logistics jobs (via **Internal Job Detail**); programme-level milestones live on the Milestones tab.

### 4.3 ERPNext Project Integration

- **Auto-creation** – ERPNext Project is created on first insert of Special Project (unless an existing Project is linked)
- **Project Type** – Default from [Special Project Settings](welcome/special-project-settings) when creating the Project
- **Status sync** – Special Project status maps to ERPNext Project (Draft/Scoping/Booked/etc. → Open; Completed → Completed; Cancelled → Cancelled)
- **Task management** – Use ERPNext Project for tasks, timesheets, and project billing

### 4.4 Scoping Activities

- **Types** – Ocular Inspection, Road Inspection, Technical Consultation
- **Cost tracking** – Record cost per activity; mark **Charged to Project** when booked
- **Auto-charge** – When status changes to Booked/Approved/Planning/In Progress, completed scoping activities can be auto-marked as charged

### 4.5 Jobs Tab and Cost & Revenue

- **Internal Job Detail** – One grid for multimodal legs and programme resource lines; aligns with **General Job** and other documents using the same child DocType
- **Resolution** – Standard service rows resolve to operational jobs for dashboard milestone rollup and maps; **Special Project** service rows are resource-only
- **Cost & Revenue Summary** – Collapsible HTML summary for totals and breakdown

### 4.6 Documents Tab

- **Document Checklist** – Project-level documents (permits, DG certs, customs docs, contracts)
- **Document Template** – Override default [Document List Template](welcome/document-list-template); leave empty to use product default
- Uses **Job Document** child table; supports document status and attachments
- See [Document Management](welcome/document-management) for document types and templates

### 4.7 Site Materials Tab

Programme-level **site inventory** (one Site Materials grid covering tracked requirements and always-along packages, plus receipts and partial shipment picks from **Create → Booking / Order**). See the dedicated user guide: [Special Project — Site Materials](welcome/special-project-site-materials).

### 4.8 Billings Tab

- **Bill types** – Milestone, Interim, Final, Ad-hoc
- **Status** – Pending, Invoiced, Paid
- **Sales Invoice** – Link when invoiced; invoice date tracked

### 4.9 More Info Tab

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
- [Special Project — Site Materials](welcome/special-project-site-materials)
