# Special Projects — Setup and Workspace Summary

## 1. Module and Workspace

| Item | Detail |
|------|--------|
| **Module** | Special Projects (`logistics.special_projects`) |
| **Workspace** | Special Projects |
| **Workspace title** | Special Projects |
| **Icon** | `grid` (workspace), `forklift` (sidebar) |
| **Sidebar** | Standard sidebar **Special Projects** → links to workspace **Special Projects** (Home) |
| **Desktop icon** | **Special Projects** (Link to Workspace Sidebar), blue, visible by default |

---

## 2. Workspace Content

The Special Projects workspace provides:

- **Overview** — Number cards:
  - **Active Projects** — count of Special Projects with status In Progress, Planning, Approved, Booked, or Scoping
  - **Total Projects** — count of all Special Projects
  - **Open Requests** — count of Special Project Requests not Fulfilled or Cancelled
- **Projects by Status** — Dashboard chart (Donut) showing Special Project count by status
- **Quick Access** — Shortcuts to **Special Project** list and **Special Project Request** list
- **Operational Reports** — Shortcuts to Special Project Status, Special Project Delivery Status, Special Project Billing Status, Special Project Request Status (reports must be created to use these)
- **Cost Analysis** — Shortcuts to Special Project Cost Summary, Special Project Job Costing
- **Insights** — Shortcut to Special Project Status (overview report)

Number cards and the dashboard chart are provided by the app. Report shortcuts link to report DocTypes; create the reports as per `SPECIAL_PROJECTS_REPORTS.md` for the links to work.

---

## 3. Setup and Master Data

There is **no dedicated “Special Projects Settings”** DocType. Configuration and setup rely on:

### 3.1 Master Data (setup before use)

| DocType | Purpose | Key fields |
|---------|---------|------------|
| **Special Handling Type** | Types of special handling (temperature, hazmat, oversized, fragile, etc.) | `handling_type`, `description`, `requires_equipment`, `requires_certification`, `default_instructions` |
| **Special Handling Equipment Type** | Types of equipment (crane, forklift, reefer, etc.) | `equipment_type`, `description`, `in_house_available` |

**Setup steps:**

1. **Special Handling Type** — Create at least the types you need (e.g. Temperature Controlled, Hazardous, Oversized, Fragile, High Value). Used on Special Project **Products** and for special handling instructions.
2. **Special Handling Equipment Type** — Create equipment types used in **Special Project Equipment** and **Special Project Equipment Request** (e.g. Crane, Forklift, Reefer Unit, Cold Chain Container, Hazmat Handler).

### 3.2 ERPNext / System Dependencies

- **Project** (ERPNext) — Created automatically when a **Special Project** is inserted; no manual setup. Optional: ensure **Project Type** “External” exists if you use it.
- **Company** — Default company is used when auto-creating the ERPNext Project.
- **Customer** — Required when creating orders from **Special Project Request**; set on the Special Project.

---

## 4. Integration (project field)

The **project** (Link to Project) field is added by **patches** to these DocTypes (no form customisation needed):

- **Orders / Bookings:** Transport Order, Air Booking, Sea Booking, Inbound Order, Release Order, Transfer Order, VAS Order  
- **Jobs:** Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration  

**Sales Invoice** already has **project** in ERPNext. When creating Sales Invoices from Special Project Billing (when implemented), set `project` from **Special Project.project**.

Run **bench migrate** so these patches are applied.

---

## 5. Roles and Permissions

| DocType | Roles with full access |
|---------|-------------------------|
| Special Project | System Manager, Projects Manager |
| Special Project Request | System Manager, Projects Manager |
| Special Handling Type | System Manager |
| Special Handling Equipment Type | System Manager |

Assign **Projects Manager** to users who should manage Special Projects and Requests.

---

## 6. Quick Reference — Where to Go

| Task | Where |
|------|--------|
| Open Special Projects | Sidebar → **Special Projects** (or desktop icon **Special Projects**) |
| List projects | Workspace → **Project** shortcut, or **Special Project** list |
| List requests | Workspace → **Request** shortcut, or **Special Project Request** list |
| Define handling types | **Special Handling Type** (search or add to workspace if desired) |
| Define equipment types | **Special Handling Equipment Type** (search or add to workspace if desired) |

---

## 7. Optional Workspace Customisation

To add master data or other links to the workspace:

1. Go to **Workspace** list, open **Special Projects**.
2. Edit the workspace: add shortcuts (e.g. **Special Handling Type**, **Special Handling Equipment Type**) or links under new sections.
3. Save and reload.

No app code change is required for adding shortcuts or links.
