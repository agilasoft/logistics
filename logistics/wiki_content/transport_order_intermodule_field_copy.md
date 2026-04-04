# Transport Order: fields copied from shipments (inter-module create)

Reference implementation: `logistics.utils.module_integration` — `create_transport_order_from_air_shipment`, `create_transport_order_from_sea_shipment`, and helpers. Parent-level DG copy uses `logistics.utils.dg_fields.copy_parent_dg_header`.

## Field name standard (freight ↔ transport)

**`contains_dangerous_goods`** is the standard parent flag on Air Shipment, Sea Shipment, Air Booking, Sea Booking, Transport Order, Transport Job, and Transport Leg (the latter fetches from the job). This matches package-level **`contains_dangerous_goods`** on Transport Order Package and Transport Job Package.

**`hazardous`** remains only where it denotes capability or classification, not “this move contains DG”: e.g. **Vehicle Type** (equipment can handle hazmat), **Commodity** / **Commodities** (product is hazardous).

## Air Shipment → Transport Order (header)

| Target (`Transport Order`) | Source (`Air Shipment`) | Notes |
|----------------------------|-------------------------|--------|
| `air_shipment` | (argument) | Link set explicitly |
| `customer` | `local_customer` | |
| `shipper` | `shipper` | |
| `consignee` | `consignee` | |
| `booking_date` | `booking_date` or today | |
| `scheduled_date` | `eta` or `etd` or `booking_date` or today | |
| `location_type` | — | Fixed `"UNLOCO"` |
| `location_from` | `origin_port` | |
| `location_to` | `destination_port` | |
| `transport_job_type` | — | Fixed `"Non-Container"` |
| `company` | `company` or default | |
| `branch` | `branch` | |
| `cost_center` | `cost_center` | |
| `profit_center` | `profit_center` | |
| `project` | `project` | |
| `sales_quote` | `sales_quote` | When set on shipment |
| `contains_dangerous_goods` | `contains_dangerous_goods` | Same name as freight |
| `dg_declaration_complete` | `dg_declaration_complete` | |
| `dg_compliance_status` | `dg_compliance_status` | |
| `dg_emergency_contact` | `dg_emergency_contact` | |
| `dg_emergency_phone` | `dg_emergency_phone` | |
| `dg_emergency_email` | `dg_emergency_email` | |

**Legs child (one row when shipper + consignee):** `facility_type_from`/`facility_from`, `facility_type_to`/`facility_to`, `scheduled_date`, `transport_job_type`, optional `pick_address` / `drop_address` from `shipper_address` / `consignee_address`.

## Sea Shipment → Transport Order (header)

Same pattern as air, except:

| Target | Source | Notes |
|--------|--------|--------|
| `sea_shipment` | (argument) | |
| `transport_job_type` | `"Container"` if `container_type` else `"Non-Container"` | |
| `container_type` | `container_type` | |
| `container_no` | First `containers[].container_no` or first package `container` | |

DG header mapping uses `copy_parent_dg_header` (same fields as air).

## Packages: Air Shipment Packages / Sea Freight Packages → Transport Order Package

Implemented in `logistics.utils.dg_fields.transport_order_package_row_from_shipment_pkg`: common measurements plus **`PACKAGE_DG_FIELDS`**, and child `contains_dangerous_goods` when the shipment is flagged or the line has DG identifiers.

## Transport Order → Transport Job (`action_create_transport_job`)

Header uses `copy_parent_dg_header(doc, job)` so **`contains_dangerous_goods`** and all parent DG tab fields copy. Packages copy by intersecting child field names (includes DG columns where both child tables match).

## Comparison: Inbound Order from shipment

Different target: **does not** copy DG header or DG package detail. It either uses `warehouse_items` or default warehouse item + `quantity`, `uom`, `weight`, `volume` per package.

## `propagate_from_air_shipment` / `propagate_from_sea_shipment` (link on save)

When a doc is saved with `air_shipment` / `sea_shipment` set, **Transport Order** only receives: `location_type`, `location_from`, `location_to`, `booking_date`, `customer` (if empty). **No DG propagation** on that path.

## Migration

`logistics.patches.v1_0_rename_transport_hazardous_to_contains_dangerous_goods` renames DB column `hazardous` → `contains_dangerous_goods` on Transport Order, Transport Job, and Transport Leg **before** schema sync.


<!-- wiki-field-reference:start -->

## Complete field reference

_Header and package fields are on the transport and freight DocTypes. Full schemas:_

- [Transport Order](welcome/transport-order), [Transport Job](welcome/transport-job)
- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment)
- [Inbound Order](welcome/inbound-order) _(when created from shipment)_

<!-- wiki-field-reference:end -->

