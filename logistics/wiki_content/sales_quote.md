# Sales Quote

**Sales Quote** is a multi-product pricing document that can include Sea Freight, Air Freight, Transport, Warehousing, and Customs services. It serves as the commercial offer to the customer and can flow into Bookings, Orders, and Jobs.

A Sales Quote records pricing for one or more services per leg, with weight breaks, quantity breaks, routing, and charges. It supports three **Quotation Types**: **Regular** (reusable across multiple jobs/orders), **One-off** (single-use only), and **Project** (project-scoped with resources and products). It integrates with ERPNext Sales Order and can create Air Booking, Sea Booking, Transport Order, Declaration Order, Inbound Order, or Release Order.

To access Sales Quote, go to:

**Home > Pricing Center > Sales Quote**

## 1. Prerequisites

Before creating a Sales Quote, it is advised to set up the following:

- Customer (from ERPNext)
- Port/Airport masters (for freight)
- [Transport Settings](welcome/transport-settings) and [Transport Template](welcome/transport-template) (for transport)
- Warehouse (for warehousing)

## 2. How to Create a Sales Quote

1. Go to the Sales Quote list, click **New**.
2. Enter **Quote Date** and select **Customer**.
3. Add **Routing Legs** (Sea, Air, Transport, Customs, Warehouse) as needed.
4. Add **Weight Breaks** for freight pricing.
5. Add **Charges** per service.
6. **Save** the document.

### 2.1 Quotation Type

- **Regular** – Reusable across multiple jobs, orders, and bookings. Child tables hold full charge parameters.
- **One-off** – Single-use only; once converted, cannot be linked to another order. Header-level default parameters; child params disabled.
- **Project** – Project-scoped; links to Special Project. Supports Projects Tab with resources and products.

### 2.2 Statuses

- **Draft** – Quote is being prepared
- **Submitted** – Quote is sent to customer
- **Lost** – Quote was not accepted
- **Ordered** – Quote was converted to order (Regular)
- **Converted** – One-off quote has been converted (One-off only)

## 3. Features

### 3.1 Creating Documents from Sales Quote

From a submitted Sales Quote, you can create:
- Air Booking, Sea Booking
- Transport Order
- Declaration Order
- Inbound Order, Release Order

### 3.2 Change Request

For additional charges on existing jobs (Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration), use **Create Change Request** from the job form. The Change Request captures new charge lines; when approved, charges are applied to the job. You can also create a Sales Quote from a Change Request for billing.

### 3.3 Integration with ERPNext

Sales Quote can be linked to ERPNext Sales Order. When the order is confirmed, you can create the corresponding logistics documents.

## 4. Calculation Methods

Each charge line (Air Freight, Sea Freight, Transport) uses a **Calculation Method** to compute revenue and cost. Revenue uses **Calculation Method**; cost uses **Cost Calculation Method**, with the same options and formulas. The same unified calculation engine is used across Air Booking, Sea Booking, Transport Order, Transport Job, Air Shipment, Sea Shipment, Declaration, and Declaration Order charges. On Bookings and Orders, charges store **Estimated Revenue** and **Estimated Cost**; on Shipments and Jobs, **Actual Revenue** and **Actual Cost** are also calculated and used for invoicing when present (see [Job Management Module](welcome/job-management-module)).

### 4.1 Formula Summary

| Method | Formula |
|--------|---------|
| Per Unit | `unit_rate × quantity` (with min/max) |
| Fixed Amount | `unit_rate` |
| Flat Rate | `unit_rate` |
| Base Plus Additional | `base_amount + (unit_rate × max(0, quantity - base_qty))` |
| First Plus Additional | `minimum_unit_rate × qty` if qty ≤ min; else `(minimum_unit_rate × min_qty) + (unit_rate × (qty - min_qty))` |
| Percentage | `(unit_rate / 100) × base_amount` |
| Weight Break | `weight × unit_rate` (tier from weight break table) |
| Qty Break | `quantity × unit_rate` (tier from qty break table) |
| Location-based | Same as Per Unit |

### 4.2 Unit Types

**Unit Type** defines what “quantity” means: Weight, Volume, Distance, Package, Piece, Job, Trip, TEU, or Operation Time.

For full details, required fields, and examples, see [Sales Quote – Calculation Method Guide](welcome/sales-quote-calculation-method).

## 5. Related Topics

- [Sales Quote – Calculation Method Guide](welcome/sales-quote-calculation-method) – full formulas, required fields, and examples
- [Sea Booking](welcome/sea-booking)
- [Air Booking](welcome/air-booking)
- [Transport Order](welcome/transport-order)
