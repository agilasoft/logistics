# Routing Tab Design — Air and Sea Freight Booking and Shipment

## 1. Overview

This document defines the **Routing Tab** for Air and Sea Freight **Booking** and **Shipment** doctypes: a single tab where users can define and manage **routing legs** (multi-leg journeys) with ports, carrier/vessel or flight, and timings. The design is based on industry practice and alignment with the existing logistics app rather than copying every possible field.

**In scope:** Air Booking, Sea Booking, Air Shipment, Sea Shipment.

---

## 2. Research and Applicability

### 2.1 Industry and standards

- **Ocean:** DCSA Commercial Schedules and Port Call standards use **ETA, ETD** and Estimated/Planned/Actual times; vessel schedules use **port, ETA, ETD, cut-off times**. Flexport’s ShipmentLeg uses origin, destination, **estimated/actual departure and arrival**, **transportation_mode**, **carrier_name**; ocean legs add **vessel_name**, **voyage_number**.
- **Air:** IATA e-AWB and Cargo-XML focus on booking and waybill; routing is typically **flight/voyage**, **origin/destination**, **ETD/ETA** (and actuals when known).
- **Common core:** Leg = **origin port**, **destination port**, **ETD, ETA, ATD, ATA**, **mode**, **carrier**; for **sea** **vessel + voyage number**, for **air** **flight number**. One or two **cut-off**-type dates (e.g. documents due) are widely used; fine-grained CTO/CFS/VGM fields are optional and can be phased.

### 2.2 Existing app

- **Booking/Shipment** already have document-level **origin_port**, **destination_port**, **etd**, **eta** (and **atd**/ **ata** on Shipment). Sea Shipment has **vessel** (Data). Ports: **UNLOCO** on Shipment and reports; Sea Booking uses **Location** in schema (reports often use UNLOCO). Carrier: **Shipping Line** (sea), **Airline** (air).
- **Freight Routing** (standalone) and **Freight Routing Items** (child) already implement multi-leg routing with: **mode**, **type** (Main / Pre-carriage / On-forwarding), **status**, **charter**; **loading_port** / **discharge_port** (Link → Location); **etd**, **atd**, **eta**, **ata**; **cutoff_date**, **documents_due_date**, **received_date**, **available_date**, **storage_date**; **origin_cto** / **destination_cto** (Cargo Terminal Operator). No vessel/voyage on the leg.

So the Routing Tab should **reuse concepts** from Freight Routing Items and Booking/Shipment, use **UNLOCO** for ports where the app standard is UNLOCO (Shipment/reports), and add **vessel + voyage** for sea and **flight number** for air as the main gap for booking/shipment-level routing.

### 2.3 Design principle

Include only **fields that are clearly applicable** for day-to-day routing and visibility: leg sequence, mode, ports, timings, carrier, **vessel + voyage** (sea) or **flight** (air), status/type, and a small set of cut-offs. Omit or defer: internal identifiers (“Defined By”), “Is Linked” (until schedule integration exists), many CTO/CFS/VGM variants, creditor/carrier ref/service string/service level, and “Published” until schedule import is implemented.

---

## 3. Goals

- **Single place for routing:** One “Routing” tab per Booking/Shipment with all legs in order.
- **Leg-level detail:** Each leg has mode, ports, ETD/ETA/ATD/ATA, carrier; for sea **vessel + voyage**, for air **flight number**.
- **Consistency with app:** Reuse port (UNLOCO), carrier (Shipping Line / Airline), and date/datetime conventions from existing doctypes.
- **Extensibility:** Optional cut-off fields and actions (Map, Import Schedules) can be added in a later phase.

---

## 4. Scope

| Document      | Routing Tab |
|---------------|-------------|
| Air Booking   | Yes         |
| Sea Booking   | Yes         |
| Air Shipment  | Yes         |
| Sea Shipment  | Yes         |

The tab contains:

1. A **Routing Legs** table (child table) listing legs.
2. **Routing Leg Details** shown when a row is selected (or in an inline form below the grid).

