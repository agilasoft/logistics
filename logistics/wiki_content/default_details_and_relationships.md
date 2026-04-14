# Default Details and Relationships

This page describes **default details** to set up for key parties (Shipper, Consignee) and service providers (Freight Agent, Carrier/Shipping Line, Airline), and how they **relate** across Sea Freight, Air Freight, Transport, and Customs.

To access organizations: **Home > Sea Freight > Organizations** or **Home > Transport > Organizations**

## 1. Shipper

**Shipper** is the party who tenders cargo for transport (exporter/consignor). Used on bookings, shipments, transport orders, declarations, and quotes.

### 1.1 Default details to set

| Field / area | Purpose |
|--------------|--------|
| **Shipper Name** | Display name; required. |
| **Customer** | Link to ERPNext Customer (optional; for billing/portal). |
| **Address** | At least one address (pickup/origin); used for BL, AWB, commercial invoice. |
| **Contact** | At least one contact; used for documentation and notifications. |

Create masters via **Home > Sea Freight > Organizations > Shipper** (or Transport > Organizations > Shipper). No system-wide “default shipper” is applied; users choose the shipper per [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking), [Transport Order](welcome/transport-order), [Declaration](welcome/declaration), [Sales Quote](welcome/sales-quote), and warehousing orders.

### 1.2 Relationships

- **Bookings:** [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking) – shipper + shipper address/contact.
- **Shipments:** [Sea Shipment](welcome/sea-shipment), [Air Shipment](welcome/air-shipment) – shipper and addresses flow from booking or are set on the shipment.
- **Transport:** [Transport Order](welcome/transport-order) – shipper for pickup/origin.
- **Customs:** [Declaration](welcome/declaration) – shipper for export/import.
- **Pricing:** [Sales Quote](welcome/sales-quote) – shipper for the quoted party.
- **Warehousing:** [Inbound Order](welcome/inbound-order), [Release Order](welcome/release-order), [Transfer Order](welcome/transfer-order), [Warehouse Job](welcome/warehouse-job), [Warehouse Contract](welcome/warehouse-contract), [VAS Order](welcome/vas-order), [Stocktake Order](welcome/stocktake-order).

---

## 2. Consignee

**Consignee** is the party to whom cargo is delivered (importer/receiver). Used on the same document types as Shipper for the delivery side.

### 2.1 Default details to set

| Field / area | Purpose |
|--------------|--------|
| **Consignee Name** | Display name; required. |
| **Customer** | Link to ERPNext Customer (optional). |
| **Address** | At least one address (delivery); used for BL, AWB, delivery legs. |
| **Contact** | At least one contact; used for documentation and notifications. |

Create masters via **Home > Sea Freight > Organizations > Consignee** (or Transport > Organizations > Consignee). There is no system-wide “default consignee”; selection is per document.

### 2.2 Relationships

- **Bookings:** [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking) – consignee + consignee address/contact.
- **Shipments:** [Sea Shipment](welcome/sea-shipment), [Air Shipment](welcome/air-shipment) – consignee and addresses from booking or set on shipment.
- **Transport:** [Transport Order](welcome/transport-order) – consignee for delivery.
- **Customs:** [Declaration](welcome/declaration) – consignee for export/import.
- **Pricing:** [Sales Quote](welcome/sales-quote).
- **Warehousing:** Same as Shipper (Inbound Order, Release Order, Transfer Order, Warehouse Job, Warehouse Contract, VAS Order, Stocktake Order).
- **Consolidations:** [Sea Consolidation](welcome/sea-consolidation), [Air Consolidation](welcome/air-consolidation) – package-level shipper/consignee.

---

## 3. Freight Agent

**Freight Agent** is the intermediary that arranges freight with carriers. Create Freight Agent masters and optionally set **defaults** so new Sea/Air documents pick a default agent.

### 3.1 Default details to set (master)

- **Agent name** and any required identifiers.
- **Address / contact** if used for correspondence or documentation.

Freight Agent is a shared master used across Sea and Air Freight.

### 3.2 Where defaults are applied

