# Shipper & Consignee — Recommended Default Fields per Service Type

## Overview

When a Shipper or Consignee is selected on a transaction, many downstream fields can be auto-populated from stored defaults. This avoids repetitive data entry and enforces consistency.

This document recommends new fields to add to the **Shipper** and **Consignee** master doctypes. Each field is scoped to a specific service type (Air, Sea, Customs, Transport) so the same shipper/consignee can carry different defaults for different logistics flows.

### Current State

Today, Shipper and Consignee carry only a handful of default fields:

| Doctype | Existing Default Fields |
|---|---|
| **Shipper** | `exporter_category`, `country`, `default_currency`, `default_incoterm`, `pick_address`, `shipper_primary_address`, `shipper_primary_contact` |
| **Consignee** | `customs_importer_classification`, `delivery_address`, `consignee_primary_address`, `consignee_primary_contact` |

The recommendations below fill the gaps identified by analysing every field on the Air, Sea, Customs, and Transport transaction doctypes that is a good candidate for per-shipper/consignee defaulting.

---

## Shipper — Recommended Fields

### General Defaults (apply across service types)

These already exist or are broadly useful beyond a single module.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `default_notify_party` | Default Notify Party | Data | Free-text name; populates `notify_party` on Air/Sea transactions |
| `default_notify_party_address` | Default Notify Party Address | Small Text | Address text; populates `notify_party_address` |
| `default_service_level` | Default Service Level | Link | Logistics Service Level |

### Air Freight Defaults

Fields to add under a **Air Freight Defaults** section/tab on Shipper.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `air_default_sending_agent` | Default Sending Agent (Air) | Link | Freight Agent |
| `air_default_receiving_agent` | Default Receiving Agent (Air) | Link | Freight Agent |
| `air_default_broker` | Default Broker (Air) | Link | Freight Agent |
| `air_default_document_template` | Default Document Template (Air) | Link | Document List Template |
| `air_default_milestone_template` | Default Milestone Template (Air) | Link | Milestone Template |
| `air_default_tc_name` | Default Terms (Air) | Link | Terms and Conditions |
| `air_default_additional_terms` | Default Additional Terms (Air) | Data | Free text |
| `air_default_client_notes` | Default Client Notes (Air) | Text Editor | Boilerplate instructions for air bookings |

### Sea Freight Defaults

Fields to add under a **Sea Freight Defaults** section/tab on Shipper.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `sea_default_sending_agent` | Default Sending Agent (Sea) | Link | Freight Agent |
| `sea_default_receiving_agent` | Default Receiving Agent (Sea) | Link | Freight Agent |
| `sea_default_broker` | Default Broker (Sea) | Link | Broker (Sea Booking) / Freight Agent (Sea Shipment) |
| `sea_default_freight_consolidator` | Default Freight Consolidator | Link | Freight Consolidator — Sea Booking only |
| `sea_default_document_template` | Default Document Template (Sea) | Link | Document List Template |
| `sea_default_milestone_template` | Default Milestone Template (Sea) | Link | Milestone Template |
| `sea_default_tc_name` | Default Terms (Sea) | Link | Terms and Conditions |
| `sea_default_additional_terms` | Default Additional Terms (Sea) | Small Text | Free text |
| `sea_default_client_notes` | Default Client Notes (Sea) | Text Editor | Boilerplate instructions for sea bookings |

### Customs Defaults

Fields to add under a **Customs Defaults** section/tab on Shipper.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `customs_default_broker` | Default Customs Broker | Link | Broker — populates `customs_broker` on Declaration / Declaration Order |
| `customs_default_freight_agent` | Default Freight Agent (Customs) | Link | Freight Agent |
| `customs_default_trade_agreement` | Default Trade Agreement | Data | Free text; populates `trade_agreement` |
| `customs_default_marks_and_numbers` | Default Marks and Numbers | Long Text | Populates `marks_and_numbers` |
| `customs_default_document_template` | Default Document Template (Customs) | Link | Document List Template |
| `customs_default_milestone_template` | Default Milestone Template (Customs) | Link | Milestone Template |
| `customs_default_special_instructions` | Default Special Instructions (Customs) | Long Text | Populates `special_instructions` |

### Transport Defaults

Fields to add under a **Transport Defaults** section/tab on Shipper.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `transport_default_document_template` | Default Document Template (Transport) | Link | Document List Template |
| `transport_default_milestone_template` | Default Milestone Template (Transport) | Link | Milestone Template |
| `transport_default_client_notes` | Default Client Notes (Transport) | Text Editor | Standing pickup / handling instructions |
| `transport_default_internal_notes` | Default Internal Notes (Transport) | Text Editor | Internal standing instructions (e.g. "always use closed van") |

---

## Consignee — Recommended Fields

