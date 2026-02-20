# Entry Type - Industry Standard Definition and Behaviours

## Overview

**Entry Type** describes how cargo enters or moves through customs territory. It affects routing, documentation, customs clearance procedures, and duty treatment. This document defines a unified set of options aligned with industry practice, customs regulations, and competitor systems.

## Industry References

- **U.S. Trade.gov** – Direct Shipment, Transshipment, Imported Directly (FTA rules)
- **19 CFR 10.604** – Transit and transshipment (U.S. customs regulations)
- **UK NCTS** – New Computerised Transit System (Common Transit Convention)
- **EU Customs Transit** – Union transit, common transit procedures
- **TIR Convention** – International road transport under customs seal
- **ICC ATA Carnet** – Temporary admission (exhibitions, samples, professional equipment)
- **WCO** – World Customs Organization guidelines

---

## Unified Entry Type Options

| Option | Description | Customs Treatment | Use Case |
|--------|-------------|-------------------|----------|
| **Direct** | Cargo shipped directly from origin to destination. No intermediate stops or customs clearance en route. Standard import/export procedure. | Full customs clearance at destination (import) or origin (export). Duty paid or deferred per normal rules. | Most common. Point-to-point shipments. |
| **Transit** | Cargo passes through intermediate territory under customs control (TIR, NCTS, In-Bond, common transit). No duty payment at intermediate points. | Goods remain under customs supervision. Transit declaration required. Must reach customs office of destination within stipulated period. | Cross-border transit, EU Common Transit, land-bridge. |
| **Transshipment** | Cargo transferred between vessels/aircraft at an intermediate port or hub. May involve customs at transfer point. | May require temporary storage, customs at transshipment port, or transit procedure through hub. | Hub-and-spoke routing, cargo transfer, feeder services. |
| **ATA Carnet** | Temporary admission for exhibitions, samples, professional equipment. Duty-free for up to 1 year (ICC/WCO). | No duty payment. Carnet serves as customs document. Must re-export within validity. | Trade shows, equipment demos, commercial samples. |

---

## Behaviour by Entry Type

### 1. Direct

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | Standard commercial invoice, packing list, bill of lading. Customs declaration at destination (import) or origin (export). |
| **Customs** | Full import/export clearance. Duty and taxes per normal rules. No transit or temporary admission. |
| **Routing** | Single leg: origin to destination. No intermediate ports for customs purposes. |
| **Validation** | No special checks. Default for most shipments. |
| **Declaration** | Standard declaration type. No transit or carnet fields. |

### 2. Transit

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | Transit declaration (TIR, NCTS, In-Bond). Goods remain under customs seal/supervision. |
| **Customs** | No duty at intermediate points. Transit procedure from office of departure to office of destination. Time limits apply. |
| **Routing** | Multiple legs with intermediate customs offices. `create_routing_for_transit_entry()` can auto-create routing legs. |
| **Validation** | When Transit: ensure routing has transit-compliant legs; transit declaration may be required. |
| **Declaration** | Transit declaration type. Transit reference number, office of departure/destination. |

### 3. Transshipment

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | May require transshipment permit, temporary storage, or transit procedure at hub. |
| **Customs** | Cargo transferred at intermediate port. May clear temporarily or move under transit. Hub customs may apply. |
| **Routing** | Multiple legs with intermediate port(s). Transfer between vessels/aircraft at hub. |
| **Validation** | When Transshipment: routing should reflect intermediate port(s). Transfer documentation. |
| **Declaration** | May require transshipment declaration or transit at hub. |

### 4. ATA Carnet

| Aspect | Behaviour |
|--------|------------|
| **Documentation** | ATA Carnet (ICC). Yellow counterfoils (US), white (foreign), blue (transit). Valid up to 1 year. |
| **Customs** | Temporary admission. No duty. Goods must re-export. Carnet holder responsible for compliance. |
| **Routing** | Standard routing. Special customs handling at each border. |
| **Validation** | Carnet number, validity date. Eligible goods only (samples, exhibitions, professional equipment). |
| **Declaration** | ATA Carnet declaration. Not for sale/lease, processing, or consumables. |

---

## Applicable DocTypes

| DocType | Field | Purpose |
|---------|-------|---------|
| Sales Quote Air Freight | air_entry_type | Quote-level entry type |
| Sales Quote Sea Freight | sea_entry_type | Quote-level entry type |
| Air Booking | entry_type | Booking entry type |
| Air Shipment | entry_type | Shipment entry type |
| Sea Booking | entry_type | Booking entry type |
| Sea Shipment | entry_type | Shipment entry type |
| Air Freight Settings | default_entry_type | Default for new Air Bookings |
| Declaration | (links to shipment) | Customs declaration type may derive from shipment entry_type |

---

## Implementation Behaviours (Code-Level)

### Validation Rules

| Entry Type | Rule | Implementation |
|------------|------|----------------|
| Direct | No special validation | Default. Single leg routing. |
| Transit | Routing may have intermediate legs | `create_routing_for_transit_entry()` creates transit legs when implemented. |
| Transshipment | Routing should include hub/transfer point | Intermediate port in routing. |
| ATA Carnet | Carnet number, validity | When ATA Carnet: validate carnet fields if present. |

### Routing Logic

| Entry Type | Routing Behaviour |
|------------|-------------------|
| Direct | Single leg: origin → destination. |
| Transit | Multiple legs with customs offices. Transit procedure. |
| Transshipment | Multiple legs with intermediate port (transfer point). |
| ATA Carnet | Standard routing. Special customs at borders. |

### Customs / Declaration Integration

- **Direct** – Standard import/export declaration.
- **Transit** – Transit declaration (TIR, NCTS, In-Bond).
- **Transshipment** – Transshipment permit or transit at hub.
- **ATA Carnet** – ATA Carnet declaration; no duty.

### Valid Values (Code)

```python
valid_entry_types = ["Direct", "Transit", "Transshipment", "ATA Carnet"]
```

---

## Migration

| Old Value | New Value |
|-----------|-----------|
| Customs Permit | Direct |
| Break-Bulk | Direct |
| ATA Carnet | ATA Carnet (unchanged) |
| Transshipment | Transshipment (unchanged) |
| (none) | Direct (default) |

---

## Summary

| Entry Type | Customs | Routing | Documentation |
|------------|---------|---------|---------------|
| Direct | Full clearance | Single leg | Standard commercial |
| Transit | No duty at intermediate | Multi-leg, customs offices | Transit declaration |
| Transshipment | May clear at hub | Multi-leg, transfer point | Transshipment/transit |
| ATA Carnet | Temporary, no duty | Standard | ATA Carnet |
