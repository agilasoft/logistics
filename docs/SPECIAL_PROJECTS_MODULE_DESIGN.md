# Special Projects Module — Design Document

## 1. Overview

The **Special Projects** module supports complex, multi-modal logistics engagements that require rigorous planning, coordination of diverse job types, special handling, equipment management, detailed costing, and flexible delivery and billing reporting. Unlike standard order flows (Transport Order → Transport Job, Warehouse Order → Warehouse Job), special projects are typically:

- **Scoping-driven** — pre-booking activities (ocular inspection, road inspection, technical consultations) with costs tracked and charged only when the project is booked
- **One-off or custom** engagements
- **Multi-modal** (transport + warehousing + air/sea freight + customs)
- **Activity-driven** with explicit planning and execution phases
- **Resource-intensive** (staff, equipment, third-party vendors)
- **Require special handling** (temperature, hazardous, oversized, etc.)
- **Multi-delivery** with phased or staged delivery reports
- **Multi-billing** with multiple invoices or billing milestones

---

## 2. Goals

| Goal | Description |
|------|-------------|
| **Rigorous planning** | Define activities, milestones, dependencies, and timelines before execution |
| **Resource management** | Allocate personnel, equipment (in-house vs outsourced), and third-party services |
| **Job orchestration** | Create and link jobs across Transport, Warehousing, Air Freight, Sea Freight, Customs
| **Special handling** | Capture temperature, hazmat, fragile, oversized, and other handling requirements |
| **Equipment tracking** | Manage special handling equipment (cranes, forklifts, reefer units, etc.) |
| **Project costing** | Aggregate project-level costs and margins |
| **Individual job costing** | Cost each job (Transport Job, Warehouse Job, Air Shipment, etc.) separately |
| **Multiple delivery reports** | Support multiple delivery milestones, proof of delivery, and delivery reports |
| **Multiple billings** | Support multiple invoices, milestones, or billing schedules per project |
| **Monitoring** | Visibility into project status, progress, and alerts |
| **Project scoping** | Pre-booking activities (ocular inspection, road inspection, technical consultations) with costs tracked but charged only when project is booked |
| **Resource and product requests** | Formal requests for resources, products, equipment; product requests integrate with logistics orders/bookings with project reference |
| **ERPNext Projects integration** | ERPNext Project auto-created on Special Project insert; use for task management, costing, billing |

---

## 3. Scope

### 3.1 In Scope

- **Special Project** (DocType) — master document for a special project
- **Activity planning** — activities, milestones, resources, dependencies
- **Integration** with Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration
- **Special handling** — temperature, hazmat, dimensions, handling instructions
- **Equipment** — in-house and outsourced equipment
- **Project costing** — roll-up and variance tracking
- **Individual job costing** — per-job cost and revenue
- **Delivery reports** — multiple delivery milestones and reports
- **Multiple billings** — multiple Sales Invoices, billing milestones, or schedules
- **Project scoping** — ocular inspection, road inspection, technical consultations; costs incurred but not charged until project is booked
- **Requests** — for resources, products, equipment; product requests integrated with Transport Order, Air Booking, Sea Booking, Inbound Order, Release Order, Transfer Order, etc., with **project** reference
- **Project link** — **project** (Link to Project) on orders, bookings, jobs, and Sales Invoice for unified project visibility
- **ERPNext Projects integration** — ERPNext Project auto-created on Special Project insert; links for tasks, costing, billing

### 3.2 Out of Scope (Phase 1)

- External project management tools (e.g. MS Project) integration
- Advanced resource scheduling (Gantt charts, resource levelling)
- Real-time asset tracking (GPS/GNSS for equipment)

---

## 4. Document Types

### 4.1 Special Project (Master DocType)

**Purpose:** Central document for a special project. All activities, jobs, resources, equipment, costs, deliveries, and billings are linked to this project.