### General Defaults (apply across service types)

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `default_notify_party` | Default Notify Party | Data | Free-text name; populates `notify_party` on Air/Sea transactions |
| `default_notify_party_address` | Default Notify Party Address | Small Text | Address text |
| `default_service_level` | Default Service Level | Link | Logistics Service Level |
| `default_incoterm` | Default Incoterm | Link | Incoterm — consignee-side Incoterm preference (Shipper already has this) |
| `default_currency` | Default Currency | Link | Currency — for charge/pricing context |
| `default_payment_terms` | Default Payment Terms | Link | Payment Terms Template |

### Air Freight Defaults

Fields to add under an **Air Freight Defaults** section/tab on Consignee.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `air_default_receiving_agent` | Default Receiving Agent (Air) | Link | Freight Agent — destination agent |
| `air_default_broker` | Default Broker (Air) | Link | Freight Agent |
| `air_default_customs_broker` | Default Customs Broker (Air) | Link | Supplier — present on Air Shipment |
| `air_default_document_template` | Default Document Template (Air) | Link | Document List Template |
| `air_default_milestone_template` | Default Milestone Template (Air) | Link | Milestone Template |
| `air_default_tc_name` | Default Terms (Air) | Link | Terms and Conditions |
| `air_default_client_notes` | Default Client Notes (Air) | Text Editor | Boilerplate delivery/handling notes |

### Sea Freight Defaults

Fields to add under a **Sea Freight Defaults** section/tab on Consignee.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `sea_default_receiving_agent` | Default Receiving Agent (Sea) | Link | Freight Agent — destination agent |
| `sea_default_broker` | Default Broker (Sea) | Link | Broker / Freight Agent |
| `sea_default_freight_consolidator` | Default Freight Consolidator | Link | Freight Consolidator |
| `sea_default_document_template` | Default Document Template (Sea) | Link | Document List Template |
| `sea_default_milestone_template` | Default Milestone Template (Sea) | Link | Milestone Template |
| `sea_default_tc_name` | Default Terms (Sea) | Link | Terms and Conditions |
| `sea_default_client_notes` | Default Client Notes (Sea) | Text Editor | Boilerplate delivery/handling notes |

### Customs Defaults

Fields to add under a **Customs Defaults** section/tab on Consignee.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `customs_default_broker` | Default Customs Broker | Link | Broker — populates `customs_broker` |
| `customs_default_freight_agent` | Default Freight Agent (Customs) | Link | Freight Agent |
| `customs_default_trade_agreement` | Default Trade Agreement | Data | Free text |
| `customs_default_marks_and_numbers` | Default Marks and Numbers | Long Text | |
| `customs_default_payment_terms` | Default Payment Terms (Customs) | Link | Payment Terms Template |
| `customs_default_document_template` | Default Document Template (Customs) | Link | Document List Template |
| `customs_default_milestone_template` | Default Milestone Template (Customs) | Link | Milestone Template |
| `customs_default_special_instructions` | Default Special Instructions (Customs) | Long Text | |
| `customs_default_country_of_origin` | Default Country of Origin | Link | Country — many consignees receive from same origin |

### Transport Defaults

Fields to add under a **Transport Defaults** section/tab on Consignee.

| Field Name | Label | Type | Options / Notes |
|---|---|---|---|
| `transport_default_document_template` | Default Document Template (Transport) | Link | Document List Template |
| `transport_default_milestone_template` | Default Milestone Template (Transport) | Link | Milestone Template |
| `transport_default_client_notes` | Default Client Notes (Transport) | Text Editor | Standing delivery instructions (e.g. "call before delivery", "dock 3 only") |
| `transport_default_internal_notes` | Default Internal Notes (Transport) | Text Editor | Internal notes (e.g. "requires tail-lift truck") |

---

## Suggested UI Layout

Both Shipper and Consignee should use **Tab Breaks** to organise the new defaults cleanly:

```
[Details]  [Air Freight]  [Sea Freight]  [Customs]  [Transport]  [Addresses and Contacts]
```

Each service-type tab contains only the defaults relevant to that service, keeping the form uncluttered.

---

## Population Logic

When a shipper or consignee is selected on a transaction, the system should auto-populate empty fields from the matching service-type defaults. The recommended approach:

1. **Client-side (`onchange`)** — Use `frappe.call` to fetch the shipper/consignee doc and populate fields immediately in the UI for quick feedback.
2. **Server-side (`validate` or `before_save`)** — As a safety net, populate any still-empty defaultable fields from the master record.
3. **Precedence rule** — Never overwrite a field the user has already filled. Only populate when the target field is empty/null.
4. **Service-type scoping** — Use the service-type prefix to select the right default. For example, on an Air Booking, read from `air_default_*` fields; on a Sea Booking, read from `sea_default_*` fields.

### Example (Air Booking — shipper selected)