| Module | Settings document | Default field | Used on |
|--------|-------------------|---------------|--------|
| Sea Freight | [Sea Freight Settings](welcome/sea-freight-settings) | **Default Freight Agent** | Sea Shipment, Sea Booking (optional), Sales Quote Sea Freight |
| Air Freight | [Air Freight Settings](welcome/air-freight-settings) | **Default Freight Agent** | Air Shipment, Air Booking (optional), Air Consolidation, Sales Quote Air Freight, Master AWB |

Set **Default Freight Agent** in the relevant settings so new Sea Shipments and Air Shipments (and related documents) are pre-filled when no agent is already selected.

---

## 4. Carrier / Shipping Line (Sea) and Airline (Air)

**Carrier** in CargoNext is represented by **Shipping Line** (sea) and **Airline** (air). Set these masters and then set **defaults** in module settings so new documents are pre-filled.

### 4.1 Sea: Shipping Line

| What to set | Where | Purpose |
|-------------|--------|--------|
| Shipping Line masters | **Home > Sea Freight** (e.g. list/workspace for Shipping Line) | Used on Sea Booking, Sea Shipment, Sea Consolidation, Master Bill, routing legs, rates. |
| **Default Shipping Line** | [Sea Freight Settings](welcome/sea-freight-settings) → Business Settings | Default for new Sea Shipments (and related sea documents). |

### 4.2 Air: Airline

| What to set | Where | Purpose |
|-------------|--------|--------|
| Airline masters | **Home > Air Freight** (Airline list) | Used on Air Booking, Air Shipment, Air Consolidation, Master AWB, flight schedules, rates. |
| **Default Airline** | [Air Freight Settings](welcome/air-freight-settings) → Business Settings | Default for new Air Shipments and related air documents. |

### 4.3 Other “carrier” defaults

- **Manifest / Customs:** Where manifest or customs integration supports a carrier, **Default Carrier** may be configured in the relevant Customs or manifest settings for e-manifest or similar flows.

---

## 5. Summary

| Party / provider | Master(s) to create | Default configured in | Applied on |
|------------------|---------------------|------------------------|------------|
| **Shipper** | Shipper (name, customer, address, contact) | — (per document) | Bookings, Shipments, Transport Order, Declaration, Quotes, Warehousing |
| **Consignee** | Consignee (name, customer, address, contact) | — (per document) | Same as Shipper |
| **Freight Agent** | Freight Agent | Sea Freight Settings, Air Freight Settings | Sea/Air Shipments, Bookings, Consolidations, Quotes, Master AWB |
| **Carrier (Sea)** | Shipping Line | Sea Freight Settings → Default Shipping Line | Sea Shipment, Sea Booking, Sea Consolidation, Master Bill |
| **Carrier (Air)** | Airline | Air Freight Settings → Default Airline | Air Shipment, Air Booking, Air Consolidation, Master AWB |
| **Carrier (Manifest)** | As per customs/manifest setup | Manifest Settings (e.g. Default Carrier) | E-manifest / customs manifests |

Ensure at least one **Shipper** and one **Consignee** (with address and contact) exist before creating bookings or shipments. For Sea and Air, create at least one **Freight Agent**, one **Shipping Line** (sea), and one **Airline** (air), and set the **defaults** in [Sea Freight Settings](welcome/sea-freight-settings) and [Air Freight Settings](welcome/air-freight-settings) so new documents are filled automatically where applicable.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocTypes **Shipper**, **Consignee**, **Freight Agent** (subsections below) and their nested child tables, in form order. Columns: **Label** (`field name`), **Type**, **Description**._

