# House Type and Entry Type – Implementation Status

This document tracks which features, validations, and behaviours from `HOUSE_TYPE_DESIGN.md` and `ENTRY_TYPE_DESIGN.md` are implemented in the codebase.

---

## House Type – Implementation Status

### Implemented

| Feature | Location | Status |
|---------|----------|--------|
| **Options** (Standard House, Co-load Master, Blind Co-load Master, Co-load House, Buyer's Consol Lead, Shipper's Consol Lead, Break Bulk) | Sea Booking, Sea Shipment, Air Booking, Air Shipment, Sales Quote Air/Sea Freight, One-Off Quote, Air Freight Settings | Done |
| **Consolidation validation** – Block Standard House and Break Bulk from being added to consolidation | `sea_consolidation.py` `add_sea_shipment()`, `air_consolidation.py` `add_air_freight_job()` | Done |
| **IATA AWBType** – "H" when house_type is set, "M" when not | `iata_cargo_xml/message_builder.py` line 211 | Done |
| **Default from settings** – Air Shipment gets default_house_type from Air Freight Settings | `air_shipment.py` before_save, `air_shipment.js` onload | Done |
| **Copy on conversion** – house_type copied from Booking to Shipment | `air_booking.py`, `sea_booking.py` convert_to_shipment | Done |
| **Copy from Sales Quote** – house_type mapped when creating from quote | `sales_quote.py`, `air_booking.py` | Done |
| **Migration** – Revert Direct→Standard House, Consolidation→Co-load Master; normalize Break-Bulk | `v1_0_align_house_type_options.py` | Done |

### Not Implemented

| Feature | Design Reference | Status |
|---------|------------------|--------|
| **Master Bill required by house type** | Consolidation types: master_bill expected when in consolidation | Not implemented – no validation that Consolidation/Co-load Master require master_bill when in consolidation |
| **Consolidation picklist filter** | Filter shipments by house_type when adding to consolidation (only show Consolidation, Co-load House types) | Not implemented – user can type any shipment name; validation only blocks at add time |
| **Co-load House specific logic** | Ensure consolidation is "Co-load" type when forwarder is house party | Not implemented – no distinction between own consolidation vs co-load consolidation |
| **Break Bulk** – no containers validation | Break Bulk: packages may use different units; no containers | Not implemented – no house_type-specific validation for Break Bulk |

---

## Entry Type – Implementation Status

### Implemented

| Feature | Location | Status |
|---------|----------|--------|
| **Options** (Direct, Transit, Transshipment, ATA Carnet) | Sea Booking, Sea Shipment, Air Booking, Air Shipment, Sales Quote Air/Sea Freight, Air Freight Settings | Done |
| **Validation** – valid entry types only | `air_booking.py` validate_required_fields | Done |
| **Sales Quote mapping** – validate and map entry_type from quote to booking | `sales_quote.py` map_sales_quote_entry_type_to_air_booking | Done |
| **Copy on conversion** – entry_type copied from Booking to Shipment | `air_booking.py`, `sea_booking.py` convert_to_shipment | Done |
| **Copy from Sales Quote** – entry_type mapped when creating from quote | `sales_quote.py`, `air_booking.py` | Done |
| **Default from settings** – Air Shipment gets default_entry_type from Air Freight Settings | `air_shipment.py` before_save, `air_shipment.js` onload | Done |
| **Migration** – Customs Permit→Direct, Break-Bulk→Direct | `v1_0_align_sea_shipment_entry_type.py` | Done |

### Not Implemented

| Feature | Design Reference | Status |
|---------|------------------|--------|
| **Sea Booking / Sea Shipment entry_type validation** | Validate entry_type against valid values | Not implemented – Sea Booking has no entry_type validation in validate() |
| **create_routing_for_transit_entry()** | Transit/Transshipment: auto-create routing legs | Not implemented – documented in TRANSIT_ENTRY_ROUTING_IMPLEMENTATION.md but method not present in codebase |
| **Transit** – routing with intermediate customs offices | Transit: multiple legs with customs offices | Not implemented |
| **Transshipment** – routing with hub/transfer point | Transshipment: intermediate port in routing | Not implemented |
| **ATA Carnet** – carnet number, validity validation | ATA Carnet: validate carnet fields if present | Not implemented – no carnet-specific validation |
| **Declaration integration** | Declaration type may derive from shipment entry_type | Not implemented – Declaration does not use entry_type from linked shipment |

---

## Summary

| Category | Implemented | Not Implemented |
|----------|-------------|-----------------|
| **House Type** | Options, consolidation block, IATA AWBType, defaults, copy, migration | Master bill required, picklist filter, Co-load House logic, Break Bulk validation |
| **Entry Type** | Options, Air Booking validation, mapping, copy, defaults, migration | Sea Booking validation, routing auto-creation, Transit/Transshipment routing, ATA Carnet validation, Declaration integration |

---

## Recommendations

1. **House Type**: Add master_bill validation when house_type is in (Co-load Master, Blind Co-load Master, Buyer's Consol Lead, Shipper's Consol Lead) and shipment is in a consolidation.
2. **Entry Type**: Add entry_type validation in Sea Booking and Sea Shipment (same as Air Booking).
3. **Entry Type**: Implement `create_routing_for_transit_entry()` in Air Booking and Air Shipment per TRANSIT_ENTRY_ROUTING_IMPLEMENTATION.md, or update the design doc to mark it as planned/optional.
4. **Declaration**: Consider linking shipment entry_type to declaration type when creating declarations from shipments.
