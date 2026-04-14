# Shipper

**Shipper** is the party who tenders cargo for transport. In CargoNext, Shipper is a master record linked to Customer or a standalone organization. Used in Sea Freight, Air Freight, Transport, and Customs.

Industry practice: Shipper = exporter (for export) or consignor. May differ from the billing party.

To access: **Home > Sea Freight > Organizations > Shipper** or **Home > Transport > Organizations > Shipper**

## 1. How to Create

1. Go to Shipper list, click **New**.
2. Enter **Shipper Name**, **Customer** (if applicable).
3. Add **Address** and **Contact**.
4. **Save**.

## 2. Usage

- Linked from [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking), [Transport Order](welcome/transport-order), [Declaration](welcome/declaration)
- Address and contact used for documentation (BL, AWB, commercial invoice)


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Shipper** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

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

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Consignee](welcome/consignee)
- [Sea Booking](welcome/sea-booking)
- [Air Booking](welcome/air-booking)
- [Glossary](welcome/glossary)