---

## 5. Recommended Fields

### 5.1 Essential (every leg)

These are the minimum for a useful routing leg and align with industry and existing app.

| Field           | Type     | Description | Notes |
|-----------------|----------|-------------|--------|
| `leg_order`     | Int      | Leg sequence (1, 2, 3, …). | Unique per parent, used for sort. |
| `mode`          | Select   | SEA / AIR. | Default from parent (Air doc → AIR, Sea doc → SEA); allow override for multi-modal. |
| `load_port`     | Link     | Port of loading. | Options: **UNLOCO** (recommended to align with Shipment/reports). |
| `discharge_port`| Link     | Port of discharge. | Same as load_port. |
| `etd`           | Datetime | Estimated Time of Departure. | Use Datetime if parent uses it elsewhere; else Date. |
| `eta`           | Datetime | Estimated Time of Arrival. | |
| `atd`           | Datetime | Actual Time of Departure. | |
| `ata`           | Datetime | Actual Time of Arrival. | |
| `carrier`       | Link     | Carrier. | **Shipping Line** (sea) or **Airline** (air). Dynamic Link or separate fields by mode if needed. |
| **Sea freight only** |||
| `vessel`        | Data     | Vessel name. | Shown when mode = SEA. Sea Shipment already uses Data for vessel. |
| `voyage_no`     | Data     | Voyage number. | **Sea freight only.** Shown when mode = SEA. |
| **Air freight only** |||
| `flight_no`     | Data     | Flight number. | **Air freight only.** Shown when mode = AIR. |

### 5.2 Recommended (widely used)

| Field           | Type   | Description | Notes |
|-----------------|--------|-------------|--------|
| `type`          | Select | Leg type. | e.g. **Main**, **Pre-carriage**, **On-forwarding**, **Other** (align with Freight Routing Items). |
| `status`        | Select | Leg status. | e.g. **Confirmed**, **Planned**, **On-hold** (align with Freight Routing Items). |
| `charter_route` | Check  | Charter route. | Optional; matches existing “Charter” on Freight Routing Items. |
| `notes`         | Small Text / Long Text | Free-form notes for the leg. | |

### 5.3 Optional / Phase 2

Include only if there is a clear use case; otherwise defer.

| Field / concept      | Use when |
|----------------------|----------|
| Cut-off / documents due | One field (e.g. `documents_due` or `cutoff_date`) is enough for most needs; align with Freight Routing Items. |
| Terminal (departure_from / arrival_at) | When CTO/terminal-level tracking is required; can be Link to Cargo Terminal Operator or Location. |
| CTO/CFS/VGM-specific dates | Only if operations require multiple distinct cut-offs; otherwise one generic cut-off is sufficient. |
| “Defined By” (external id) | When integrating with an external system that sends a leg id. |
| “Is Linked” / “Published” | When implementing import from global sailing/flight schedules. |
| Creditor, Carrier Ref., Service String, Carrier Service Level | When commercial or billing workflows need them; not required for core routing. |
| Map, Published Schedules, Import Schedules | Implement as actions when map or schedule data is available. |

---

## 6. Routing Legs Table (Child Table)

**Child DocTypes:** e.g. Air Booking Routing Leg, Sea Booking Routing Leg, Air Shipment Routing Leg, Sea Shipment Routing Leg (one per parent type).

**Table columns (grid view)** — use the essential + recommended fields only:

| Column    | Field           | In list view | Note |
|-----------|-----------------|--------------|------|
| Leg       | `leg_order`     | Yes          | |
| Mode      | `mode`          | Yes          | |
| Type      | `type`          | Yes          | |
| Status    | `status`        | Yes          | |
| Vessel    | `vessel`        | Yes          | **Sea only** (hide when mode = AIR). |
| Voyage    | `voyage_no`     | Yes          | **Sea only** (hide when mode = AIR). |
| Flight    | `flight_no`     | Yes          | **Air only** (hide when mode = SEA). |
| Load Port | `load_port`     | Yes          | |
| Discharge | `discharge_port`| Yes          | |
| ETD       | `etd`           | Yes          | |
| ETA       | `eta`           | Yes          | |
| ATD       | `atd`           | Optional     | |
| ATA       | `ata`           | Optional     | |