| Field | Type | Description |
|-------|------|-------------|
| **naming_series** | Select | e.g. `SP-.#####` |
| **project** | Link | **Project** (ERPNext) — auto-created on insert; links to ERPNext Project for task management, costing, billing (read-only; set by system) |
| **project_name** | Data | Short name or title |
| **customer** | Link | Customer |
| **sales_quote** | Link | Optional link to Sales Quote |
| **status** | Select | Draft, Scoping, Booked, Planning, Approved, In Progress, On Hold, Completed, Cancelled |
| **priority** | Select | Low, Normal, High, Urgent |
| **start_date** | Date | Project start |
| **end_date** | Date | Project end |
| **planned_start** | Date | Planned start |
| **planned_end** | Date | Planned end |
| **description** | Small Text | Project description |
| **special_handling_instructions** | Long Text | Overall special handling notes |
| **internal_notes** | Long Text | Internal notes |

**Child tables:**
- **Scoping Activities** — Special Project Scoping Activity (pre-booking; costs charged when project is booked)
- **Activities** — Special Project Activity
- **Resources** — Special Project Resource
- **Products** — Special Project Product
- **Equipment** — Special Project Equipment
- **Jobs** — Special Project Job (links to Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration)
- **Deliveries** — Special Project Delivery
- **Billings** — Special Project Billing

**Related (via link):** Special Project Request — requests are linked via `special_project`; show in "Requests" tab or Related list.

**ERPNext Project:** An ERPNext **Project** record is **automatically created** when a Special Project is inserted. The `project` field is set by the system and links to this created Project. Use **Link Project** only to attach an existing Project (e.g. if auto-creation was skipped or for migration).

---

### 4.2 Special Project Scoping Activity (Child Table)

**Purpose:** Define pre-booking scoping activities—ocular inspection, road inspection, technical consultations—that incur costs during the scoping phase. These costs are **tracked but not charged to the project** until the project is **booked**. Once the project status moves to **Booked** (or **Approved**/ later phases), scoping costs become chargeable and flow into project costing.

| Field | Type | Description |
|-------|------|-------------|
| **scoping_type** | Select | Ocular Inspection, Road Inspection, Technical Consultation |
| **activity_date** | Date | Date the activity was performed |
| **description** | Small Text | Description of the activity |
| **location** | Data | Location or site (e.g. for road inspection route) |
| **assigned_to** | Link | User |
| **cost** | Currency | Cost incurred |
| **currency** | Link | Currency |
| **charged_to_project** | Check | Set when project is booked; indicates cost has been charged to project |
| **charged_date** | Date | Date when cost was charged to project (set on booking) |
| **status** | Select | Planned, In Progress, Completed, Cancelled |
| **notes** | Small Text | Notes |

**Behaviour:**
- During **Scoping** status: costs are recorded but `charged_to_project` remains unchecked.
- When project status changes to **Booked** (or **Approved**): action **Charge Scoping Costs** sets `charged_to_project` = 1 and `charged_date` = today for all completed scoping activities; their costs then flow into project costing.
- Scoping costs can optionally be included in the first billing milestone when the project is booked.

---

### 4.3 Special Project Request (DocType)

**Purpose:** Formal request for resources, products, equipment, or other items needed for the project. Requests can be created from a Special Project and fulfilled by creating or linking to logistics orders/bookings (for products) or by allocation (for resources/equipment).

| Field | Type | Description |
|-------|------|-------------|
| **naming_series** | Select | e.g. `SPR-.#####` |
| **special_project** | Link | Special Project (required) |
| **request_date** | Date | Date of request |
| **required_by** | Date | Required by date |
| **requested_by** | Link | User |
| **status** | Select | Draft, Submitted, Approved, Partially Fulfilled, Fulfilled, Cancelled |
| **priority** | Select | Low, Normal, High, Urgent |
| **description** | Small Text | Overall description |
| **notes** | Long Text | Notes |

**Child tables:**
- **Resource Requests** — Special Project Resource Request
- **Product Requests** — Special Project Product Request (integrated with orders/bookings)
- **Equipment Requests** — Special Project Equipment Request

---

### 4.4 Special Project Resource Request (Child Table)

**Purpose:** Request for personnel, third-party services, or generic resources.

