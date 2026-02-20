# One-Off Quote vs Contract Quote (Sales Quote) – Design

## 1. Overview and Goals

**Objective:** Separate **one-off quotes** from **contract quotes** so that:

1. **One-Off Quote** is a distinct document, structurally similar to an order/booking, and can be **converted** into the corresponding order (Transport Order, Air Booking, Sea Booking). One quote → one order/booking.
2. **Sales Quote (Contract Quote)** remains the existing contract/pricing document used for recurring business. It does **not** implement one-off behavior; all one-off logic is removed from it.
3. **Orders, bookings, and jobs** can reference **either** a One-Off Quote **or** a Sales Quote via a **dynamic link**, so that quote references are unambiguous and reportable.

## 2. Current State (Summary)

| Aspect | Current Behavior |
|--------|------------------|
| **Sales Quote** | Has a **One-Off** checkbox. When checked, the quote can create Transport Order, Air Booking, or Sea Booking via actions/dialogs. When unchecked, it is used as a contract quote (e.g. Transport Order link filters exclude `one_off = 1`). |
| **Transport Order** | Has **Sales Quote** (Link). Link filters: `is_transport = 1` and **one_off != 1** (contract only). One-off flow: create order from Sales Quote via "Create Transport Order from Sales Quote" with `one_off = 1` filter. |
| **Air Booking / Sea Booking** | Have **Sales Quote** (Link). Can be created from a one-off Sales Quote via dialogs; also support "Fetch quotations" from Sales Quote. |
| **Air Shipment / Sea Shipment** | Have **Sales Quote** (Link). |
| **Declaration / Declaration Order** | Have **Sales Quote** (Link). |
| **Warehouse Contract** | Has **Sales Quote** (Link). |
| **Transport Job** | No direct quote field; when creating Sales Invoice, code uses `job.sales_quote` (likely intended to come from parent Transport Order). |
| **Charge child tables** | Transport Job Charges, Air Shipment Charges, Sea Freight Charges, Warehouse Job Charges use **sales_quote_link** (Link to Sales Quote) to trace charge source. |
| **Create-from flows** | `create_from_sales_quote.js` and Sales Quote server methods: `create_transport_order_from_sales_quote`, `create_air_booking_from_sales_quote`, `create_sea_booking_from_sales_quote` (all require `one_off = 1`). |

## 3. Target State

### 3.1 Document Roles

| Document | Role |
|----------|------|
| **One-Off Quote** | Single-transaction quote. Structure mirrors the target order/booking (transport, air, sea). One document can be converted into **one** Transport Order, **one** Air Booking, or **one** Sea Booking. No contract/pricing-tariff semantics. |
| **Sales Quote** | Contract quote / tariff quote. Used for recurring pricing, warehouse contracts, and as the source of **contract**-based orders (e.g. Transport Order linked to Sales Quote for charge pull). **No** one-off checkbox and **no** "create order from this quote" one-off flows. |

### 3.2 Quote Reference on Orders/Bookings/Jobs

Orders, bookings, and jobs that today have a single **Sales Quote** link will support a **dynamic quote reference** so they can point to either:

- **One-Off Quote**, or  
- **Sales Quote** (contract quote).

This is implemented with Frappe’s **Dynamic Link** pattern:

- **quote_type** (Select): `"One-Off Quote"` \| `"Sales Quote"`.
- **quote** (Dynamic Link, `options = quote_type`): the document name.

So a row/record has either `(quote_type = "One-Off Quote", quote = "OOQ-00001")` or `(quote_type = "Sales Quote", quote = "SQU-00001")`. List views and reports show "Quote" as the resolved dynamic link (doctype + name).

## 4. One-Off Quote – New DocType

### 4.1 Purpose

- Represent a **single** ad-hoc quote that will become **one** order or booking.
- Structure is **similar to** the target document (order/booking), not to the multi-modal Sales Quote.
- Actions: **Convert to Transport Order**, **Convert to Air Booking**, **Convert to Sea Booking** (one conversion per quote, as appropriate).

### 4.2 Suggested Structure (High Level)

