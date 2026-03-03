# FCL (Full Container Load) – CW1 vs Logistics App Alignment Report

This report compares the **CW1 “Edit Quick Booking”** FCL booking form (Additional Details) with the **Logistics app** Sea Booking and Sea Shipment doctypes to show where the app is aligned and where gaps exist.

**Reference:** CW1 Quick Booking – Details tab (Booking S00190507), FCL sea freight context (Origin PHSFS/Subic Bay → Dest. CAVAN/Vancouver).

---

## 1. Summary

| Category | Aligned | Partial | Not in App |
|----------|---------|---------|------------|
| General / Dates | ✓ | — | 3 |
| Origin / Destination | ✓ | — | — |
| Sailing Summary | ✓ | 1 | 3 |
| Addresses & Contacts | ✓ | 1 | — |
| Agents / Brokers / CTO | — | 1 | 6 |
| Controlling Parties | — | — | 2 |
| Pricing / Cost | — | 1 | 2 |
| Tabs / Structure | ✓ | — | 2 |

**Overall:** Core FCL fields (origin, destination, sailing, vessel/voyage, carrier, house BL, addresses, charges) are **aligned**. Gaps are mainly in **cut-offs**, **agent/broker/CTO roles**, **controlling parties**, **header-level sell/cost**, and **NVOCC/Port Transport**.

---

## 2. Field-by-Field Alignment

### 2.1 General Information

| CW1 Field | Logistics App | Location | Notes |
|-----------|----------------|----------|--------|
| **Booked Date** | ✓ `booking_date` | Sea Booking, Sea Shipment | Aligned. |
| **Client Req. ETA** | ⚠ Partial | `eta` on Sea Booking / Sea Shipment | ETA exists; no separate “Client Requested ETA” vs operational ETA. |
| **Warehouse Rec.** | ✗ | — | Not present. |
| **Interim Receipt** | ✗ | — | Not present. |
| **CFS Reference** | ✗ | — | Not on Sea Booking/Sea Shipment. (CFS exists in Air: Master Air Waybill has `origin_cfs` / `destination_cfs`.) |
| **Booking Party** | ⚠ Partial | `local_customer` | Customer is captured; “Booking Party” in CW1 may be a distinct role (e.g. forwarder); no separate Booking Party field. |

### 2.2 Origin & Destination

| CW1 Field | Logistics App | Location | Notes |
|-----------|----------------|----------|--------|
| **Origin** (code + name) | ✓ `origin_port` | Sea Booking, Sea Shipment | Link to UNLOCO; port name from master. |
| **Dest.** (code + name) | ✓ `destination_port` | Sea Booking, Sea Shipment | Same. |
| **ETD** | ✓ `etd` | Sea Booking, Sea Shipment; also on Routing Leg | Aligned. |
| **ETA** | ✓ `eta` | Sea Booking, Sea Shipment; also on Routing Leg | Aligned. |
| **Load Port / Discharge Port** (display) | ✓ | Routing Leg: `load_port`, `discharge_port` | Per-leg; main leg matches header origin/destination. |

### 2.3 Sailing Summary

| CW1 Field | Logistics App | Location | Notes |
|-----------|----------------|----------|--------|
| **Load Port** | ✓ `load_port` | Sea Booking Routing Leg, Sea Shipment Routing Leg | Aligned. |
| **Discharge Port** | ✓ `discharge_port` | Same | Aligned. |
| **Voyage No** | ✓ `voyage_no` | Sea Booking Routing Leg, Sea Shipment (header + leg) | Aligned. |
| **Vessel** | ✓ `vessel` | Sea Booking Routing Leg, Sea Shipment (header + leg) | Aligned. |
| **CFS Cut Off** | ✗ | — | Not present. |
| **CTO Cut Off** | ✗ | — | Not present. |
| **Estimated Departure / Arrival** | ✓ `etd` / `eta`, `atd` / `ata` | Booking/Shipment and routing legs | Aligned (actuals on shipment). |
| **Carrier** | ✓ `shipping_line` (header), `carrier` (routing leg) | Sea Booking, Sea Shipment, Routing Leg (carrier_type + carrier) | Aligned. |
| **CFS Reference** (in sailing) | ✗ | — | Not present. |
| **Creditor** | ✗ | — | No direct “Creditor”; charges have `pay_to` (Supplier). |
| **House Bill Number** | ✓ `house_bl` | Sea Booking, Sea Shipment | Aligned. |
| **Direct** (checkbox) | ✓ | `entry_type` = "Direct"; `house_type` (e.g. Standard House) | Concept aligned; different field names. |
| **Add New Sailing / View Sailings / Clear Sailing / Import** | ⚠ Partial | Routing Legs table; no dedicated “Sailings” UI or Import | Multiple legs supported; no CW1-style sailing list/import. |

### 2.4 Pickup / Delivery Addresses

| CW1 Field | Logistics App | Location | Notes |
|-----------|----------------|----------|--------|
| **Pickup Address** | ✓ `shipper_address` | Sea Booking, Sea Shipment | With address display; can use Override by choosing different Address. |
| **Delivery Address** | ✓ `consignee_address` | Same | Same. |
| **Override** (per address) | ⚠ Partial | Different Address link effectively overrides | No explicit “Override” checkbox. |
| **Address** (dropdown) | ✓ | Address link + display | Aligned. |
| **Contact** | ✓ `shipper_contact`, `consignee_contact` | Same | Aligned. |

