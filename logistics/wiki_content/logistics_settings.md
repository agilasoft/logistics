# Logistics Settings

**Logistics Settings** is a single-document configuration that defines global defaults and behavior shared across CargoNext modules. It controls company defaults, numbering, recognition, and cross-module options.

To access Logistics Settings, go to:

**Home > Logistics > Logistics Settings**

## 1. Prerequisites

Before configuring Logistics Settings, ensure the following are set up:

- Company, Branch, Cost Center, Profit Center (from ERPNext)
- Naming Series for key doctypes (if custom)

## 2. How to Configure

1. Go to **Logistics Settings** (single document; no list).
2. Configure each tab/section as needed (including **Credit Control** for customer credit enforcement—see §3.6 and [Credit Management](welcome/credit-management)).
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Default company for new logistics documents
- **Default Branch** – Default branch
- **Default Cost Center** – Default cost center for job costing
- **Default Profit Center** – Default profit center
- **Default Currency** – Default currency for charges

### 3.2 Naming Settings

- **Sea Booking Naming Series** – Naming for Sea Booking
- **Sea Shipment Naming Series** – Naming for Sea Shipment
- **Air Booking Naming Series** – Naming for Air Booking
- **Air Shipment Naming Series** – Naming for Air Shipment
- **Transport Order Naming Series** – Naming for Transport Order
- **Transport Job Naming Series** – Naming for Transport Job
- **Declaration Order Naming Series** – Naming for Declaration Order
- **Declaration Naming Series** – Naming for Declaration
- **Warehouse Job Naming Series** – Naming for Warehouse Job

### 3.3 Recognition Settings

- **Enable WIP Recognition** – Enable work-in-progress recognition for jobs
- **Default Recognition Policy** – Policy for revenue/cost recognition
- **Recognition Date Basis** – Basis for recognition (ETD, ETA, Job Date)

### 3.4 Integration Settings

- **Enable ERPNext Sales Order Integration** – Link to ERPNext Sales Order
- **Enable ERPNext Purchase Integration** – Link to ERPNext Purchase
- **Default Item Group** – Default for logistics items

### 3.5 Portal Settings

- **Enable Customer Portal** – Enable portal for customers
- **Portal Default Route** – Default route after login
- **Enable Transport Jobs Portal** – Enable transport jobs on portal
- **Enable Warehouse Jobs Portal** – Enable warehouse jobs on portal
- **Enable Stock Balance Portal** – Enable stock balance on portal

### 3.6 Credit Control

Use the **Credit Control** tab to turn on logistics-wide credit enforcement:

1. **Hold conditions** — When a customer is treated as on hold (manual **Credit Status** on Customer, credit limit breach, overdue receivables, etc.).
2. **Bypass role** (optional) — Users with this role skip credit blocks.
3. **Apply hold to all DocTypes** — When checked, every registered logistics DocType gets full Warn + Hold; the **Subject DocTypes** table is disabled and ignored.
4. **DocTypes subject to credit hold** — When (3) is off, table **Subject DocTypes**: one row per DocType with **Warn on save**, **Hold create**, **Hold submit**, and **Hold print / PDF** (independent toggles per row).

Temporary exceptions use **Credit Hold Lift Request** (submitted by Credit Manager).

