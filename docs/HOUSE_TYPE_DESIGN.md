# House Type - Industry Standard Definition and Behaviours

## Overview

**House Type** describes the bill-of-lading structure and the forwarder's role in the shipment. It determines whether the forwarder issues a House Bill (HBL/HAWB) or operates under a Master Bill (MBL/MAWB), and how consolidation is handled. This document defines industry-aligned options with specific behaviours for each type.

## Industry References

- **House vs Master Bill of Lading** – HBL issued by forwarder to shipper; MBL issued by carrier to forwarder (Unishippers, CBP OHBOL FAQ)
- **NVOCC / Co-loader** – Master Consolidator vs Co-load House (King Freight, GoFreight)
- **46 CFR § 520.11** – NVOCC co-loading disclosure requirements (US)
- **IATA Cargo** – HAWB vs MAWB in air freight (CargoEZ, CargoNet)
- **Master Bill Types** – Direct, Co-Load, Agent Consolidation (existing Master Bill doctype)

---

## Unified House Type Options

| Option | Description | Bill Structure | Use Case |
|--------|-------------|----------------|----------|
| **Standard House** | Single shipper, direct booking. Forwarder books space with carrier and issues one House Bill to the customer. | One HBL/HAWB per shipment; MBL/MAWB may show forwarder or carrier. | FCL, full container, single-customer shipments. |
| **Co-load Master** | Multiple shippers combined. Forwarder consolidates LCL cargo, issues HBLs to each shipper, receives one MBL from carrier. | Multiple HBLs; one MBL. Forwarder is master on MBL. | LCL, groupage, forwarder-led consolidation. |
| **Blind Co-load Master** | Same as Co-load Master but party details not disclosed to carrier. | Multiple HBLs; one MBL. Forwarder is master on MBL. | LCL where carrier does not see individual shipper/consignee. |
| **Co-load House** | Forwarder's cargo travels under another forwarder's Master Bill. Forwarder is a co-loader (house party), not the master. | One HBL per shipment; MBL held by another forwarder. | Space purchase from consolidator, co-load arrangements. |
| **Buyer's Consol Lead** | Buyer consolidates: collects cargo from multiple suppliers for one destination. | Multiple HBLs; one MBL. Forwarder is master. | Import consolidation, buyer-led groupage. |
| **Shipper's Consol Lead** | Shipper consolidates: sends cargo to multiple buyers from one origin. | Multiple HBLs; one MBL. Forwarder is master. | Export consolidation, shipper-led groupage. |
| **Break Bulk** | Non-containerized cargo (loose cartons, pallets, project cargo) stowed directly in vessel hold. | May use HBL or MBL depending on arrangement. | Oversized, heavy lift, non-containerized. |

---

## Behaviour by House Type

### 1. Standard House

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | Single House Bill (HBL/HAWB) per shipment. Master Bill optional; if used, typically shows forwarder as shipper/consignee. |
| **Master Bill link** | Optional. If `master_bill` is set, it represents the carrier's MBL under which this direct shipment travels. |
| **Consolidation** | Not applicable. Shipment cannot be added to Sea/Air Consolidation. |
| **Validation** | No consolidation-specific checks. |
| **IATA AWBType** | `H` (House) when generating FSU/FWB. |
| **Transport mode** | Typically FCL (sea) or full ULD (air). |

### 2. Co-load Master / Blind Co-load Master / Buyer's Consol Lead / Shipper's Consol Lead

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | Multiple House Bills; one Master Bill for the consolidated load. Forwarder is master on MBL. |
| **Master Bill link** | Expected when consolidation is created. Links to Master Bill covering the consolidated container/flight. |
| **Consolidation** | Shipment can be added to Sea Consolidation or Air Consolidation. Forwarder creates the consolidation. |
| **Validation** | When added to consolidation: validate route compatibility, weight/volume limits, dangerous goods. |
| **IATA AWBType** | `H` (House) for individual HAWBs; consolidation has MAWB. |
| **Transport mode** | Typically LCL (sea) or part ULD (air). |

### 3. Co-load House

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | House Bill only. Master Bill is held by another forwarder (consolidator). Forwarder does not receive MBL. |
| **Master Bill link** | Optional reference to consolidator's MBL (for tracking). Forwarder is not the master. |
| **Consolidation** | Shipment can be added to a consolidation created by another party. Forwarder is co-loader, not consolidation owner. |
| **Validation** | When in consolidation: ensure consolidation is "Co-load" type; forwarder is house party. |
| **IATA AWBType** | `H` (House). |
| **Transport mode** | LCL or part ULD. |