No “Defined By” or “Is Linked” in the grid unless phase-2 integration is in scope.

---

## 7. Routing Leg Details (Form)

When a leg row is selected (or a new leg is added), show a details form with:

- **Leg details:** Leg Order, Mode, Type, Status, Charter Route.
- **Sea freight (when mode = SEA):** Vessel, Voyage No, Carrier.
- **Air freight (when mode = AIR):** Flight No, Carrier.
- **Origin:** Load Port, ETD, ATD.
- **Destination:** Discharge Port, ETA, ATA.
- **Notes.**

Optionally one **cut-off** or **documents due** date in origin or a small “Cut-offs” section. Terminal (departure_from / arrival_at) and extra CTO/CFS/VGM fields only in phase 2.

**Actions (phase 2):** Map, Published Schedules, Import Global Sailing Schedules, Import Global Flights — add when map/schedule integrations exist.

---

## 8. Alignment with Existing App

- **Voyage vs Flight:** **Voyage** is used only for **sea freight** (vessel + voyage number). **Flight** is used only for **air freight** (flight number). Use separate fields `voyage_no` and `flight_no`; show and validate by mode (SEA → vessel, voyage_no; AIR → flight_no).
- **Ports:** Use **UNLOCO** for `load_port` and `discharge_port` to align with Sea Shipment, Sea Consolidation, and reports. If the app later standardizes Sea Booking on UNLOCO, keep consistency.
- **Carrier:** Reuse **Shipping Line** (sea) and **Airline** (air). Implement via Dynamic Link (`carrier_type` + `carrier`) or two optional Link fields (one for sea, one for air) and show by mode.
- **Dates:** Use **Date** if parent and Freight Routing Items use Date; use **Datetime** if more precision is needed (e.g. Sea Consolidation uses Datetime). Keep one convention across the Routing Tab.
- **Naming:** No need for a user-facing “Defined By”;
  - child name can be auto (e.g. `parent_name-{idx}` or naming series). Add an external id only for integrations.

---

## 9. Behaviour and Validation

- **Leg order:** `leg_order` unique per parent; auto-set on add (e.g. max + 1); reorder on delete if desired.
- **Mode:** Default from parent (Air → AIR, Sea → SEA); allow other modes for multi-modal.
- **Ports:** Validate against UNLOCO (or Location if that is the chosen standard). Optionally check that first leg’s load_port and last leg’s discharge_port align with parent origin/destination.
- **Sync to parent (optional):** For single-leg or primary leg, consider syncing first leg’s ETD/ETA and last leg’s ATD/ATA to parent `etd`/`eta`/`atd`/`ata` for list views and reports.

---

## 10. Implementation Checklist

- [ ] Create child DocTypes: Air Booking Routing Leg, Sea Booking Routing Leg, Air Shipment Routing Leg, Sea Shipment Routing Leg with **essential + recommended** fields only.
- [ ] Add “Routing” tab and Routing Legs table to Air Booking, Sea Booking, Air Shipment, Sea Shipment.
- [ ] Implement Routing Leg Details (inline or on row selection) with sections: Leg details; Vessel & Voyage (sea) or Flight (air) by mode; Origin; Destination; Notes.
- [ ] Use UNLOCO for ports; Shipping Line / Airline for carrier (Dynamic Link or mode-based fields).
- [ ] Add validation for leg_order and optional port/mode rules.
- [ ] Optional: Sync first/last leg timings to parent.
- [ ] Phase 2: One cut-off/documents_due field if needed; Map and Import Schedules actions when integrations are ready.

This design keeps the Routing Tab focused on **applicable, high-value fields** and aligns with industry practice and the existing logistics codebase.
