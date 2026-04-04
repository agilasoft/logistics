# Customs Authority

**Customs Authority** is the government body that regulates imports/exports in a country or region. In CargoNext, it is a master record used for declarations, permits, and compliance.

To access: **Home > Customs > Master Data > Customs Authority**

## 1. How to Create

1. Go to Customs Authority list, click **New**.
2. Enter **Authority Name**, **Country**, **Code**.
3. Add contact/portal details if applicable.
4. **Save**.

## 2. Usage

- Linked from [Declaration](welcome/declaration), [Declaration Order](welcome/declaration-order), [Permit Application](welcome/permit-application)
- Used for filing compliance and authority-specific rules


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Customs Authority** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Authority Information (`authority_information_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Customs Authority Name (`customs_authority_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Country (`country`) | Link | **Purpose:** Creates a controlled reference to **Country** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Country**. Create the master first if it does not exist. |
| Authority Type (`authority_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: National, Regional, Port, Airport, Border. |
| `column_break_info` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Is Active (`is_active`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Timezone (`timezone`) | Data | **Purpose:** Time zone for SLA windows, cut-offs, and local-time display. **What to enter:** Use the format your organisation standardises (e.g. IANA **Region/City** or a short code from your master list). |
| Contact Information (`contact_information_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Website (`website`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| Phone (`phone`) | Data | **Purpose:** Voice or fax contact for parties, drivers, or brokers. **What to enter:** Phone or fax in local or international format; include country code when needed. |
| Email (`email`) | Data | **Purpose:** Contact email for notices, portal, or authority correspondence. **What to enter:** A valid email address (one line), e.g. name@company.com. |
| `column_break_contact` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Address Line 1 (`address_line_1`) | Data | **Purpose:** Street-level address for pick-up, delivery, or registered office. **What to enter:** Building, street, suite — match what appears on invoices or B/L. |
| Address Line 2 (`address_line_2`) | Data | **Purpose:** Street-level address for pick-up, delivery, or registered office. **What to enter:** Building, street, suite — match what appears on invoices or B/L. |
| City (`city`) | Data | **Purpose:** City or locality for routing, addresses, and manifests. **What to enter:** City name as used on commercial documents. |
| State/Province (`state`) | Data | **Purpose:** Sub-national region for compliance and address blocks. **What to enter:** State, province, or region name or code per local practice. |
| Postal Code (`postal_code`) | Data | **Purpose:** Postal routing for addresses and customs paperwork. **What to enter:** Official postal or ZIP code for the city shown. |
| Processing Information (`processing_information_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Standard Processing Days (`standard_processing_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Express Processing Days (`express_processing_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Operating Hours Start (`operating_hours_start`) | Time | **Purpose:** Clock time for shifts, gate hours, or cut-off times without a full date. **What to enter:** Time only (HH:MM or per ERPNext control). |
| `column_break_processing` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Operating Hours End (`operating_hours_end`) | Time | **Purpose:** Clock time for shifts, gate hours, or cut-off times without a full date. **What to enter:** Time only (HH:MM or per ERPNext control). |
| Working Days (`working_days`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Monday to Friday, Monday to Saturday, All Week, Custom. |
| Public Holidays (comma separated dates) (`public_holidays`) | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |
| Service Level Agreement (`service_level_agreement_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| SLA Standard (Days) (`sla_standard_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| SLA Express (Days) (`sla_express_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| SLA Urgent (Days) (`sla_urgent_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| `column_break_sla` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable SLA Tracking (`enable_sla_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| SLA Alert Threshold (%) (`sla_alert_threshold_percent`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| Integration (`integration_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Has API Integration (`has_api_integration`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| API Endpoint URL (`api_endpoint_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| API Authentication Method (`api_authentication_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: API Key, OAuth, Basic Auth, Token. |
| `column_break_integration` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| API Username (`api_username`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| API Key (`api_key`) | Password | **Purpose:** Field type **Password** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Enable EDI (`enable_edi`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Fee Structure (`fee_structure_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Base Processing Fee (`base_processing_fee`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Express Processing Fee (`express_processing_fee`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Urgent Processing Fee (`urgent_processing_fee`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `column_break_fees` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Additional Notes (`additional_notes_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Notes (`notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Declaration](welcome/declaration)
- [Customs Settings](welcome/customs-settings)
- [Customs Module](welcome/customs-module)