- **Naming:** e.g. `One-Off Quote` (DocType), naming series `OOQ-.#####` (example).
- **Core fields:** Customer, Date, Valid Until, Shipper, Consignee, Incoterm, Service Level, etc. (subset of what orders/bookings need).
- **Mode:** One quote is for **one** mode: Transport **or** Air **or** Sea (not all three). So:
  - **Quote type / Mode:** Select: `Transport` \| `Air` \| `Sea`.
  - **Transport:** If Transport – location type, location from/to, load type, vehicle type, container type, weight/volume/chargeable, packages, **charges** (child table). No Sales Quote Transport child; structure similar to Transport Order (e.g. charges table).
  - **Air:** If Air – direction, airline, ports, dates, weight/volume/chargeable, packages, routing, house details, **charges**. Structure similar to Air Booking.
  - **Sea:** If Sea – direction, weight/volume/chargeable, packages, **charges**. Structure similar to Sea Booking.

- **Conversion:**  
  - **Convert to Transport Order** (only if mode = Transport): create one Transport Order from this One-Off Quote and set the order’s dynamic quote reference to this One-Off Quote.  
  - **Convert to Air Booking** (only if mode = Air): create one Air Booking, set booking’s quote reference to this One-Off Quote.  
  - **Convert to Sea Booking** (only if mode = Sea): create one Sea Booking, set booking’s quote reference to this One-Off Quote.

- **State:** Optional status such as Draft, Submitted, Converted (and optionally link to the created order/booking for traceability).

### 4.3 What Not to Duplicate

- One-Off Quote does **not** need the full Sales Quote contract/tariff model (e.g. Sales Quote Transport, Sales Quote Air Freight, Sales Quote Sea Freight as separate child DocTypes used for tariff lookup). It holds the data needed to create **one** order/booking and its charges.

## 5. Sales Quote (Contract Quote) – Cleanup

### 5.1 Removals

- Remove **One-Off** checkbox and all logic that depends on it.
- Remove **create_transport_order_from_sales_quote**, **create_air_booking_from_sales_quote**, **create_sea_booking_from_sales_quote** (and any similar one-off creation methods) from Sales Quote.
- Remove one-off-only filters from:
  - Transport Order: currently link_filters exclude `one_off = 1`; after cleanup, link_filters should only restrict to contract-relevant filters (e.g. `is_transport = 1`), with **no** reference to one_off.
- Update **create_from_sales_quote.js** (and any menu/actions that open "Create … from Sales Quote" for one-off): point to **One-Off Quote** and the new conversion APIs (create from One-Off Quote), not from Sales Quote.

### 5.2 What Stays

- Sales Quote remains the **contract quote**: multi-modal (sea, air, transport, customs, warehousing), tariff/pricing structure, validity, and link to Warehouse Contract, etc.
- Orders that are created **under a contract** still reference **Sales Quote** via the new **dynamic quote** reference (quote_type = "Sales Quote", quote = &lt;name&gt;).
- Additional-charge and Change Request flows that use Sales Quote (with job reference) remain; they refer to **Sales Quote** only (contract/additional charge quote).

## 6. Dynamic Quote Reference on Orders, Bookings, Jobs

### 6.1 Replacing Single `sales_quote` Link

For every doctype that currently has:

- **sales_quote** (Link, Options = "Sales Quote")

replace with (or add and then deprecate the old field):

- **quote_type** (Select): Options = `"One-Off Quote", "Sales Quote"` (or "Contract Quote" if you rename in UI).
- **quote** (Dynamic Link, Options = **quote_type**): the document name.

**Validation:** Exactly one of the two quote types must be selected when the other is used; `quote` is required when `quote_type` is set. Optional: allow both null for orders/bookings not created from any quote.

### 6.2 Affected DocTypes (Quote Reference)