```python
if self.shipper and not self.sending_agent:
    shipper_doc = frappe.get_cached_doc("Shipper", self.shipper)
    self.sending_agent = shipper_doc.get("air_default_sending_agent")
    self.receiving_agent = self.receiving_agent or shipper_doc.get("air_default_receiving_agent")
    self.broker = self.broker or shipper_doc.get("air_default_broker")
    self.document_list_template = self.document_list_template or shipper_doc.get("air_default_document_template")
    self.milestone_template = self.milestone_template or shipper_doc.get("air_default_milestone_template")
    self.tc_name = self.tc_name or shipper_doc.get("air_default_tc_name")
    self.additional_terms = self.additional_terms or shipper_doc.get("air_default_additional_terms")
    self.client_notes = self.client_notes or shipper_doc.get("air_default_client_notes")
    self.notify_party = self.notify_party or shipper_doc.get("default_notify_party")
    self.notify_party_address = self.notify_party_address or shipper_doc.get("default_notify_party_address")
    self.service_level = self.service_level or shipper_doc.get("default_service_level")
    self.incoterm = self.incoterm or shipper_doc.get("default_incoterm")
```

---

## Summary Matrix

Mapping of which transaction fields get populated from which master default, by service type.

### Shipper → Transaction Field

| Transaction Field | Air | Sea | Customs | Transport |
|---|---|---|---|---|
| `sending_agent` | `air_default_sending_agent` | `sea_default_sending_agent` | — | — |
| `receiving_agent` | `air_default_receiving_agent` | `sea_default_receiving_agent` | — | — |
| `broker` | `air_default_broker` | `sea_default_broker` | `customs_default_broker` | — |
| `freight_agent` | — | — | `customs_default_freight_agent` | — |
| `freight_consolidator` | — | `sea_default_freight_consolidator` | — | — |
| `incoterm` | `default_incoterm` | `default_incoterm` | `default_incoterm` | — |
| `service_level` | `default_service_level` | `default_service_level` | `default_service_level` | `default_service_level` |
| `document_list_template` | `air_default_document_template` | `sea_default_document_template` | `customs_default_document_template` | `transport_default_document_template` |
| `milestone_template` | `air_default_milestone_template` | `sea_default_milestone_template` | `customs_default_milestone_template` | `transport_default_milestone_template` |
| `tc_name` | `air_default_tc_name` | `sea_default_tc_name` | — | — |
| `additional_terms` | `air_default_additional_terms` | `sea_default_additional_terms` | — | — |
| `notify_party` | `default_notify_party` | `default_notify_party` | — | — |
| `notify_party_address` | `default_notify_party_address` | `default_notify_party_address` | — | — |
| `client_notes` | `air_default_client_notes` | `sea_default_client_notes` | — | `transport_default_client_notes` |
| `internal_notes` | — | — | — | `transport_default_internal_notes` |
| `special_instructions` | — | — | `customs_default_special_instructions` | — |
| `trade_agreement` | — | — | `customs_default_trade_agreement` | — |
| `marks_and_numbers` | — | — | `customs_default_marks_and_numbers` | — |

### Consignee → Transaction Field

| Transaction Field | Air | Sea | Customs | Transport |
|---|---|---|---|---|
| `receiving_agent` | `air_default_receiving_agent` | `sea_default_receiving_agent` | — | — |
| `broker` | `air_default_broker` | `sea_default_broker` | `customs_default_broker` | — |
| `customs_broker` | `air_default_customs_broker` | — | `customs_default_broker` | — |
| `freight_agent` | — | — | `customs_default_freight_agent` | — |
| `freight_consolidator` | — | `sea_default_freight_consolidator` | — | — |
| `incoterm` | `default_incoterm` | `default_incoterm` | `default_incoterm` | — |
| `currency` | `default_currency` | `default_currency` | `default_currency` | — |
| `payment_terms` | — | — | `customs_default_payment_terms` | — |
| `service_level` | `default_service_level` | `default_service_level` | `default_service_level` | `default_service_level` |
| `document_list_template` | `air_default_document_template` | `sea_default_document_template` | `customs_default_document_template` | `transport_default_document_template` |
| `milestone_template` | `air_default_milestone_template` | `sea_default_milestone_template` | `customs_default_milestone_template` | `transport_default_milestone_template` |
| `tc_name` | `air_default_tc_name` | `sea_default_tc_name` | — | — |
| `notify_party` | `default_notify_party` | `default_notify_party` | — | — |
| `notify_party_address` | `default_notify_party_address` | `default_notify_party_address` | — | — |
| `client_notes` | `air_default_client_notes` | `sea_default_client_notes` | — | `transport_default_client_notes` |
| `internal_notes` | — | — | — | `transport_default_internal_notes` |
| `special_instructions` | — | — | `customs_default_special_instructions` | — |
| `trade_agreement` | — | — | `customs_default_trade_agreement` | — |
| `marks_and_numbers` | — | — | `customs_default_marks_and_numbers` | — |
| `country_of_origin` | — | — | `customs_default_country_of_origin` | — |
| `customs_importer_classification` | — | — | *(already exists)* | — |
