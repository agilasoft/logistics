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

### 3.4 Manage Requests

1. Create **Special Project Request** from the project
2. Add **Resource Requests**, **Product Requests**, **Equipment Requests**
3. Submit and approve; track fulfillment status
4. Use **Create Order** (or similar) to create bookings/orders from requests and link them to the project

### 3.5 Track Deliveries and Billing

1. **Deliveries** tab – Track Full, Partial, Milestone, or Proof of Delivery with status (Pending, Scheduled, Completed, Delayed)
2. **Billings** tab – Define Milestone, Interim, Final, or Ad-hoc billings; link Sales Invoice when invoiced

## 4. Features

### 4.1 ERPNext Project Integration

- **Auto-creation** – ERPNext Project is created on first save of Special Project
- **Project Type** – Set in [Special Project Settings](welcome/special-project-settings)
- **Status sync** – Special Project status maps to ERPNext Project (Draft/Scoping/Booked/etc. → Open; Completed → Completed; Cancelled → Cancelled)
- **Task management** – Use ERPNext Project for tasks, timesheets, and project billing

### 4.2 Scoping Activities

- **Types** – Ocular Inspection, Road Inspection, Technical Consultation
- **Cost tracking** – Record cost per activity; mark **Charged to Project** when booked
- **Auto-charge** – When status changes to Booked/Approved/Planning/In Progress, completed scoping activities are auto-marked as charged

### 4.3 Activity Planning

- **Activity types** – Transport, Warehousing, Air Freight, Sea Freight, Customs, Special Handling, Documentation, Other
- **Job linking** – Link activities to Transport Job, Warehouse Job, Air Shipment, Sea Shipment, or Declaration
- **Planned vs actual** – Track planned and actual start/end dates per activity

### 4.4 Resource Management

- **Resource types** – Personnel, Equipment, Third Party, Other
- **In-house vs supplier** – Mark in-house or link Supplier
- **Planned/actual hours** – Track hours and cost per unit

### 4.5 Product and Equipment

- **Products** – Item, quantity, UOM, weight, volume, special handling, temperature range, hazmat class
- **Equipment** – Link to Special Handling Equipment Type; track planned/actual usage and cost

### 4.6 Jobs Tab

- Link Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration
- Track planned cost, actual cost, planned revenue, actual revenue per job

### 4.7 Deliveries Tab

- **Delivery types** – Full, Partial, Milestone, Proof of Delivery
- **Status** – Pending, Scheduled, Completed, Delayed
- **Items delivered** – Free-text or structured description of delivered items

### 4.8 Billings Tab

- **Bill types** – Milestone, Interim, Final, Ad-hoc
- **Status** – Pending, Invoiced, Paid
- **Sales Invoice** – Link when invoiced; invoice date tracked

### 4.9 Dashboard and Reports

- **Number cards** – Active Projects, Total Projects, Open Requests
- **Chart** – Special Projects by Status
- **Quick access** – Project list, Request list, Settings

## 5. Workspace Structure

### 5.1 Quick Access

- **Project** – Special Project list
- **Request** – Special Project Request list
- **Settings** – Special Project Settings

### 5.2 Masters

- [Special Handling Type](welcome/special-handling-type) – Handling types (e.g. DG, temperature-controlled)
- [Special Handling Equipment Type](welcome/special-handling-equipment-type) – Equipment types for project equipment

## 6. Related Topics

- [Getting Started](welcome/getting-started)
- [Sales Quote](welcome/sales-quote)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- [Air Shipment](welcome/air-shipment)
- [Sea Shipment](welcome/sea-shipment)
- [Declaration](welcome/declaration)
- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