| Field | Type | Description |
|-------|------|-------------|
| **resource_type** | Select | Personnel, Third Party, Other |
| **resource_role** | Data | Role or description (e.g. "Driver", "Crane Operator") |
| **quantity** | Float | Quantity requested |
| **uom** | Link | UOM (e.g. Nos, Hours) |
| **required_from** | Datetime | Required from |
| **required_to** | Datetime | Required to |
| **allocation_status** | Select | Pending, Allocated, Partially Allocated, Cancelled |
| **resource** | Link | Special Project Resource (when allocated; links to project resource) |
| **notes** | Small Text | Notes |

---

### 4.5 Special Project Product Request (Child Table)

**Purpose:** Request for products/items. **Integrated with logistics orders and bookings.** When fulfilled, creates or links to Transport Order, Air Booking, Sea Booking, Inbound Order, Release Order, Transfer Order, etc. Each order/booking carries **special_project** reference.

| Field | Type | Description |
|-------|------|-------------|
| **item** | Link | Item |
| **quantity** | Float | Quantity requested |
| **uom** | Link | UOM |
| **description** | Small Text | Description |
| **weight** | Float | Weight (if applicable) |
| **volume** | Float | Volume (if applicable) |
| **fulfillment_type** | Select | Inbound, Release, Transport, Air Freight, Sea Freight, Transfer, VAS |
| **reference_doctype** | Link | DocType (populated when fulfilled: Inbound Order, Release Order, Transport Order, Air Booking, Sea Booking, Transfer Order, VAS Order) |
| **reference_doc** | Dynamic Link | The order/booking document (options = reference_doctype) |
| **fulfillment_status** | Select | Pending, Ordered, Partially Fulfilled, Fulfilled, Cancelled |
| **notes** | Small Text | Notes |

**Behaviour:**
- **Create Inbound Order from Request** — creates Inbound Order with items from product requests where fulfillment_type = Inbound; sets **project** on Inbound Order
- **Create Release Order from Request** — creates Release Order with items; sets **project** on Release Order
- **Create Transport Order from Request** — creates Transport Order with packages; sets **project** on Transport Order
- **Create Air Booking from Request** — creates Air Booking with packages; sets **project** on Air Booking
- **Create Sea Booking from Request** — creates Sea Booking with packages; sets **project** on Sea Booking
- **Create Transfer Order from Request** — creates Transfer Order with items; sets **project** on Transfer Order
- **Link Existing Order** — link an existing order/booking to the request; sets **project** on that document

**Integration:** All logistics orders/bookings must have **project** (Link to Project) to reference the project. When created from Special Project Request, `project` is set from Special Project.project.

---

### 4.6 Special Project Equipment Request (Child Table)

**Purpose:** Request for special handling equipment (in-house or outsourced).

| Field | Type | Description |
|-------|------|-------------|
| **equipment_type** | Link | Special Handling Equipment Type |
| **quantity** | Float | Quantity requested |
| **required_from** | Datetime | Required from |
| **required_to** | Datetime | Required to |
| **allocation_status** | Select | Pending, Allocated, Partially Allocated, Cancelled |
| **equipment** | Link | Special Project Equipment (when allocated; links to project equipment) |
| **notes** | Small Text | Notes |

---

### 4.7 Special Project Activity (Child Table)

**Purpose:** Define activities for rigorous planning. Each activity has a sequence, dependencies, assigned resources, and timeline.

| Field | Type | Description |
|-------|------|-------------|
| **activity_order** | Int | Sequence (1, 2, 3, …) |
| **activity_name** | Data | Short name |
| **activity_type** | Select | e.g. Transport, Warehousing, Air Freight, Sea Freight, Customs, Special Handling, Documentation, Other |
| **description** | Small Text | Description |
| **status** | Select | Not Started, In Progress, Completed, On Hold, Cancelled |
| **planned_start** | Datetime | Planned start |
| **planned_end** | Datetime | Planned end |
| **actual_start** | Datetime | Actual start |
| **actual_end** | Datetime | Actual end |
| **depends_on** | Link | Special Project Activity (optional; predecessor activity) |
| **assigned_to** | Link | User |
| **resource** | Link | Special Project Resource (optional resource) |
| **job_type** | Select | Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration, None |
| **job** | Dynamic Link | Link to the job (optional; populated when job created) |
| **notes** | Small Text | Notes |

**Validation:** `depends_on` must reference an activity with lower `activity_order` (or same parent).

---

