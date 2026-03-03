# Quotation Type Integration Design

This document describes the design for integrating **Sales Quote** and **One-Off Quote** under a unified quotation model with a **Quotation Type** selector. The selector controls reuse behavior, parameter placement (header vs. child), and project-specific capabilities.

---

## 1. Overview

| Quotation Type | Reuse | Parameter Placement | Special Features |
|----------------|-------|---------------------|------------------|
| **Regular** | Reusable across multiple jobs/orders/bookings | Child tables hold full parameters | Contract-style; standard multimodal routing |
| **One-off** | Single-use only; cannot be linked to other orders | Header defaults; child params disabled | Simplified flow; one conversion per quote |
| **Project** | Project-scoped; links to Special Project | Header + Projects Tab; resources quotable | Multimodal; Projects Tab; resources + products |

---

## 2. Quotation Type Definitions

### 2.1 Regular

- **Purpose:** Contract-style quotation that can be reused across multiple jobs, orders, and bookings.
- **Behavior:**
  - Same as current **Sales Quote** behavior.
  - Can be linked from: Transport Order, Warehouse Contract, Air Booking, Sea Booking, Declaration Order.
  - Each child table row (Sea Freight, Air Freight, Transport, Customs, Warehousing) holds **full charge parameters** (load type, direction, ports, shipping line, etc.).
  - Supports **multimodal** routing with `is_multimodal`, `routing_legs`, `billing_mode`.
- **Validation:** No restriction on number of linked orders/bookings.

### 2.2 One-off

- **Purpose:** Single-transaction quotation; one-time use only.
- **Behavior:**
  - **Single-use:** Once converted to an order/booking, the quote cannot be linked to any other order or booking.
  - **Header-level default parameters:** Charge parameters (load type, direction, weight, volume, origin, destination, etc.) are defined in the **header** per product (Sea, Air, Transport).
  - **Child tables:** Charge parameters in child tables are **disabled** (read-only or hidden). Child rows only hold: item code, revenue/cost calculation fields (calculation method, quantity, unit rate, etc.). Parameters are inherited from the header.
  - **Conversion tracking:** `status` (Draft / Converted), `converted_to_doc` (reference to the created order/booking).
- **Validation:**
  - On linking from an order/booking: if quote is already converted, block the link.
  - Only one order/booking can reference a One-off quote.

### 2.3 Project

- **Purpose:** Quotation for project-based work; supports resources, multimodal services, and project linkage.
- **Behavior:**
  - **Multimodal:** Always allows multimodal quotation (Sea + Air + Transport + Customs + Warehousing).
  - **Projects Tab:** Dedicated tab for project-related content:
    - Link to **Special Project** (optional).
    - **Resources** table: quote resources (personnel, equipment, third party) with quantity, UOM, planned hours, cost per unit.
    - **Products** table: other products/services to include in the quotation (beyond standard logistics products).
  - **Routing:** Same routing model as Regular (routing legs, billing mode).
  - **Reuse:** Tied to the linked Special Project; can be used for jobs created under that project.
- **Validation:** When linked to a Special Project, jobs created from the quote should be associated with that project.

---

## 3. Data Model

### 3.1 Unified Quote Doctype (Sales Quote)

**Option A: Single DocType with Quotation Type**

Extend **Sales Quote** to support all three types. One-Off Quote is merged into Sales Quote as a type.

| Field | Type | Description |
|-------|------|-------------|
| `quotation_type` | Select | `Regular`, `One-off`, `Project` |
| `status` | Select | `Draft`, `Submitted`, `Converted` (for One-off) |
| `converted_to_doc` | Data | Reference to created order/booking (One-off only) |
| `special_project` | Link | Special Project (Project type only) |

**Option B: Keep Separate DocTypes**

Retain **Sales Quote** and **One-Off Quote** as separate doctypes, but add `quotation_type` to both. Sales Quote supports Regular and Project; One-Off Quote supports One-off only. A shared base or mixin can be used for common logic.

**Recommendation:** Option A (unified Sales Quote) simplifies maintenance and user experience. One-Off Quote becomes a "mode" of Sales Quote rather than a separate doctype.

### 3.2 Header-Level Default Parameters (One-off)

When `quotation_type = "One-off"`, the following sections appear in the header (per product tab):

**Sea:**
- `sea_load_type`, `sea_direction`, `sea_transport_mode`, `shipping_line`, `freight_agent_sea`, `sea_house_type`
- `sea_weight`, `sea_volume`, `sea_chargeable`, `sea_weight_uom`, `sea_volume_uom`, `sea_chargeable_uom`
- `origin_port_sea`, `destination_port_sea`

**Air:**
- `air_load_type`, `air_direction`, `airline`, `freight_agent`, `air_house_type`
- `origin_port`, `destination_port`
- Weight/volume/chargeable if applicable

**Transport:**
- `transport_template`, `load_type`, `vehicle_type`, `container_type`
- `location_type`, `location_from`, `location_to`
- `pick_mode`, `drop_mode`

These fields are **hidden or disabled** when `quotation_type = "Regular"` or `"Project"`.

### 3.3 Child Table Parameter Visibility

| Child Table | Regular | One-off | Project |
|-------------|---------|---------|---------|
| Sales Quote Sea Freight | Full parameters (load type, direction, ports, etc.) | **Disabled** (inherit from header) | Full parameters |
| Sales Quote Air Freight | Full parameters | **Disabled** | Full parameters |
| Sales Quote Transport | Full parameters | **Disabled** | Full parameters |
| Sales Quote Customs | Full parameters | Full (or header defaults if added) | Full parameters |
| Sales Quote Warehouse | Full parameters | Full (or header defaults if added) | Full parameters |