| DocType | Current Field | Change |
|---------|----------------|--------|
| Transport Order | sales_quote | Replace with quote_type + quote (dynamic link). |
| Air Booking | sales_quote | Replace with quote_type + quote. |
| Sea Booking | sales_quote | Replace with quote_type + quote. |
| Air Shipment | sales_quote | Replace with quote_type + quote. |
| Sea Shipment | sales_quote | Replace with quote_type + quote. |
| Declaration | sales_quote | Replace with quote_type + quote. |
| Declaration Order | sales_quote | Replace with quote_type + quote. |
| Warehouse Contract | sales_quote | Replace with quote_type + quote. |
| Change Request | sales_quote | Replace with quote_type + quote (if it should support both; else keep Link to Sales Quote). |

For **Transport Job** (and any other job that derives quote from parent order): either add **quote_type** + **quote** and set them from the parent order when the job is created, or resolve quote from the parent order when needed (e.g. for Sales Invoice `quotation_no`). Design choice: prefer adding quote_type + quote on the job and syncing from order for consistent reporting and SI.

### 6.3 Display and List Views

- **Quote** column in list views: show the dynamic link (e.g. "One-Off Quote | OOQ-00001" or "Sales Quote | SQU-00002"). This can be a computed/display field or a formatter that uses `quote_type` + `quote`.
- Form: section "Quote" with quote_type and quote; optional read-only "Quote" display that shows a single hyperlink to the referenced document.

### 6.4 Downstream Use (e.g. Sales Invoice)

- Where code today sets `quotation_no` from `sales_quote` (e.g. Transport Job → Sales Invoice), it should set:
  - Either a single **quotation_no** (if Frappe’s Sales Invoice expects one Link): then set it only when `quote_type` is "Sales Quote" (same doctype as current), and for "One-Off Quote" either leave blank or add a custom field for one-off quote reference.
  - Or extend Sales Invoice (or logistics custom) with **quote_type** + **quote** (dynamic) so both quote types can be stored and displayed.

Recommendation: add **quote_type** + **quote** (dynamic) on Sales Invoice (or in custom) so both One-Off Quote and Sales Quote are traceable; keep standard **quotation_no** for Sales Quote when applicable for compatibility.

## 7. Charge Child Tables (Sales Quote Link → Dynamic Quote Link)

Charge tables that currently have **sales_quote_link** (Link to Sales Quote) should support **both** quote types so that charge lineage is clear:

- **quote_type** (Select): `"One-Off Quote"` \| `"Sales Quote"`.
- **quote** (Dynamic Link, Options = quote_type): replace or complement **sales_quote_link**.

Affected child tables (conceptually):

- Transport Job Charges (sales_quote_link)
- Air Shipment Charges (sales_quote_link)
- Sea Freight Charges (sales_quote_link)
- Warehouse Job Charges (sales_quote_link)

Logic that populates "Sales Quote Link" from the parent order/booking should be updated to set quote_type and quote from the parent’s dynamic quote reference (and from One-Off Quote when the order was created from one).

## 8. Sales Quote: Charge Parameters in Child Doctypes Only

Sales Quote (contract quote) must support **multiple charge rows per mode**, each with its **own** set of parameters (e.g. different vehicle types, lane from/to, pick/drop mode for Transport; different origin/destination, carrier, freight agent for Air). All such **charge-parameter** fields must live in the **child** doctypes only; the **header** must not hold mode-specific parameters that belong to individual charge lines.

### 8.1 Principle

- **Header (Sales Quote):** Only common fields (customer, date, valid_until, shipper, consignee, incoterm, service level, **is_sea / is_air / is_transport / is_customs / is_warehousing**), optional high-level dimensions (weight, volume, chargeable at quote level if needed for display), and accounts (company, branch, cost center, profit center). No mode-specific routing, location, vehicle, carrier, or agent fields.
- **Child tables:** Each row defines the **parameters that apply to that charge** (vehicle type, location from/to, pick/drop, origin/destination, carrier, freight agent, etc.). Pricing/rate logic and charge applicability use these child-row parameters, not header fields.

### 8.2 Transport: Header → Sales Quote Transport (child)

**Remove from Sales Quote header** (move or duplicate only in child):