### 4.8 Special Project Resource (Child Table)

**Purpose:** Define resources needed (personnel, equipment, third-party services).

| Field | Type | Description |
|-------|------|-------------|
| **resource_type** | Select | Personnel, Equipment, Third Party, Other |
| **resource_name** | Link | Dynamic Link (Employee, Equipment, Supplier, etc.) |
| **resource_role** | Data | Role or description (e.g. "Project Manager", "Driver") |
| **quantity** | Float | Quantity (e.g. 2 drivers, 1 crane) |
| **uom** | Link | UOM |
| **planned_hours** | Float | Planned hours |
| **actual_hours** | Float | Actual hours |
| **in_house** | Check | In-house or outsourced |
| **supplier** | Link | Supplier (if outsourced) |
| **cost_per_unit** | Currency | Cost per unit |
| **currency** | Link | Currency |
| **notes** | Small Text | Notes |

---

### 4.9 Special Project Product (Child Table)

**Purpose:** Define products or items involved in the project.

| Field | Type | Description |
|-------|------|-------------|
| **item** | Link | Item |
| **quantity** | Float | Quantity |
| **uom** | Link | UOM |
| **description** | Small Text | Description |
| **weight** | Float | Weight |
| **weight_uom** | Link | UOM |
| **volume** | Float | Volume |
| **volume_uom** | Link | UOM |
| **special_handling** | Link | Special Handling Type (optional) |
| **temperature_min** | Float | Temperature range (if applicable) |
| **temperature_max** | Float | Temperature range (if applicable) |
| **hazmat_class** | Data | Hazard class (if applicable) |
| **notes** | Small Text | Notes |

---

### 4.10 Special Handling Type (Master DocType)

**Purpose:** Define types of special handling (temperature, hazmat, oversized, fragile, etc.).

| Field | Type | Description |
|-------|------|-------------|
| **handling_type** | Data | e.g. Temperature Controlled, Hazardous, Oversized, Fragile, High Value |
| **description** | Small Text | Description |
| **requires_equipment** | Check | Whether special equipment is required |
| **requires_certification** | Check | Whether certification is required |
| **default_instructions** | Long Text | Default handling instructions |

---

### 4.11 Special Project Equipment (Child Table)

**Purpose:** Define special handling equipment needed for the project (in-house or outsourced).

| Field | Type | Description |
|-------|------|-------------|
| **equipment_type** | Link | Equipment Type (e.g. Crane, Forklift, Reefer Unit, Cold Chain) |
| **equipment** | Link | Equipment (optional; specific asset if in-house) |
| **in_house** | Check | In-house or outsourced |
| **supplier** | Link | Supplier (if outsourced) |
| **quantity** | Float | Quantity |
| **planned_start** | Datetime | Planned start |
| **planned_end** | Datetime | Planned end |
| **actual_start** | Datetime | Actual start |
| **actual_end** | Datetime | Actual end |
| **cost_per_unit** | Currency | Cost per unit |
| **currency** | Link | Currency |
| **notes** | Small Text | Notes |

---

### 4.12 Special Handling Equipment Type (Master DocType)

**Purpose:** Define types of special handling equipment.

| Field | Type | Description |
|-------|------|-------------|
| **equipment_type** | Data | e.g. Crane, Forklift, Reefer Unit, Cold Chain Container, Hazmat Handler |
| **description** | Small Text | Description |
| **in_house_available** | Check | Whether company has in-house equipment |

---

### 4.13 Special Project Job (Child Table)

**Purpose:** Link jobs from Transport, Warehousing, Air Freight, Sea Freight, and Customs to the project.

| Field | Type | Description |
|-------|------|-------------|
| **job_type** | Select | Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration |
| **job** | Dynamic Link | Link to the job (options = job_type) |
| **activity** | Link | Special Project Activity (optional; links to activity) |
| **sequence** | Int | Sort order |
| **planned_cost** | Currency | Planned cost |
| **actual_cost** | Currency | Planned cost (read-only; calculated from job charges) |
| **planned_revenue** | Currency | Planned revenue |
| **actual_revenue** | Currency | Actual revenue (read-only; from Sales Invoice) |
| **notes** | Small Text | Notes |