See **[Credit Management](welcome/credit-management)** for full behaviour, lift requests, and technical notes.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Logistics Settings** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Transport Order (`transport_order_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Allowed Routing Legs (`transport_order_section`) | Section Break | **From definition:** Define which routing leg types can create Transport Orders from Air/Sea Shipment. E.g. Import + On-forwarding (company controls delivery), Export + Pre-carriage (company controls pickup). **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Allowed Legs (`allowed_transport_order_legs`) | Table | **Purpose:** Stores repeating **Logistics Settings Transport Order Leg** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Routing & Maps (`routing_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Routing Provider (`routing_provider`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Disabled, OSRM, Mapbox, Google. |
| OSRM Base URL (`osrm_base_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| Mapbox API Key (`routing_mapbox_api_key`) | Password | **Purpose:** Field type **Password** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Google API Key (`routing_google_api_key`) | Password | **Purpose:** Field type **Password** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Default Avg Speed (KPH) (`routing_default_avg_speed_kmh`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_rifi` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Routing Auto Compute (`routing_auto_compute`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Routing Show Map (`routing_show_map`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Map Renderer (`map_renderer`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: OpenStreetMap, Google Maps, Mapbox, MapLibre. |
| Maps Enable External Links (`maps_enable_external_links`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Routing Tiles URL (`routing_tiles_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| Routing Tiles Attr (`routing_tiles_attr`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Routing Timeout (sec) (`routing_timeout_sec`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Temperature Limits (`temperature_validation_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Minimum Temperature (°C) (`min_temp`) | Float | **From definition:** Minimum allowed temperature in degrees Celsius. Temperatures below this value will be rejected. **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Maximum Temperature (°C) (`max_temp`) | Float | **From definition:** Maximum allowed temperature in degrees Celsius. Temperatures above this value will be rejected. **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_temp` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Container Management (`container_management_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Container Management (`container_management_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Container Management (`enable_container_management`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Auto Create Container (`auto_create_container`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Strict Container Validation (ISO 6346) (`strict_container_validation`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Container Penalty Alerts (`enable_container_penalty_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Container deposits and GL (`container_deposit_section`) | Section Break | **From definition:** Pending carrier payments and pending carrier refunds are posted via Journal Entry through Debtors (AR) with a Customer party, offsetting the clearing account (see user documentation). **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Deposit cash pattern (`container_deposit_pattern`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Customer Funded, Forwarder Funded. |
| Require Job Number on deposit lines (`require_job_number_on_container_deposits`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_cd1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default company for deposit JE (`container_deposit_default_company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Deposit clearing account (`container_deposit_clearing_account`) | Link | **From definition:** Balance sheet offset account paired with Debtors on container deposit JEs. **Purpose:** Creates a controlled reference to **Account** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Account**. Create the master first if it does not exist. |
| Customer deposit liability account (`container_deposit_customer_liability_account`) | Link | **Purpose:** Creates a controlled reference to **Account** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Account**. Create the master first if it does not exist. |
| Deposit forfeiture expense account (`container_deposit_forfeiture_account`) | Link | **Purpose:** Creates a controlled reference to **Account** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Account**. Create the master first if it does not exist. |
| Debtors override (optional) (`container_deposit_debtors_account`) | Link | **From definition:** If empty, Company default receivable account is used for AR lines. **Purpose:** Creates a controlled reference to **Account** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Account**. Create the master first if it does not exist. |
| Roles allowed to waive refund documents (`container_deposit_refund_waiver_roles`) | Small Text | **From definition:** Comma-separated Role names. Users with any of these roles may set checklist rows to Waived with a reason. **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Refund document requirements (template) (`container_refund_requirements`) | Table | **Purpose:** Stores repeating **Logistics Settings Container Refund Requirement** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Measurements (`measurements_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Measurements (`measurements_section`) | Section Break | **From definition:** Base UOMs are used for conversion and reporting. Default UOMs are used when creating new lines. **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Base Dimension UOM (`base_dimension_uom`) | Link | **From definition:** Pivot UOM for length/width/height (e.g. CM). **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Base Volume UOM (`base_volume_uom`) | Link | **From definition:** Pivot UOM for volume (e.g. CBM). **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Base Weight UOM (`base_weight_uom`) | Link | **From definition:** Pivot UOM for weight and chargeable weight (e.g. KG). **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| `column_break_measurements` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Dimension UOM (`default_dimension_uom`) | Link | **From definition:** Default for dimension_uom on new lines. **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Volume UOM (`default_volume_uom`) | Link | **From definition:** Default for volume_uom on new lines. **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Weight UOM (`default_weight_uom`) | Link | **From definition:** Default for weight_uom on new lines. **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Chargeable Weight UOM (`default_chargeable_weight_uom`) | Link | **From definition:** Default for chargeable_weight_uom on new lines. **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Alerts and Delays Notification (`alerts_and_delays_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Auto Status Updates (`status_updates_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Auto Status Updates (`enable_auto_status_updates`) | Check | **From definition:** When enabled, scheduled tasks will update milestone (Delayed), document (Overdue/Expired), permit, and exemption statuses automatically. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Documents (`documents_section`) | Section Break | **From definition:** Alert levels: Critical = required date or expiry date past. Warning and Information = days before required date or expiry date. **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Warning (Days) (`document_expiring_soon_days`) | Int | **From definition:** Documents required or expiring within this many days show as Warning (yellow). **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Information (Days) (`document_informational_days`) | Int | **From definition:** Documents required or expiring within this many days (beyond Warning window) show as Information (blue). Must be greater than Warning (Days) for Information alerts to appear. **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Milestones (`milestones_section`) | Section Break | **From definition:** Alert levels: Critical = delayed (past planned end). Warning and Information = days before planned end. **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Warning (Days) (`milestone_impending_days`) | Int | **From definition:** Milestones due within this many days show as Warning (yellow). **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Information (Days) (`milestone_informational_days`) | Int | **From definition:** Milestones due within this many days show as Information (blue). Must be greater than Warning (Days) for Information alerts to appear. **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Strict Milestone Schedule Validation (`strict_milestone_schedule_validation`) | Check | **From definition:** When enabled, Actual End cannot be earlier than Planned Start. Disable only if early completion before planned start is part of your process. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Penalties (`penalties_section`) | Section Break | **From definition:** Alert levels: Critical = free time exceeded. Warning = days before free time expires. **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Warning (Days) (`penalty_impending_days`) | Int | **From definition:** Days before free time expires to show Warning (yellow). **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Delays (`delays_section`) | Section Break | **From definition:** Alert levels: Critical = delayed. Warning = days before expected delay. **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Warning (Days) (`delay_impending_days`) | Int | **From definition:** Days before expected delay to show Warning (yellow). **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Credit Control (`credit_control_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Enable logistics credit control (`enable_credit_control`) | Check | **From definition:** When enabled, documents for customers on credit hold are controlled after hold conditions: either **Apply hold to all DocTypes** (full defaults for every registered DocType) or per-row **Subject DocTypes** below. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Hold conditions (`credit_control_intro`) | Section Break | **From definition:** A customer is under credit hold when any enabled condition is true: manual status (Customer > Credit tab), credit limit exceeded, or overdue sales invoices (payment terms deviation). **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Hold when Credit Status is On Hold (`credit_block_on_status_on_hold`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Hold when Credit Status is Watch (`credit_block_on_status_watch`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Hold when credit limit is exceeded (`credit_apply_limit_breach`) | Check | **From definition:** Uses ERPNext customer / group / company credit limit vs outstanding (same basis as Selling). **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Hold on payment terms deviation (`credit_apply_payment_terms_breach`) | Check | **From definition:** Hold when any submitted Sales Invoice for the customer and company has outstanding amount and due date before today minus grace days. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Payment terms grace (days) (`credit_payment_terms_grace_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Bypass role (`credit_control_bypass_role`) | Link | **From definition:** Users with this role skip credit blocks (optional). **Purpose:** Creates a controlled reference to **Role** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Role**. Create the master first if it does not exist. |
| Apply hold to all DocTypes (`credit_apply_hold_to_all_doctypes`) | Check | **From definition:** When enabled, every registered logistics DocType in credit control uses Warn on save and Hold create, submit, and print. The Subject DocTypes table is disabled and ignored. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| DocTypes subject to credit hold (`credit_subject_doctypes_section`) | Section Break | **From definition:** When **Apply hold to all DocTypes** is off, add one row per DocType and set Warn / Hold columns. When it is on, the table is disabled; all registered DocTypes in code are subject to full hold behaviour. **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Subject DocTypes (`credit_control_rules`) | Table | **From definition:** Ignored when **Apply hold to all DocTypes** is checked. Otherwise one row per DocType (must also be registered in code). **Purpose:** Stores repeating **Logistics Settings Credit Rule** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |

#### Child table: Logistics Settings Transport Order Leg (field `allowed_transport_order_legs` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Direction (`direction`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Domestic. |
| Leg Type (`leg_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Pre-carriage, On-forwarding, Main, Other. |

#### Child table: Logistics Settings Container Refund Requirement (field `container_refund_requirements` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Requirement Name (`requirement_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Mandatory for refund (`mandatory_for_refund`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Applies to (`applies_to`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: All, Import, Export. |
| Shipping Line (`shipping_line`) | Link | **Purpose:** Creates a controlled reference to **Shipping Line** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipping Line**. Create the master first if it does not exist. |
| `column_break_crr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Attachment required (`attachment_required`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Instructions (`instructions`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

#### Child table: Logistics Settings Credit Rule (field `credit_control_rules` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Subject DocType (`controlled_doctype`) | Link | **From definition:** DocType evaluated when the resolved customer is on credit hold. **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |
| Warn on save (`block_save`) | Check | **From definition:** After save: orange warning only; save is not blocked. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Hold create (`block_insert`) | Check | **From definition:** Block creating new documents for a customer on hold. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Hold submit (`block_submit`) | Check | **From definition:** Block submit while on hold. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Hold print / PDF (`block_print`) | Check | **From definition:** Block print and PDF while on hold. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Credit Management](welcome/credit-management)
- [Sea Freight Settings](welcome/sea-freight-settings)
- [Air Freight Settings](welcome/air-freight-settings)
- [Transport Settings](welcome/transport-settings)
- [Warehouse Settings](welcome/warehouse-settings)
- [Customer Portal](welcome/customer-portal)
