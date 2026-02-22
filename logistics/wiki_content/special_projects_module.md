# Special Projects Module

**Special Projects** manages complex, one-off logistics projects that span multiple modes (air, sea, transport, warehousing, customs) and require scoping, resource planning, equipment, and milestone-based billing. It integrates with ERPNext Project for task management and links logistics jobs across the platform to a single project.

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

A **Special Project** is the main document. On save, an ERPNext **Project** is auto-created (or you can link an existing one). The Special Project ID uses the ERPNext Project ID (e.g. PROJ-0001) when auto-created, or the fallback series SP-.#####.

### 2.2 Special Project Request

A **Special Project Request** captures internal requests for resources, products, or equipment within a project. Use it to track fulfillment of resource requests, product requests, and equipment requests with statuses: Draft → Submitted → Approved → Partially Fulfilled → Fulfilled.

### 2.3 Integration with Logistics Doctypes

Logistics documents (Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, etc.) have a **Project** field. Link them to the Special Project’s ERPNext Project so all jobs appear under one project for billing and reporting.

## 3. Typical Workflow

### 3.1 Create and Scope a Project

1. Go to **Special Projects > Project > New**
2. Enter **Project Name**, **Customer**, **Sales Quote** (optional)
3. Set **Status** (Draft → Scoping → Booked → Planning → Approved → In Progress → Completed)
4. Add **Scoping Activities** (Ocular Inspection, Road Inspection, Technical Consultation) with dates, costs, and status
5. **Save** – an ERPNext Project is auto-created and linked

### 3.2 Plan Activities and Resources

1. **Activities** tab – Define activities (Transport, Warehousing, Air Freight, Sea Freight, Customs, Special Handling, Documentation) with planned/actual dates and link to jobs
2. **Resources** tab – Add personnel, equipment, third-party resources with planned hours and costs
3. **Products** tab – Add items with quantities, special handling, temperature, hazmat
4. **Equipment** tab – Add equipment types with planned/actual usage windows and costs

### 3.3 Link Logistics Jobs

1. In **Jobs** tab – Add Transport Job, Warehouse Job, Air Shipment, Sea Shipment, or Declaration with planned/actual cost and revenue
2. Or set the **Project** field on the job document directly – jobs with the same project appear under the Special Project

### 3.4 Manage Requests and Create Orders

1. Create **Special Project Request** from the project
2. Add **Resource Requests**, **Product Requests**, **Equipment Requests**
3. For **Product Requests**, set **Fulfillment Type** (Inbound, Release, Transport, Air Freight, Sea Freight, Transfer, VAS)
4. Use **Create Order** actions to create Inbound Order, Release Order, Transfer Order, Transport Order, Air Booking, or Sea Booking from product requests – orders are linked to the project
5. Use **Link Existing Order** to attach an order created outside the request flow to the request and set its project

### 3.5 Track Deliveries and Billing

1. **Deliveries** tab – Track Full, Partial, Milestone, or Proof of Delivery with status (Pending, Scheduled, Completed, Delayed)
2. **Billings** tab – Define Milestone, Interim, Final, or Ad-hoc billings; link Sales Invoice when invoiced

## 4. Features

### 4.1 Dashboard Tab

The Dashboard tab provides a compact overview of project status, resources, jobs, billings, and costs:

- **Status** – Current status (Draft, Scoping, Booked, Planning, Approved, In Progress, On Hold, Completed, Cancelled) with color-coded badge
- **Resources** – Count, planned vs actual hours
- **Jobs** – Count, planned/actual cost and revenue
- **Billings** – Items count, planned amount, pending vs invoiced/paid
- **Deliveries** – Total, pending, completed
- **Summary** – Budget (cost), actual cost, budget (revenue), actual revenue

Use the Dashboard to monitor project health, resource utilization, and cost vs budget at a glance.

### 4.2 ERPNext Project Integration