**Validation:** `job` must be a valid document of type `job_type`.

---

### 4.14 Special Project Delivery (Child Table)

**Purpose:** Define multiple delivery milestones and reports.

| Field | Type | Description |
|-------|------|-------------|
| **sequence** | Int | Delivery sequence |
| **delivery_date** | Date | Delivery date |
| **delivery_type** | Select | Full, Partial, Milestone, Proof of Delivery |
| **description** | Small Text | Description |
| **status** | Select | Pending, Scheduled, Completed, Delayed |
| **items_delivered** | Long Text | Summary of items delivered |
| **delivery_report** | Attach | Attached delivery report |
| **delivery_location** | Link | Address or Location |
| **proof_of_delivery** | Link | Link to POD (if applicable) |
| **notes** | Small Text | Notes |

---

### 4.15 Special Project Billing (Child Table)

**Purpose:** Define multiple billing milestones or invoices.

| Field | Type | Description |
|-------|------|-------------|
| **sequence** | Int | Billing sequence |
| **bill_type** | Select | Milestone, Interim, Final, Ad-hoc |
| **milestone_description** | Small Text | Description |
| **planned_amount** | Currency | Planned amount |
| **currency** | Link | Currency |
| **status** | Select | Pending, Invoiced, Paid |
| **sales_invoice** | Link | Sales Invoice (when created) |
| **invoice_date** | Date | Invoice date |
| **notes** | Small Text | Notes |

---

## 5. Special Handling

### 5.1 Project-Level Special Handling

The Special Project can have:
- **Special handling instructions** (Long Text) — overall instructions
- **Products** table — each product can have `special_handling`, `temperature_min/max`, `hazmat_class`

### 5.2 Job-Level Special Handling

Jobs (Transport Job, Warehouse Job, Air Shipment, Sea Shipment) already support or can be extended:
- **Transport Job** — temperature, load type, special instructions
- **Warehouse Job** — storage type, temperature, handling requirements
- **Air Shipment / Sea Shipment** — temperature, handling codes, special cargo

Special Projects should **propagate** special handling from project products to linked jobs when jobs are created or updated.

### 5.3 Special Handling Equipment

- **Equipment Type** — Crane, Forklift, Reefer Unit, Cold Chain, Hazmat Handler
- **Equipment** — in-house asset or outsourced supplier
- **Planned vs actual** usage (start/end dates)

---

## 6. Project Costing

### 6.1 Project-Level Costing

| Component | Source | Description |
|-----------|--------|-------------|
| **Scoping costs** | Special Project Scoping Activity | Ocular inspection, road inspection, technical consultations (*only when charged_to_project = 1, i.e. after project is booked*) |
| **Resource costs** | Special Project Resource | Personnel, equipment, third-party |
| **Equipment costs** | Special Project Equipment | Special handling equipment |
| **Job costs** | Special Project Job → job charges | Sum of charges from linked jobs |
| **Other costs** | Optional: Special Project Cost | Ad-hoc costs (e.g. permits, documentation) |

**Total Project Cost** = sum(scoping costs where charged) + sum(resource costs) + sum(equipment costs) + sum(job costs) + other costs

**Scoping cost behaviour:** During the **Scoping** phase, scoping costs are tracked but *excluded* from project costing. When the project is **Booked**, the action **Charge Scoping Costs** marks completed scoping activities as charged; their costs then flow into project costing.

### 6.2 Individual Job Costing

Each linked job (Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration) has its own charges table. The Special Project Job child table holds:
- **planned_cost** — user-entered
- **actual_cost** — fetched from job charges (sum of cost amounts)
- **planned_revenue** — user-entered
- **actual_revenue** — from Sales Invoice linked to the job

**Job Margin** = actual_revenue - actual_cost

---

## 7. Delivery Reports

### 7.1 Multiple Delivery Milestones

- **Delivery sequence** — 1, 2, 3, …
- **Delivery type** — Full, Partial, Milestone, Proof of Delivery
- **Status** — Pending, Scheduled, Completed, Delayed
- **Attachments** — delivery report, proof of delivery

### 7.2 Integration with POD

- **Transport Job** — can have Proof of Delivery per leg
- **Special Project Delivery** — can link to POD if applicable