### 4. Break Bulk

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | House Bill or Master Bill depending on arrangement. Cargo not in containers. |
| **Master Bill link** | Optional. |
| **Consolidation** | Generally not applicable (break bulk is not LCL groupage). Special break-bulk consolidations may exist. |
| **Validation** | No containers; packages may use different units (pieces, pallets). Weight/volume required. |
| **IATA AWBType** | `H` or `M` depending on arrangement. |
| **Transport mode** | Break Bulk (sea); air may use charter or special handling. |

---

## Applicable DocTypes

| DocType | Field | Purpose |
|---------|-------|---------|
| Sales Quote Air Freight | air_house_type | Quote-level house type |
| Sales Quote Sea Freight | sea_house_type | Quote-level house type |
| Air Booking | house_type | Booking house type |
| Air Shipment | house_type | Shipment house type |
| Sea Booking | house_type | Booking house type |
| Sea Shipment | house_type | Shipment house type |
| Air Consolidation | (derived from shipments) | Consolidation contains House-type shipments |
| Sea Consolidation | (derived from shipments) | Consolidation contains House-type shipments |
| Master Bill | master_type | Direct, Co-Load, Agent Consolidation, etc. |
| Air Freight Settings | default_house_type | Default for new Air Bookings |
| Sea Freight Settings | default_house_type | Default for new Sea Bookings (if added) |

---

## Implementation Behaviours (Code-Level)

### Validation Rules

| House Type | Rule | Implementation |
|------------|------|----------------|
| Standard House | Cannot add to consolidation | `house_type == "Standard House"` → block "Add to Consolidation" |
| Co-load Master, Blind Co-load Master, Buyer's Consol Lead, Shipper's Consol Lead | Can add to consolidation; forwarder is master | Allow add; consolidation owner = current company |
| Co-load House | Can add to consolidation; forwarder is house party | Allow add; consolidation may be external/co-load |
| Break Bulk | No standard consolidation | Block or allow per business rule |

### Master Bill Logic

| House Type | master_bill required | master_bill meaning |
|------------|----------------------|----------------------|
| Standard House | No | If set: carrier MBL for this direct shipment |
| Co-load Master, Blind Co-load Master, Buyer's Consol Lead, Shipper's Consol Lead | Yes (when in consolidation) | MBL for the consolidated load |
| Co-load House | No (MBL held by consolidator) | Optional ref to consolidator's MBL |
| Break Bulk | No | Optional |

### IATA / Cargo XML

- `AWBType = "H"` when `house_type` is set (any value) and forwarder issues HAWB.
- `AWBType = "M"` when forwarder is master and issues MAWB (e.g. consolidation master).

### Consolidation Filtering

- **Sea Consolidation**: Include shipments where `house_type` in `("Co-load Master", "Blind Co-load Master", "Buyer's Consol Lead", "Shipper's Consol Lead", "Co-load House")`.
- **Air Consolidation**: Same logic.
- **Standard House** and **Break Bulk** (when not in special consol): Exclude from standard consolidation picklists.

---

## Migration

If data was previously migrated to simplified values (Direct, Consolidation), revert to original values:

| Old Value | New Value |
|-----------|-----------|
| Direct | Standard House |
| Consolidation | Co-load Master |
| (none) | Standard House (default) |

**Options kept as-is**: Co-load House, Break Bulk, Blind Co-load Master, Buyer's Consol Lead, Shipper's Consol Lead.

---

## Summary

| House Type | HBL/HAWB | MBL/MAWB | Consolidation | Typical Mode |
|------------|----------|----------|---------------|--------------|
| Standard House | Yes (1:1) | Optional | No | FCL |
| Co-load Master | Yes (many) | Yes (master) | Yes (owner) | LCL |
| Blind Co-load Master | Yes (many) | Yes (master) | Yes (owner) | LCL |
| Co-load House | Yes (1:1) | No (held by other) | Yes (house party) | LCL |
| Buyer's Consol Lead | Yes (many) | Yes (master) | Yes (owner) | LCL |
| Shipper's Consol Lead | Yes (many) | Yes (master) | Yes (owner) | LCL |
| Break Bulk | Yes/No | Optional | No/Special | Break Bulk |