Child tables always retain: `item_code`, `item_name`, revenue/cost fields (calculation method, quantity, unit rate, tariff, etc.).

### 3.4 Projects Tab (Project Type Only)

When `quotation_type = "Project"`:

| Field | Type | Description |
|-------|------|-------------|
| `special_project` | Link | Special Project |
| `project_resources` | Table | Quote resources (resource type, role, quantity, UOM, planned hours, cost per unit) |
| `project_products` | Table | Other products to include (item, description, quantity, rate) |

`project_resources` and `project_products` can be new child doctypes or reuse structures from Special Project (e.g. Special Project Resource, Special Project Product).

---

## 4. UI / Form Behavior

### 4.1 Quotation Type Selector

- Placed near the top of the form (e.g. after `naming_series`, before `customer`).
- On change:
  - **Regular:** Show standard layout; hide header default params; enable child params.
  - **One-off:** Show header default params per product; disable child params; show `status`, `converted_to_doc`.
  - **Project:** Show Projects Tab; enable `is_multimodal`; show `special_project`, `project_resources`, `project_products`.

### 4.2 Depends On / Read Only

- Header default params: `depends_on: eval:doc.quotation_type == "One-off"`.
- Child table parameter fields: `read_only_depends_on: eval:doc.quotation_type == "One-off"` (or `depends_on` to hide).
- Projects Tab: `depends_on: eval:doc.quotation_type == "Project"`.

### 4.3 Naming Series

- Regular: `SQU.#########`
- One-off: `OOQ-.#####` (or unified series with type in name)
- Project: `PQ-.#####` or same as Regular with type indicator

---

## 5. Validation & Business Logic

### 5.1 One-off Single-Use

- On **submit** of order/booking that references a One-off quote: set quote `status = "Converted"`, `converted_to_doc = <order/booking name>`.
- When user tries to link a **second** order/booking to the same One-off quote:
  - Validate: if `status == "Converted"`, throw: *"One-off Quote {name} has already been converted and cannot be used with another order/booking."*
- Optional: `reopen_one_off_quote` to reset status when the linked order is cancelled.

### 5.2 Project Quote and Special Project

- When `quotation_type == "Project"` and `special_project` is set:
  - Jobs created from the quote (e.g. via routing legs) can be linked to the Special Project.
  - Resources and products from the Projects Tab can flow into the project when it is created/updated.

### 5.3 Conversion Flows

| Quotation Type | Converts To |
|----------------|-------------|
| Regular | Transport Order, Warehouse Contract, Air Booking, Sea Booking, Declaration Order (multiple allowed) |
| One-off | Single Transport Order, Warehouse Contract, Air Booking, Sea Booking, or Declaration Order |
| Project | Special Project + associated jobs; or individual bookings linked to the project |

---

## 6. Migration Considerations

### 6.1 Existing Sales Quote

- Set `quotation_type = "Regular"` for all existing Sales Quotes.
- No structural change to child tables.

### 6.2 Existing One-Off Quote

- **If Option A (unified):** Migrate One-Off Quote records into Sales Quote with `quotation_type = "One-off"`. Map header params and child tables. Preserve `converted_to_doc` and `status`.
- **If Option B (separate):** Add `quotation_type = "One-off"` to One-Off Quote; no migration of records.

### 6.3 References

- Orders/bookings that reference `sales_quote` or `one_off_quote` (via `quote_type` + `quote`) must be updated if One-Off Quote is merged into Sales Quote. Ensure `quote_type` and `quote` point to the unified Sales Quote.

---

## 7. Summary

| Aspect | Regular | One-off | Project |
|--------|---------|---------|---------|
| **Reuse** | Multiple jobs/orders | Single use only | Project-scoped |
| **Header params** | Hidden | Default parameters | Hidden |
| **Child params** | Enabled | Disabled (inherit) | Enabled |
| **Multimodal** | Supported | Supported | Always supported |
| **Projects Tab** | Hidden | Hidden | Shown (resources, products) |
| **Special Project link** | No | No | Yes |

---

## 8. Implementation Phases

1. **Phase 1:** Add `quotation_type` to Sales Quote; implement Regular (default) and One-off behaviors (header params, child read-only). ✅ Implemented
2. **Phase 2:** Migrate One-Off Quote data into Sales Quote (if Option A); update order/booking references.
3. **Phase 3:** Add Project type; Projects Tab, resources, products, Special Project link. ✅ Implemented
4. **Phase 4:** Deprecate One-Off Quote doctype (if Option A) and update all references.

---

## 9. Implementation Summary (Unified DocType)

### Completed

- **Sales Quote** extended with:
  - `quotation_type` (Regular, One-off, Project)
  - `status`, `converted_to_doc` for One-off
  - One-off header default parameters (Sea, Air, Transport tabs)
  - Projects Tab with `special_project`, `project_resources`, `project_products`
  - Naming series: SQU, OOQ, PQ
- **Sales Quote Resource** and **Sales Quote Product** child doctypes for Project type
- **One-off validation**: Block second conversion; set status/converted_to_doc on create
- **reopen_sales_quote_one_off**: Reset status when quote cleared in order/booking
- **Migration patch**: Set `quotation_type = "Regular"` for existing Sales Quotes
- **Form script**: `quotation_type` change handler; `one_off` replaced with `quotation_type === "One-off"`

### One-Off Quote Doctype

- Retained for backward compatibility. New One-off quotes use Sales Quote with `quotation_type = "One-off"`.