---

## 8. Multiple Billings

### 8.1 Billing Milestones

- **Billing sequence** — 1, 2, 3, …
- **Bill type** — Milestone, Interim, Final, Ad-hoc
- **Planned amount** — planned invoice amount
- **Status** — Pending, Invoiced, Paid
- **Sales Invoice** — link when invoice is created

### 8.2 Creation of Sales Invoices

- **Action:** Create Sales Invoice from Special Project Billing
- Filter: only billings with status = Pending
- Can create **one** Sales Invoice per billing row, or **batch** create from multiple rows
- Link to Sales Invoice via `sales_invoice` field
- Update status to Invoiced

### 8.3 Allocation of Charges

- When creating Sales Invoice from project billing, charges can be allocated from:
  - Linked jobs’ charges
  - Or manual entry
- Design choice: **Billing row** can specify which jobs/charges to include (e.g. “Job 1 + Job 2 + 50% of Job 3”) or use a simpler allocation (e.g. equal split, or proportional by job cost).

---

## 9. Monitoring

### 9.1 Project Dashboard

- **Status** — overall project status
- **Progress** — % activities completed, % jobs completed
- **Cost vs budget** — planned vs actual costs
- **Revenue vs planned** — planned vs actual revenue
- **Delivery milestones** — % delivered
- **Billing milestones** — % billed

### 9.2 Alerts

- **Activities overdue** — planned_end < today and status != Completed
- **Deliveries delayed** — delivery status = Delayed
- **Cost overrun** — actual cost > planned cost
- **Resource allocation** — resources assigned but not allocated to activities
- **Unfulfilled requests** — requests with pending or partially fulfilled items

---

## 10. Workflow

### 10.1 Status Flow

```
Draft → Scoping → Booked → Planning → Approved → In Progress → Completed
          ↓          ↓           ↓          ↓
       Cancelled  Cancelled   On Hold    On Hold
                                 ↓          ↓
                              Cancelled  Cancelled
```

**Scoping phase:** Project is in pre-booking assessment. Ocular inspection, road inspection, and technical consultations are performed; costs are recorded but **not charged to the project**.

**Booked:** Project is confirmed. **Charge Scoping Costs** action marks scoping activities as charged; their costs flow into project costing and can be included in billing.

### 10.2 Actions

| Action | Description |
|--------|-------------|
| **Add Scoping Activity** | Add ocular inspection, road inspection, or technical consultation; record cost |
| **Charge Scoping Costs** | When project is booked: mark all completed scoping activities as charged; costs flow into project costing |
| **Create Request** | Create Special Project Request (resources, products, equipment) linked to project |
| **Link Project** | Link existing ERPNext Project to Special Project (fallback when auto-creation is skipped or for migration) |
| **Create Inbound/Release/Transport/Air/Sea Order from Request** | Create logistics order/booking from product requests; sets project on order |
| **Link Existing Order** | Link existing order/booking to request and set project |
| **Create Activity** | Add activity to planning |
| **Create Job from Activity** | Create Transport Job, Warehouse Job, Air Shipment, Sea Shipment, or Declaration from activity and link to project |
| **Link Existing Job** | Link an existing job to the project |
| **Create Delivery Report** | Add delivery milestone |
| **Create Billing Milestone** | Add billing milestone |
| **Create Sales Invoice** | Create Sales Invoice from billing row; sets **project** on Sales Invoice for ERPNext integration |
| **Refresh Costs** | Recalculate actual costs from linked jobs |
| **Refresh Revenue** | Recalculate actual revenue from Sales Invoices |

---

## 11. Integration with Existing Modules

### 11.1 Project Link Scope (Orders, Bookings, Jobs, Sales Invoice)

The **project** (Link to Project) field is used for unified project visibility across logistics and ERPNext. It is **not** limited to orders/bookings; it applies to:

| Document Type | project (Link) | Notes |
|---------------|----------------|-------|
| **Orders & Bookings** | Transport Order, Air Booking, Sea Booking, Inbound Order, Release Order, Transfer Order, VAS Order | Set when creating from Special Project Request |
| **Jobs** | Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration | Set when creating from Special Project Activity or linking |
| **Sales Invoice** | Sales Invoice | Already exists in ERPNext; set when creating from Special Project Billing |