### 2.5 Agents & Brokers

| CW1 Field | Logistics App | Location | Notes |
|-----------|----------------|----------|--------|
| **Pickup CTO** | ✗ | — | Not present. |
| **Delivery CTO** | ✗ | — | Not present. |
| **Pickup Agent** | ✗ | — | Not present. |
| **Delivery Agent** | ✗ | — | Not present. |
| **Export Broker** | ✗ | — | Not present. (Customs Declaration has `customs_broker` only.) |
| **Import Broker** | ✗ | — | Not present. |
| **Freight Agent** (concept) | ✓ `freight_agent` | Sea Booking, Sea Shipment | Single freight agent; no split by pickup/delivery or export/import. |

### 2.6 Port Transport & Controlling Parties

| CW1 Field | Logistics App | Location | Notes |
|-----------|----------------|----------|--------|
| **Port Transport** (e.g. ALLTRAMNL + address) | ✗ | — | Not on Sea Booking/Sea Shipment. |
| **Controlling Customer** | ✗ | — | Not present. |
| **Controlling Agent** | ✗ | — | Not present. |

### 2.7 Pricing / Cost (Header Level)

| CW1 Field | Logistics App | Location | Notes |
|-----------|----------------|----------|--------|
| **Gateway Sell** (single amount) | ⚠ Partial | Charges table: `selling_amount` per line | Revenue by charge line; no single “Gateway Sell” header field. |
| **Negotiated Cost** (single amount) | ⚠ Partial | Charges table: `buying_amount` per line | Cost by charge line; no single “Negotiated Cost” header field. |
| **Use Standard R** / **STD** | ✗ | — | No equivalent “use standard rate” at header. |

### 2.8 Tabs / Form Structure

| CW1 Tab | Logistics App | Notes |
|---------|----------------|--------|
| **Details** | ✓ Details | Main booking/shipment details. |
| **Additional Details** | — | No “Additional Details” tab; some extra fields live in Details or other tabs. |
| **Custom Fields** | ✓ (Frappe) | Custom Fields supported by platform. |
| **Workflow & Tracking** | ✓ (milestones/dashboard) | Sea Shipment: Dashboard, Milestones, SLA, delay/penalty sections. |
| **Billing** | ✓ Charges tab; Accounts | Charges tab + Accounts (company, branch, cost center, profit center). |
| **Addresses** | ✓ Contacts & Addresses (Details); Sea Shipment Addresses tab | Shipper/Consignee addresses and contacts. |
| **Compliance Risk** | ⚠ Partial | Dangerous Goods tab (DG declaration, compliance status). No generic “Compliance Risk” tab. |
| **eDocs** | ✓ Documents tab | Document checklist and Job Document. |
| **Notes** | ✓ Notes tab | Internal Notes, Client Notes. |
| **Logs** | ✓ (Frappe) | Version / doc timeline. |
| **NVOCC Display** (option) | ✗ | Not present. |

---

## 3. Recommendations (if targeting CW1 parity)

1. **Cut-offs:** Add optional **CFS Cut Off** and **CTO Cut Off** (date/datetime) to Sea Booking and/or Sea Shipment (or to routing leg) if required for operations.
2. **References:** Add **Warehouse Rec.**, **Interim Receipt**, and **CFS Reference** as optional data fields where needed.
3. **Booking Party:** If “Booking Party” is distinct from “Customer”, add a **Booking Party** link (e.g. to Customer or a Party doctype).
4. **Agents / CTOs / Brokers:** Add optional links: **Pickup CTO**, **Delivery CTO**, **Pickup Agent**, **Delivery Agent**, **Export Broker**, **Import Broker** (e.g. to Freight Agent or Supplier/Customer), if business requires them.
5. **Controlling parties:** Add **Controlling Customer** and **Controlling Agent** if used for revenue or control reporting.
6. **Port Transport:** Add **Port Transport** (link or data) on Sea Booking/Sea Shipment if needed.
7. **Header sell/cost:** If CW1-style single “Gateway Sell” and “Negotiated Cost” are required, add optional currency fields and keep line-level charges as detail.
8. **NVOCC:** Add **NVOCC Display** (checkbox or role-based view option) if needed for NVOCC workflows.

---

## 4. Document References

- **Logistics app:**  
  - `Sea Booking`: `logistics/sea_freight/doctype/sea_booking/sea_booking.json`  
  - `Sea Booking Routing Leg`: `logistics/sea_freight/doctype/sea_booking_routing_leg/sea_booking_routing_leg.json`  
  - `Sea Shipment`: `logistics/sea_freight/doctype/sea_shipment/sea_shipment.json`  
  - `Sea Shipment Routing Leg`: `logistics/sea_freight/doctype/sea_shipment_routing_leg/sea_shipment_routing_leg.json`  
  - `Sea Booking Charges`: `logistics/sea_freight/doctype/sea_booking_charges/sea_booking_charges.json`  
- **CW1:** Edit Quick Booking – Details tab (FCL), screenshot reference.

---

*Report generated for FCL alignment between CW1 Quick Booking (Additional Details) and the Logistics app Sea Booking / Sea Shipment.*