### Shipper

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Details (`details_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Shipper Name (`shipper_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `column_break_mmav` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Exporter Category (`exporter_category`) | Link | **Purpose:** Creates a controlled reference to **Exporter Category** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Exporter Category**. Create the master first if it does not exist. |
| Country (`country`) | Link | **Purpose:** Creates a controlled reference to **Country** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Country**. Create the master first if it does not exist. |
| Default Currency (`default_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Default Incoterm (`default_incoterm`) | Link | **Purpose:** Creates a controlled reference to **Incoterm** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Incoterm**. Create the master first if it does not exist. |
| General defaults (`section_general_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Notify Party (`default_notify_party`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Default Notify Party Address (`default_notify_party_address`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| `column_break_general` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Service Level (`default_service_level`) | Link | **Purpose:** Creates a controlled reference to **Logistics Service Level** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Service Level**. Create the master first if it does not exist. |
| Air Freight (`air_freight_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Air freight defaults (`section_air_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Sending Agent (Air) (`air_default_sending_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Default Receiving Agent (Air) (`air_default_receiving_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| `column_break_air_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Broker (Air) (`air_default_broker`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Default Document Template (Air) (`air_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Air) (`air_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_air_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Terms (Air) (`air_default_tc_name`) | Link | **Purpose:** Creates a controlled reference to **Terms and Conditions** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Terms and Conditions**. Create the master first if it does not exist. |
| Default Additional Terms (Air) (`air_default_additional_terms`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Default Client Notes (Air) (`air_default_client_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Sea Freight (`sea_freight_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Sea freight defaults (`section_sea_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Sending Agent (Sea) (`sea_default_sending_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Default Receiving Agent (Sea) (`sea_default_receiving_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| `column_break_sea_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Broker (Sea) (`sea_default_broker`) | Link | **Purpose:** Creates a controlled reference to **Broker** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Broker**. Create the master first if it does not exist. |
| Default Freight Consolidator (`sea_default_freight_consolidator`) | Link | **Purpose:** Creates a controlled reference to **Freight Consolidator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Consolidator**. Create the master first if it does not exist. |
| Default Document Template (Sea) (`sea_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Sea) (`sea_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_sea_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Terms (Sea) (`sea_default_tc_name`) | Link | **Purpose:** Creates a controlled reference to **Terms and Conditions** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Terms and Conditions**. Create the master first if it does not exist. |
| Default Additional Terms (Sea) (`sea_default_additional_terms`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Default Client Notes (Sea) (`sea_default_client_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Customs (`customs_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Customs defaults (`section_customs_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Customs Broker (`customs_default_broker`) | Link | **Purpose:** Creates a controlled reference to **Broker** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Broker**. Create the master first if it does not exist. |
| Default Freight Agent (Customs) (`customs_default_freight_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| `column_break_customs_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Trade Agreement (`customs_default_trade_agreement`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Default Marks and Numbers (`customs_default_marks_and_numbers`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Default Document Template (Customs) (`customs_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Customs) (`customs_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_customs_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Special Instructions (Customs) (`customs_default_special_instructions`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Transport (`transport_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Transport defaults (`section_transport_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Document Template (Transport) (`transport_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Transport) (`transport_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_transport_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Client Notes (Transport) (`transport_default_client_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Default Internal Notes (Transport) (`transport_default_internal_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Addresses and Contacts (`addresses_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `addresses_and_contacts` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Addresses (`address_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| `column_break_ekpq` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Contacts (`contact_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| `section_break_unej` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Primary Address (`shipper_primary_address`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. |
| Pick Address (`pick_address`) | Link | **From definition:** Default address for transport pickups **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. |
| `primary_address` | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |
| `column_break_giwp` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Primary Contact (`shipper_primary_contact`) | Link | **Purpose:** Creates a controlled reference to **Contact** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Contact**. Create the master first if it does not exist. |

### Consignee

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Details (`details_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Consignee Name (`consignee_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Customs (`section_break_customs`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Customs Importer Classification (`customs_importer_classification`) | Select | **From definition:** Customs lane classification (SGL=Super Green Lane, GL=Green Lane) **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: SGL, GL, Yellow Lane, Red Lane, Not Classified. |
| General defaults (`section_general_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Notify Party (`default_notify_party`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Default Notify Party Address (`default_notify_party_address`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| `column_break_general` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Service Level (`default_service_level`) | Link | **Purpose:** Creates a controlled reference to **Logistics Service Level** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Service Level**. Create the master first if it does not exist. |
| Default Incoterm (`default_incoterm`) | Link | **Purpose:** Creates a controlled reference to **Incoterm** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Incoterm**. Create the master first if it does not exist. |
| Default Currency (`default_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Default Payment Terms (`default_payment_terms`) | Link | **Purpose:** Creates a controlled reference to **Payment Terms Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Payment Terms Template**. Create the master first if it does not exist. |
| Air Freight (`air_freight_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Air freight defaults (`section_air_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Receiving Agent (Air) (`air_default_receiving_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Default Broker (Air) (`air_default_broker`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| `column_break_air_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Customs Broker (Air) (`air_default_customs_broker`) | Link | **Purpose:** Creates a controlled reference to **Supplier** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Supplier**. Create the master first if it does not exist. |
| Default Document Template (Air) (`air_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Air) (`air_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_air_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Terms (Air) (`air_default_tc_name`) | Link | **Purpose:** Creates a controlled reference to **Terms and Conditions** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Terms and Conditions**. Create the master first if it does not exist. |
| Default Client Notes (Air) (`air_default_client_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Sea Freight (`sea_freight_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Sea freight defaults (`section_sea_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Receiving Agent (Sea) (`sea_default_receiving_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Default Broker (Sea) (`sea_default_broker`) | Link | **Purpose:** Creates a controlled reference to **Broker** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Broker**. Create the master first if it does not exist. |
| `column_break_sea_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Freight Consolidator (`sea_default_freight_consolidator`) | Link | **Purpose:** Creates a controlled reference to **Freight Consolidator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Consolidator**. Create the master first if it does not exist. |
| Default Document Template (Sea) (`sea_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Sea) (`sea_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_sea_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Terms (Sea) (`sea_default_tc_name`) | Link | **Purpose:** Creates a controlled reference to **Terms and Conditions** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Terms and Conditions**. Create the master first if it does not exist. |
| Default Client Notes (Sea) (`sea_default_client_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Customs (`customs_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Customs defaults (`section_customs_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Customs Broker (`customs_default_broker`) | Link | **Purpose:** Creates a controlled reference to **Broker** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Broker**. Create the master first if it does not exist. |
| Default Freight Agent (Customs) (`customs_default_freight_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| `column_break_customs_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Trade Agreement (`customs_default_trade_agreement`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Default Marks and Numbers (`customs_default_marks_and_numbers`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Default Payment Terms (Customs) (`customs_default_payment_terms`) | Link | **Purpose:** Creates a controlled reference to **Payment Terms Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Payment Terms Template**. Create the master first if it does not exist. |
| Default Document Template (Customs) (`customs_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Customs) (`customs_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_customs_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Special Instructions (Customs) (`customs_default_special_instructions`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Default Country of Origin (`customs_default_country_of_origin`) | Link | **Purpose:** Creates a controlled reference to **Country** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Country**. Create the master first if it does not exist. |
| Transport (`transport_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Transport defaults (`section_transport_defaults`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Document Template (Transport) (`transport_default_document_template`) | Link | **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Default Milestone Template (Transport) (`transport_default_milestone_template`) | Link | **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| `column_break_transport_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Client Notes (Transport) (`transport_default_client_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Default Internal Notes (Transport) (`transport_default_internal_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Addresses and Contacts (`addresses_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `addresses_and_contacts` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Addresses (`address_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| `column_break_nivp` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Contacts (`contact_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| `section_break_vizq` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Primary Address (`consignee_primary_address`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. |
| Delivery Address (`delivery_address`) | Link | **From definition:** Default address for transport deliveries **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. |
| Primary Address (`primary_address`) | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |
| `column_break_umfc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Primary Contact (`consignee_primary_contact`) | Link | **Purpose:** Creates a controlled reference to **Contact** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Contact**. Create the master first if it does not exist. |
| Connections (`connections_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |

### Freight Agent

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Freight Agent Name (`freight_agent_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `column_break_pbzu` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Organization (`tab_2_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Supplier (`supplier`) | Link | **Purpose:** Creates a controlled reference to **Supplier** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Supplier**. Create the master first if it does not exist. |
| Related Parties (`related_parties_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| AR Netting Group (`ar_netting_group`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| AP Netting Group (`ap_netting_group`) | Link | **Purpose:** Creates a controlled reference to **Supplier** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Supplier**. Create the master first if it does not exist. |

<!-- wiki-field-reference:end -->

## 6. Related Topics

- [Shipper](welcome/shipper)
- [Consignee](welcome/consignee)
- [Sea Freight Settings](welcome/sea-freight-settings)
- [Air Freight Settings](welcome/air-freight-settings)
- [Getting Started](welcome/getting-started)
- [Sea Freight Module](welcome/sea-freight-module)
- [Air Freight Module](welcome/air-freight-module)
- [Glossary](welcome/glossary)
