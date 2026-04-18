# Customs Settings

**Customs Settings** is a single-document configuration that defines default values and behavior for the Customs module. It controls declaration defaults, compliance, document requirements, and integration options.

To access Customs Settings, go to:

**Home > Customs > Customs Settings**

## 1. Prerequisites

Before configuring Customs Settings, ensure the following are set up:

- Company, Branch (from ERPNext)
- [Customs Authority](welcome/customs-authority) – Customs authorities
- [Commodity](welcome/commodity) – HS code masters
- [Document List Template](welcome/document-list-template) – For document requirements

## 2. How to Configure

1. Go to **Customs Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Company for new declarations
- **Default Branch** – Branch for customs operations
- **Default Customs Authority** – Default authority for declarations
- **Default Currency** – Currency for duty/tax

### 3.2 Declaration Settings

- **Default Declaration Type** – Import, Export, Transit
- **Require HS Code** – Require HS code for commodities
- **Require Commodity Description** – Require detailed description
- **Auto Calculate Duty** – Automatically calculate duty from rates

### 3.3 Document Settings

- **Default Document List Template** – Template for declaration documents
- **Require Commercial Invoice** – Mandatory for submission
- **Require Packing List** – Mandatory for submission
- **Require Bill of Lading** – Mandatory for import

### 3.4 Compliance Settings

- **Enable Compliance Alerts** – Alert for compliance issues
- **Compliance Check Interval** – How often to check
- **Enable Manifest Integration** – Integrate with manifest systems

### 3.5 Integration Settings

- **Enable Customs Clearance Tracking** – Track clearance status
- **Enable EDI Submission** – Submit declarations via EDI
- **Customs Portal URL** – Portal for manual submission


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Customs Settings** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| General Settings (`general_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Customs Authority (`default_customs_authority`) | Link | **Purpose:** Creates a controlled reference to **Customs Authority** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customs Authority**. Create the master first if it does not exist. |
| Default Currency (`default_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| `column_break_general` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Cost Center (`default_cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Default Profit Center (`default_profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| Default Branch (`default_branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Declaration Settings (`declaration_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Declaration Type (`default_declaration_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Transit, Bonded. |
| Auto Assign Declaration Number (`auto_assign_declaration_number`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Require HS Code (`require_hs_code`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_declaration` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Declaration Status (`default_declaration_status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Draft, Submitted, Under Review, Cleared, Released, Rejected, Cancelled. |
| Enable Declaration Amendments (`enable_declaration_amendments`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Maximum Amendment Count (`max_amendment_count`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Permits and Exemptions (Declaration Submit) (`permits_exemptions_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Block Submit if Required Permit Not Obtained (`block_submit_if_required_permit_not_obtained`) | Check | **From definition:** Prevent submit when a required permit is not obtained (linked Permit Application status must be Approved or Renewed). **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Block Submit if Permit Expired (`block_submit_if_permit_expired`) | Check | **From definition:** Prevent submit when an obtained permit is past its expiry date. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Permit Expiring Warning (Days) (`permit_expiring_warn_days`) | Int | **From definition:** Show a non-blocking warning when an obtained permit expires within this many days (unless Block if Permit Expires Within Days applies). **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| `column_break_permits_exemptions` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Block Submit if Permit Expires Within (Days) (`block_submit_if_permit_expires_within_days`) | Int | **From definition:** If greater than zero, block submit when an obtained permit's expiry falls within this many days from today (expired permits use Block if Permit Expired). **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Block Submit if Exemption Certificate Invalid (`block_submit_if_exemption_cert_invalid`) | Check | **From definition:** Prevent submit when a linked Exemption Certificate record is missing. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Block Submit if Exemption Certificate Not Active (`block_submit_if_exemption_cert_not_active`) | Check | **From definition:** Prevent submit when the Exemption Certificate status is not Active. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Block Submit if Exemption Certificate Expired (`block_submit_if_exemption_cert_expired`) | Check | **From definition:** Prevent submit when the Exemption Certificate valid-to date is in the past. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Workflow Settings (`workflow_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Approval Workflow (`enable_approval_workflow`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Require Approval for Submission (`require_approval_for_submission`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_workflow` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Auto Submit on Approval (`auto_submit_on_approval`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Status Notifications (`enable_status_notifications`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Integration Settings (`integration_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Customs Authority API (`enable_customs_authority_api`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| API Endpoint URL (`api_endpoint_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| API Authentication Key (`api_authentication_key`) | Password | **Purpose:** Field type **Password** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| `column_break_integration` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable EDI Integration (`enable_edi_integration`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| EDI Provider (`edi_provider`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Custom, Third Party. |
| Enable Government Portal Integration (`enable_government_portal`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Compliance Settings (`compliance_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Compliance Tracking (`enable_compliance_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Require Document Attachments (`require_document_attachments`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Document Expiry Alert Days (`document_expiry_alert_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| `column_break_compliance` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable Compliance Alerts (`enable_compliance_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Compliance Check Interval (Hours) (`compliance_check_interval_hours`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Default Retention Period (Days) (`default_retention_period_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Calculation Settings (`calculation_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Revenue Calculation Method (`default_revenue_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Base Plus Additional, First Plus Additional, Percentage. |
| Default Cost Calculation Method (`default_cost_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Base Plus Additional, First Plus Additional, Percentage. |
| `column_break_calculation` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable Auto Calculation (`enable_auto_calculation`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Round Off Precision (`round_off_precision`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Notification Settings (`notification_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Email Notifications (`enable_email_notifications`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Notify on Submission (`notify_on_submission`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Notify on Approval (`notify_on_approval`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_notification` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Notify on Rejection (`notify_on_rejection`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Notify on Status Change (`notify_on_status_change`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default Email Template (`default_email_template`) | Link | **Purpose:** Creates a controlled reference to **Email Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Email Template**. Create the master first if it does not exist. |
| Sustainability Settings (`sustainability_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Sustainability Tracking (`enable_sustainability_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default Paper Usage Factor (pages) (`default_paper_usage_factor`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_sustainability` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Carbon Factor (kg CO2e) (`default_carbon_factor`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Additional Settings (`additional_settings_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Additional Features (`additional_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Bulk Operations (`enable_bulk_operations`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Advanced Analytics (`enable_advanced_analytics`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_additional` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable Mobile Access (`enable_mobile_access`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Notes (`notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Declaration Order](welcome/declaration-order)
- [Declaration](welcome/declaration)
- [Commodity](welcome/commodity)
- [Customs Authority](welcome/customs-authority)
- [Document Management](welcome/document-management)