| Field | Move to child |
|-------|----------------|
| transport_template | **Sales Quote Transport** (optional per row) |
| load_type | **Sales Quote Transport** (per row) |
| vehicle_type | **Sales Quote Transport** (already present; ensure no header dependency) |
| container_type | **Sales Quote Transport** (per row) |
| location_type | **Sales Quote Transport** (per row) |
| location_from | **Sales Quote Transport** (Dynamic Link, options = location_type) |
| location_to | **Sales Quote Transport** (Dynamic Link, options = location_type) |
| pick_mode | **Sales Quote Transport** (per row) |
| drop_mode | **Sales Quote Transport** (per row) |

Header may retain only the **transport** checkbox (or **is_transport**) and the **transport** table (Sales Quote Transport). Optional: keep a single **transport_weight**, **transport_volume**, **transport_chargeable** (and UOMs) on header as quote-level defaults for display only; charge applicability and pricing are driven by child rows.

### 8.3 Air Freight: Header → Sales Quote Air Freight (child)

**Remove from Sales Quote header** (move to child):

| Field | Move to child |
|-------|----------------|
| air_load_type | **Sales Quote Air Freight** (per row) |
| air_direction | **Sales Quote Air Freight** (per row) |
| airline | **Sales Quote Air Freight** (carrier; per row) |
| freight_agent | **Sales Quote Air Freight** (per row) |
| air_house_type | **Sales Quote Air Freight** (per row) |
| air_release_type | **Sales Quote Air Freight** (per row) |
| air_entry_type | **Sales Quote Air Freight** (per row) |
| origin_port | **Sales Quote Air Freight** (per row) |
| destination_port | **Sales Quote Air Freight** (per row) |
| air_etd / air_eta | **Sales Quote Air Freight** (optional; per row if needed for charge context) |
| air_house_bl, air_packs, air_inner, air_gooda_value, air_insurance | **Sales Quote Air Freight** (optional; per row if needed) |
| air_description, air_marks_and_nos | **Sales Quote Air Freight** (optional; per row if needed) |

Header may retain only **is_air** and the **air_freight** table (Sales Quote Air Freight). Optional: keep **air_weight**, **air_volume**, **air_chargeable** (and UOMs) on header as quote-level defaults for display; charge parameters (origin, destination, carrier, freight agent, etc.) are only in the child.

### 8.4 Sea Freight: Header → Sales Quote Sea Freight (child)

**Remove from Sales Quote header** (move to child):

| Field | Move to child |
|-------|----------------|
| sea_load_type | **Sales Quote Sea Freight** (per row) |
| Any sea-specific routing or service parameters | **Sales Quote Sea Freight** (per row, as needed) |

Header may retain only **is_sea** and the **sea_freight** table. Optional: keep **sea_weight**, **sea_volume**, **sea_chargeable** (and UOMs) on header as quote-level defaults; charge applicability parameters only in child.

### 8.5 Warehousing: Header → Sales Quote Warehouse (child)

**Remove from Sales Quote header** (move to child):

| Field | Move to child |
|-------|----------------|
| site | **Sales Quote Warehouse** (per row, if used for charge applicability) |
| warehouse_weight, warehouse_volume, warehouse_chargeable (and UOMs) | Optional: keep on header as defaults, or move to **Sales Quote Warehouse** per row for charge-scope (e.g. per handling unit type / storage type). |

**Sales Quote Warehouse** already has **handling_unit_type**, **storage_type**, and charge fields per row; ensure any other charge-scoping parameters (e.g. site, warehouse) are in the child, not the header.

### 8.6 Customs

If Sales Quote has a customs section with header-level parameters that define which charges apply (e.g. declaration type, route), move those parameters into the relevant **customs** child table (or create one) so that each charge row carries its own parameters.

### 8.7 Implementation impact

- **Pricing / rate engines** that today read location, vehicle_type, origin_port, destination_port, airline, freight_agent, etc. from the **parent** Sales Quote must be changed to read from the **child row** (Sales Quote Transport, Sales Quote Air Freight, etc.) for the row being priced.
- **Order/booking “fetch from Sales Quote”** logic that maps header fields (e.g. location_from, location_to, vehicle_type) to Transport Order or Air Booking must be updated to either: (a) use a single “default” child row when pulling to order, or (b) let the user choose which child row(s) apply, or (c) aggregate/merge parameters from multiple rows as per business rules.
- **Validation:** When **is_transport** / **is_air** / **is_sea** / **is_warehousing** is set, the corresponding child table must have at least one row; charge-parameter fields on the child are required as per existing (or updated) rules.