When creating from Special Project, `project` is set from Special Project.project (the linked ERPNext Project).

---

### 11.2 ERPNext Projects Module Integration

**Approach:** When a Special Project is created, an ERPNext **Project** is **automatically created** and linked. Special Project adds logistics-specific features; ERPNext Project provides task management, costing, and billing.

| ERPNext Project | Special Project |
|-----------------|-----------------|
| Task management (Tasks, dependencies) | Scoping activities, logistics activities |
| Timesheets (time tracking) | Resource/equipment allocation |
| % completion (Task Completion, Task Weight, etc.) | Activity progress |
| Costing (Timesheet cost, Purchase Cost, Expense Claim, Consumed Material) | Job costs, scoping costs, resource costs |
| Billing (Sales Order, Sales Invoice) | Multiple delivery reports, multiple billings |
| Customer, Sales Order | Customer, Sales Quote |

**Special Project.project** = Link to ERPNext Project. **Auto-created on insert:** When a Special Project is inserted, the system automatically creates an ERPNext Project and sets `project`. The Project is populated with: project_name (from Special Project.project_name), customer, expected_start_date, expected_end_date, status (mapped from Special Project status).

- All logistics docs (orders, bookings, jobs) set `project` from Special Project.project
- Sales Invoice created from Special Project Billing sets `project` (ERPNext already supports this)
- Project shows: Total Costing, Total Billed, Gross Margin, Tasks, Timesheets

**Implementation:** `on_insert` or `after_insert` hook on Special Project creates Project and updates Special Project.project.

---

### 11.3 Transport Job

- **project** (Link to Project) — set from Special Project when linked
- **Special Project Job** — when job is linked, Transport Job Charges feed into project costing

### 11.4 Warehouse Job

- **project** (Link to Project) — set from Special Project when linked
- **Special Project Job** — Warehouse Job Charges feed into project costing

### 11.5 Air Shipment / Sea Shipment

- **project** (Link to Project) — set from Special Project when linked
- **Special Project Job** — Air/Sea Shipment Charges feed into project costing

### 11.6 Declaration (Customs)

- **project** (Link to Project) — set from Special Project when linked
- **Special Project Job** — Declaration charges feed into project costing

### 11.7 Logistics Orders and Bookings (Product Request Integration)

Product requests integrate with logistics orders/bookings. Each must have **project** (Link to Project) to reference the project:

| Document | project | Use Case |
|----------|---------|----------|
| **Transport Order** | Link | Product request → Create Transport Order from Request |
| **Air Booking** | Link | Product request → Create Air Booking from Request |
| **Sea Booking** | Link | Product request → Create Sea Booking from Request |
| **Inbound Order** | Link | Product request → Create Inbound Order from Request |
| **Release Order** | Link | Product request → Create Release Order from Request |
| **Transfer Order** | Link | Product request → Create Transfer Order from Request |
| **VAS Order** | Link | Product request → Create VAS Order from Request |

When creating an order/booking from a product request, the system sets **project** on the created document (from Special Project.project). **Link Existing Order** sets **project** on an existing document.

### 11.8 Sales Invoice

- **project** (Link to Project) — **already exists in ERPNext; no change required**
- When creating Sales Invoice from Special Project Billing, set `project` from Special Project.project
- Enables project-wise billing report, Total Billed Amount on Project

### 11.10 Sales Quote

- **Special Project** (Link) — optional link from Special Project to Sales Quote
- **Create-from Quote** — optional: create Special Project from Sales Quote (with multi-modal lines)

---

## 12. Data Model Summary