- **Auto-creation** – ERPNext Project is created on first save of Special Project
- **Project Type** – Set in [Special Project Settings](welcome/special-project-settings)
- **Status sync** – Special Project status maps to ERPNext Project (Draft/Scoping/Booked/etc. → Open; Completed → Completed; Cancelled → Cancelled)
- **Task management** – Use ERPNext Project for tasks, timesheets, and project billing

### 4.3 Scoping Activities

- **Types** – Ocular Inspection, Road Inspection, Technical Consultation
- **Cost tracking** – Record cost per activity; mark **Charged to Project** when booked
- **Auto-charge** – When status changes to Booked/Approved/Planning/In Progress, completed scoping activities are auto-marked as charged

### 4.4 Activity Planning

- **Activity types** – Transport, Warehousing, Air Freight, Sea Freight, Customs, Special Handling, Documentation, Other
- **Job linking** – Link activities to Transport Job, Warehouse Job, Air Shipment, Sea Shipment, or Declaration
- **Planned vs actual** – Track planned and actual start/end dates per activity

### 4.5 Resource Management

- **Resource types** – Personnel, Equipment, Third Party, Other
- **In-house vs supplier** – Mark in-house or link Supplier
- **Planned/actual hours** – Track hours and cost per unit

### 4.6 Product and Equipment

- **Products** – Item, quantity, UOM, weight, volume, special handling, temperature range, hazmat class
- **Equipment** – Link to Special Handling Equipment Type; track planned/actual usage and cost

### 4.7 Jobs Tab

- Link Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration
- Track planned cost, actual cost, planned revenue, actual revenue per job
- **Cost & Revenue Summary** – Collapsible section showing totals (planned/actual cost, revenue, margin) and breakdown by job type

### 4.8 Documents Tab

- **Document Checklist** – Project-level documents (permits, DG certs, customs docs, contracts)
- **Document Template** – Override default [Document List Template](welcome/document-list-template); leave empty to use product default
- Uses **Job Document** child table; supports document status and attachments
- See [Document Management](welcome/document-management) for document types and templates

### 4.9 Deliveries Tab

- **Delivery types** – Full, Partial, Milestone, Proof of Delivery
- **Status** – Pending, Scheduled, Completed, Delayed
- **Items delivered** – Free-text or structured description of delivered items

### 4.10 Billings Tab

- **Bill types** – Milestone, Interim, Final, Ad-hoc
- **Status** – Pending, Invoiced, Paid
- **Sales Invoice** – Link when invoiced; invoice date tracked

### 4.11 More Info Tab

- **Client Notes** – Notes visible to customer
- **Internal Notes** – Internal-only notes
- **Terms and Conditions** – Link to Terms and Conditions master
- **Service Level Agreement** – Link to Logistics Service Level for project-level commitments

### 4.12 Create Order from Request

From a Special Project Request, create logistics orders from **Product Requests** based on **Fulfillment Type**:

| Fulfillment Type | Creates |
|------------------|---------|
| Inbound | Inbound Order |
| Release | Release Order |
| Transfer | Transfer Order |
| Transport | Transport Order |
| Air Freight | Air Booking |
| Sea Freight | Sea Booking |

Orders are linked to the Special Project’s ERPNext Project. Use **Link Existing Order** to attach an order created outside the request flow.

## 5. Workspace Structure

### 5.1 Number Cards and Chart

- **Active Projects** – Projects in progress
- **Total Projects** – All projects
- **Open Requests** – Unfulfilled requests
- **Chart** – Special Projects by Status

### 5.2 Quick Access

- **Project** – Special Project list
- **Request** – Special Project Request list
- **Active Projects** – Filtered list (status: In Progress, Planning, Approved, Booked, Scoping)

### 5.3 Reports

**Operational**

- **Projects Report** – Project list with filters
- **Request Fulfillment** – Open requests, status, fulfillment %
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
- **Special Project**, **Request** – Main doctypes
- **Operational** – Projects Report, Request Fulfillment, Delivery Status, Billing Status
- **Cost Analysis** – Cost vs Revenue, Profitability
- **Strategic Planning** – By Customer, Pipeline
- **Setup** – Handling Type, Equipment Type
- **Settings** – Special Project Settings

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