## 9. Implementation Notes

### 8.1 Migration

- **Data migration:** Existing records have `sales_quote` set (Link to Sales Quote). Migrate to `quote_type = "Sales Quote"` and `quote = <existing sales_quote value>`. Then drop or hide the old `sales_quote` field.
- **One-Off Quote:** No migration from existing "one-off" Sales Quotes is strictly required; new one-off flow uses the new One-Off Quote doctype. Optionally: a one-time script to create One-Off Quote documents from existing one-off Sales Quotes and update any orders that pointed to them to use quote_type + quote (One-Off Quote).

### 9.2 Backward Compatibility

- Reports and APIs that filter or join on `sales_quote` must be updated to use `quote_type` and `quote` (e.g. `WHERE quote_type = 'Sales Quote' AND quote = %s`).
- Permissions and "link" configuration in DocType JSON (link_doctype / link_fieldname) that point to `sales_quote` should be updated to the new dynamic quote (or to both doctypes as needed).

### 9.3 Determinism of "Quote" on Orders/Bookings/Jobs

- Each order/booking/job has at most **one** quote reference: either one One-Off Quote or one Sales Quote.
- The dynamic link (quote_type + quote) makes this explicit and queryable: list views and reports can filter by "Quote" = any document, or by quote_type, or by specific quote name. No ambiguity between one-off and contract quote.

## 10. Affected Areas (Checklist)

| Area | Action |
|------|--------|
| **New DocType** | Add **One-Off Quote** (structure per section 4). |
| **Sales Quote** | Remove one_off field; remove create_*_from_sales_quote methods; adjust link_filters where they reference one_off. **Move all charge-parameter fields from header to child** (section 8): Transport (location_from/to, pick_mode, drop_mode, vehicle_type, load_type, container_type, transport_template), Air (origin_port, destination_port, airline, freight_agent, direction, house/release/entry types, etc.), Sea (sea_load_type, etc.), Warehousing (site, etc.) into Sales Quote Transport, Sales Quote Air Freight, Sales Quote Sea Freight, Sales Quote Warehouse. Update pricing/rate engines and "fetch from quote" logic to use child rows. |
| **Transport Order** | Replace sales_quote with quote_type + quote; update JS (one-off check, charge pull) to use quote_type/quote; charge pull only when quote_type = "Sales Quote". |
| **Air Booking / Sea Booking** | Replace sales_quote with quote_type + quote; "Fetch quotations" only when quote_type = "Sales Quote"; conversion flows from One-Off Quote. |
| **Air Shipment / Sea Shipment** | Replace sales_quote with quote_type + quote. |
| **Declaration / Declaration Order** | Replace sales_quote with quote_type + quote. |
| **Warehouse Contract** | Replace sales_quote with quote_type + quote. |
| **Transport Job** | Add quote_type + quote (from order) or resolve from order; update create_sales_invoice to set quotation/quote from dynamic link. |
| **Warehouse Job / other jobs** | Same pattern if they need to show or use quote reference. |
| **create_from_sales_quote.js** | Rework to "Create from One-Off Quote" (Transport Order, Air Booking, Sea Booking); dialogs filter One-Off Quote by mode. |
| **Charge child tables** | Add quote_type + quote (dynamic); keep or phase out sales_quote_link. |
| **Change Request** | Use quote_type + quote if it should reference both quote types; else keep Link to Sales Quote. |
| **Workspace / shortcuts** | Add One-Off Quote to Pricing Center (or relevant) workspace; update "Create … from Quote" actions to One-Off Quote. |

This design keeps **contract quote** behavior in **Sales Quote** only, moves **one-off** behavior into **One-Off Quote** with conversion to orders/bookings, and makes quote references on orders/bookings/jobs **deterministic** via a single dynamic link (One-Off Quote or Sales Quote).