```
Special Project
├── Special Project Scoping Activity (child) — Ocular Inspection, Road Inspection, Technical Consultation
├── Special Project Activity (child)
│   └── depends_on → Special Project Activity
├── Special Project Resource (child)
├── Special Project Product (child)
├── Special Project Equipment (child)
├── Special Project Job (child)

│   ├── job_type: Transport Job | Warehouse Job | Air Shipment | Sea Shipment | Declaration
│   └── job: Dynamic Link
│
├── Special Project Delivery (child)
└── Special Project Billing (child)
    └── sales_invoice → Sales Invoice

Special Project (has project → Project)
    └── project: Link to ERPNext Project (task management, costing, billing)

Special Project Request (standalone; special_project → Special Project)
├── Special Project Resource Request (child)
├── Special Project Product Request (child) — reference_doctype, reference_doc → orders/bookings
└── Special Project Equipment Request (child)

Documents with project (Link to Project):
Orders/Bookings: Transport Order, Air Booking, Sea Booking, Inbound Order, Release Order, Transfer Order, VAS Order
Jobs: Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration
Sales Invoice: (already has project in ERPNext)

Master Doctypes:
- Special Handling Type
- Special Handling Equipment Type
```

---

## 13. Implementation Phases

### Phase 1: Core

- [ ] Special Project (DocType)
- [ ] Special Project Scoping Activity (child) — ocular inspection, road inspection, technical consultations; charge on booking
- [ ] Special Project Request (DocType) — resources, products, equipment
- [ ] Special Project Resource Request, Product Request, Equipment Request (child tables)
- [ ] Add **project** (Link to Project) to Transport Order, Air Booking, Sea Booking, Inbound Order, Release Order, Transfer Order, VAS Order, Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration (Sales Invoice already has project)
- [ ] Create Order from Request actions (Inbound, Release, Transport, Air, Sea, Transfer)
- [ ] Special Project Activity (child)
- [ ] Special Project Resource (child)
- [ ] Special Project Product (child)
- [ ] Special Project Job (child)
- [ ] Special Project Delivery (child)
- [ ] Special Project Billing (child)
- [ ] Special Handling Type (master)
- [ ] Auto-create ERPNext Project on Special Project insert; propagate project when creating orders/jobs/invoices
- [ ] Project costing summary (roll-up from jobs)

### Phase 2: Equipment and Special Handling

- [ ] Special Project Equipment (child)
- [ ] Special Handling Equipment Type (master)
- [ ] Special handling propagation to jobs
- [ ] Equipment in-house vs outsourced tracking

### Phase 3: Planning and Monitoring

- [ ] Activity dependencies
- [ ] Gantt or timeline view (optional)
- [ ] Project dashboard
- [ ] Alerts for overdue activities, cost overrun

### Phase 4: Billing and Delivery

- [ ] Create Sales Invoice from Billing (set project from Special Project.project)
- [ ] Multiple delivery reports
- [ ] Proof of Delivery integration

---

## 14. Reports

| Report | Description |
|--------|-------------|
| **Special Project Status** | List of projects with status, progress, costs |
| **Special Project Cost Summary** | Project-level cost breakdown |
| **Special Project Job Costing** | Per-job cost and revenue for projects |
| **Special Project Delivery Status** | Delivery milestones and status |
| **Special Project Billing Status** | Billing milestones and status |
| **Special Project Request Status** | Requests by project, fulfillment status |

---

## 15. Summary

The Special Projects module provides:

- **Project scoping** — ocular inspection, road inspection, technical consultations; costs tracked during scoping and charged when project is booked
- **Requests** for resources, products, equipment — formal request workflow; product requests integrate with Transport Order, Air Booking, Sea Booking, Inbound Order, Release Order, Transfer Order, VAS Order (each with **project** reference)
- **Project link** — **project** (Link to Project) on orders, bookings, jobs, and Sales Invoice; **ERPNext Projects integration** — Special Project links to ERPNext Project for task management, costing, billing
- **Rigorous planning** via activities, milestones, dependencies, and resources
- **Resource and equipment management** (in-house and outsourced)
- **Orchestration** of jobs across Transport, Warehousing, Air Freight, Sea Freight, Customs
- **Special handling** for temperature, hazmat, oversized, fragile, etc.
- **Equipment** for special handling (cranes, forklifts, reefer units)
- **Project costing** and **individual job costing**
- **Multiple delivery reports** and milestones
- **Multiple billings** with Sales Invoice creation
- **Monitoring** via dashboard and alerts

The design aligns with existing logistics app patterns (child tables, Link to jobs, charges tables) and integrates with Transport Job, Warehouse Job, Air Shipment, Sea Shipment, and Declaration.
