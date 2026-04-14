# Sales Quote

**Sales Quote** is a multi-product pricing document that can include Sea Freight, Air Freight, Transport, Warehousing, and Customs services. It serves as the commercial offer to the customer and can flow into Bookings, Orders, and Jobs.

A Sales Quote records pricing for one or more services per leg, with weight breaks, quantity breaks, routing, and charges. It supports three **Quotation Types**: **Regular** (reusable across multiple jobs/orders), **One-off** (single-use only), and **Project** (project-scoped with resources and products). It integrates with ERPNext Sales Order and can create Air Booking, Sea Booking, Transport Order, Declaration Order, Inbound Order, or Release Order.

To access Sales Quote, go to:

**Home > Pricing Center > Sales Quote**

## 1. Prerequisites

Before creating a Sales Quote, it is advised to set up the following:

- Customer (from ERPNext)
- Port/Airport masters (for freight)
- [Transport Settings](welcome/transport-settings) and [Transport Template](welcome/transport-template) (for transport)
- Warehouse (for warehousing)

## 2. How to Create a Sales Quote

1. Go to the Sales Quote list, click **New**.
2. Enter **Quote Date** and select **Customer**.
3. Add **Routing Legs** (Sea, Air, Transport, Customs, Warehouse) as needed.
4. Add **Weight Breaks** for freight pricing.
5. Add **Charges** per service.
6. **Save** the document.

### 2.1 Quotation Type

- **Regular** – Reusable across multiple jobs, orders, and bookings. Child tables hold full charge parameters.
- **One-off** – Single-use only; once converted, cannot be linked to another order. Header-level default parameters; child params disabled.
- **Project** – Project-scoped; links to Special Project. Supports Projects Tab with resources and products.

### 2.2 Statuses

- **Draft** – Quote is being prepared
- **Submitted** – Quote is sent to customer
- **Lost** – Quote was not accepted
- **Ordered** – Quote was converted to order (Regular)
- **Converted** – One-off quote has been converted (One-off only)

## 3. Features

### 3.1 Creating Documents from Sales Quote

From a submitted Sales Quote, you can create:
- Air Booking, Sea Booking
- Transport Order
- Declaration Order
- Inbound Order, Release Order

**Separate Billings per Service Type** (Routing tab): When **checked**, each Booking/Order gets only charges for its service type. When **unchecked**, all charges go to the main service; legs with no charges for their service are created as **Internal Jobs** linked to the Main Job (revenue = cost of main job, cost as per tariff). See [Sales Quote – Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job).

### 3.2 Change Request

For additional charges on existing jobs (Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration), use **Create Change Request** from the job form. The Change Request captures new charge lines; when approved, charges are applied to the job. You can also create a Sales Quote from a Change Request for billing.

### 3.3 Integration with ERPNext

Sales Quote can be linked to ERPNext Sales Order. When the order is confirmed, you can create the corresponding logistics documents.

## 4. Calculation Methods

Each charge line (Air Freight, Sea Freight, Transport) uses a **Calculation Method** to compute revenue and cost. Revenue uses **Calculation Method**; cost uses **Cost Calculation Method**, with the same options and formulas. The same unified calculation engine is used across Air Booking, Sea Booking, Transport Order, Transport Job, Air Shipment, Sea Shipment, Declaration, and Declaration Order charges. On Bookings and Orders, charges store **Estimated Revenue** and **Estimated Cost**; on Shipments and Jobs, **Actual Revenue** and **Actual Cost** are also calculated and used for invoicing when present (see [Job Management Module](welcome/job-management-module)).

### 4.1 Formula Summary

| Method | Formula |
|--------|---------|
| Per Unit | `unit_rate × quantity` (with min/max) |
| Fixed Amount | `unit_rate` |
| Flat Rate | `unit_rate` |
| Base Plus Additional | `base_amount + (unit_rate × max(0, quantity - base_qty))` |
| First Plus Additional | `minimum_unit_rate × qty` if qty ≤ min; else `(minimum_unit_rate × min_qty) + (unit_rate × (qty - min_qty))` |
| Percentage | `(unit_rate / 100) × base_amount` |
| Weight Break | `weight × unit_rate` (tier from weight break table) |
| Qty Break | `quantity × unit_rate` (tier from qty break table) |
| Location-based | Same as Per Unit |

### 4.2 Unit Types

**Unit Type** defines what “quantity” means: Weight, Volume, Distance, Package, Piece, Job, Trip, TEU, or Operation Time.

For full details, required fields, and examples, see [Sales Quote – Calculation Method Guide](welcome/sales-quote-calculation-method).


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Sales Quote** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Quote Details (`section_break_aall`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Quotation Type (`quotation_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Regular, One-off, Project. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: SQU.#########, OOQ.#####, PQ.#####. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_rpzo` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Main Service (`main_service`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Air, Sea, Transport, Customs, Warehousing. |
| Separate Billings per Service Type (`separate_billings_per_service_type`) | Check | **From definition:** When unchecked, all charges go to the main service Booking/Order. When checked, each Booking/Order gets only charges for its service type. Legs with no charges for their service become Internal Jobs linked to the Main Job. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Status (`status_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `column_break_ralf` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Draft, Converted. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_azte` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Converted To (`converted_to_doc`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `section_break_duom` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Sales Quote** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Quote**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Consignee (`consignee`) | Link | **Purpose:** Creates a controlled reference to **Consignee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Consignee**. Create the master first if it does not exist. |
| Shipper (`shipper`) | Link | **Purpose:** Creates a controlled reference to **Shipper** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipper**. Create the master first if it does not exist. |
| `column_break_abll` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Date (`date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Valid Until (`valid_until`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Incoterm (`incoterm`) | Link | **Purpose:** Creates a controlled reference to **Incoterm** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Incoterm**. Create the master first if it does not exist. |
| Parameters (`one_off_params_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Origin Port (`origin_port`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Destination Port (`destination_port`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Load Type (`load_type`) | Link | **Purpose:** Creates a controlled reference to **Load Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Load Type**. Create the master first if it does not exist. |
| Transport Mode (`transport_mode`) | Link | **Purpose:** Creates a controlled reference to **Transport Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Mode**. Create the master first if it does not exist. |
| Direction (`direction`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Domestic. |
| `column_break_params` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Airline (`airline`) | Link | **Purpose:** Creates a controlled reference to **Airline** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Airline**. Create the master first if it does not exist. |
| Freight Agent (`freight_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Shipping Line (`shipping_line`) | Link | **Purpose:** Creates a controlled reference to **Shipping Line** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipping Line**. Create the master first if it does not exist. |
| Freight Agent (`freight_agent_sea`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Location Type (`location_type`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |
| Location From (`location_from`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **location_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Location To (`location_to`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **location_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Transport Template (`transport_template`) | Link | **Purpose:** Creates a controlled reference to **Transport Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Template**. Create the master first if it does not exist. |
| Vehicle Type (`vehicle_type`) | Link | **Purpose:** Creates a controlled reference to **Vehicle Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Vehicle Type**. Create the master first if it does not exist. |
| Container Type (`container_type`) | Link | **Purpose:** Creates a controlled reference to **Container Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Container Type**. Create the master first if it does not exist. |
| Routing (`routing_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Multimodal Routing Details (`routing_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Billing Mode (`billing_mode`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Consolidated, Per Product. **Behaviour:** Hidden in default layout; may still be set by import, API, or script. |
| Routing Legs (`routing_legs`) | Table | **Purpose:** Stores repeating **Sales Quote Routing Leg** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Charges (`charges_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Quote Charges (`charges_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Charges (`charges`) | Table | **Purpose:** Stores repeating **Sales Quote Charge** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| `section_break_oiqx` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `warehousing` | Table | **Purpose:** Stores repeating **Sales Quote Warehouse** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| `section_break_bpor` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Additional Charge (`additional_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Job Type (`job_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration. |
| Job (`job`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **job_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Projects (`projects_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Project Details (`projects_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Special Project (`special_project`) | Link | **Purpose:** Creates a controlled reference to **Special Project** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Special Project**. Create the master first if it does not exist. |
| Resources (`project_resources`) | Table | **Purpose:** Stores repeating **Sales Quote Resource** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Products (`project_products`) | Table | **Purpose:** Stores repeating **Sales Quote Product** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Accounts (`accounts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Sales Rep (`sales_rep`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| Operations Rep (`operations_rep`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| Customer Service Rep (`customer_service_rep`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| `column_break_jabf` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| More Info (`additional_information_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Terms and Conditions (`terms_and_conditions_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Terms (`tc_name`) | Link | **Purpose:** Creates a controlled reference to **Terms and Conditions** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Terms and Conditions**. Create the master first if it does not exist. |
| Terms and Conditions Details (`terms`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. **Behaviour:** Auto-filled from `tc_name.terms` when the link/source changes — verify after edits. |
| Service Level Agreement (`service_level_agreement_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Service Code (`service_code`) | Link | **Purpose:** Creates a controlled reference to **Logistics Service Level** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Service Level**. Create the master first if it does not exist. |
| Service Level Details (`service_level_details`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. **Behaviour:** Auto-filled from `service_code.text_uufb` when the link/source changes — verify after edits. |
| Connections (`connections_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |

#### Child table: Sales Quote Routing Leg (field `routing_legs` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Mode (`mode`) | Link | **Purpose:** Creates a controlled reference to **Transport Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Mode**. Create the master first if it does not exist. |
| Type (`type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Main, Pre-carriage, On-forwarding, Other. |
| Main Job (`is_main_job`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Confirmed, Planned, On-hold. |
| `column_break_leg` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Origin (`origin`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Destination (`destination`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| ETD (`etd`) | Date | **Purpose:** Planned departure date for planning, cut-offs, and customer communication. **What to enter:** Pick the expected departure date (local or agreed time zone). |
| ETA (`eta`) | Date | **Purpose:** Planned arrival for routing and consignee readiness. **What to enter:** Expected arrival date at destination. |
| `column_break_job` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Job Type (`job_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Transport Job, Air Shipment, Sea Shipment, Air Booking, Sea Booking, Transport Order. |
| Job No (`job_no`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **job_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Notes (`notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

#### Child table: Sales Quote Charge (field `charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Service Type (`service_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Air, Sea, Transport, Customs, Warehousing. |
| Charge Group (`charge_group`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Origin, Destination, Freight, Customs, Documentation, Storage, Insurance, Other. |
| Item Code (`item_code`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_code.item_name` when the link/source changes — verify after edits. |
| Charge Type (`charge_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Revenue, Cost, Margin, Disbursement, Other. |
| Charge Category (`charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Freight, Fuel Surcharge, Terminal Handling, Port Charges, Customs Clearance, Documentation, Insurance, Storage, Detention, Demurrage, Other. |
| `column_break_core` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Tariff (`tariff`) | Link | **Purpose:** Creates a controlled reference to **Tariff** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Tariff**. Create the master first if it does not exist. |
| Revenue Tariff (`revenue_tariff`) | Link | **Purpose:** Creates a controlled reference to **Tariff** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Tariff**. Create the master first if it does not exist. |
| Cost Tariff (`cost_tariff`) | Link | **Purpose:** Creates a controlled reference to **Tariff** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Tariff**. Create the master first if it does not exist. |
| Use Tariff in Revenue (`use_tariff_in_revenue`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Use Tariff in Cost (`use_tariff_in_cost`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Bill To (`bill_to`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Pay To (`pay_to`) | Link | **Purpose:** Creates a controlled reference to **Supplier** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Supplier**. Create the master first if it does not exist. |
| Quotation Type (`quotation_type`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Hidden in default layout; may still be set by import, API, or script. |
| Air Parameters (`section_break_air_params`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Air House Type (`air_house_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Standard House, Co-load Master, Blind Co-load Master, Co-load House, Buyer's Consol Lead, Shipper's Consol Lead, Break Bulk. |
| Airline (`airline`) | Link | **Purpose:** Creates a controlled reference to **Airline** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Airline**. Create the master first if it does not exist. |
| Freight Agent (`freight_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Sea Parameters (`section_break_sea_params`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Sea House Type (`sea_house_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Standard House, Co-load Master, Blind Co-load Master, Co-load House, Buyer's Consol Lead, Shipper's Consol Lead, Break Bulk. |
| Freight Agent (`freight_agent_sea`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Shipping Line (`shipping_line`) | Link | **Purpose:** Creates a controlled reference to **Shipping Line** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipping Line**. Create the master first if it does not exist. |
| Transport Mode (`transport_mode`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: FCL, LCL. |
| Common Parameters (`section_break_common_params`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Load Type (`load_type`) | Link | **Purpose:** Creates a controlled reference to **Load Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Load Type**. Create the master first if it does not exist. |
| Direction (`direction`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Domestic. |
| Origin Port (`origin_port`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Destination Port (`destination_port`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Transport Parameters (`section_break_transport_params`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Transport Template (`transport_template`) | Link | **Purpose:** Creates a controlled reference to **Transport Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Template**. Create the master first if it does not exist. |
| Vehicle Type (`vehicle_type`) | Link | **Purpose:** Creates a controlled reference to **Vehicle Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Vehicle Type**. Create the master first if it does not exist. |
| Container Type (`container_type`) | Link | **Purpose:** Creates a controlled reference to **Container Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Container Type**. Create the master first if it does not exist. |
| `column_break_transport` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Location Type (`location_type`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |
| Location From (`location_from`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **location_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Location To (`location_to`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **location_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Pick Mode (`pick_mode`) | Link | **Purpose:** Creates a controlled reference to **Pick and Drop Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Pick and Drop Mode**. Create the master first if it does not exist. |
| Drop Mode (`drop_mode`) | Link | **Purpose:** Creates a controlled reference to **Pick and Drop Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Pick and Drop Mode**. Create the master first if it does not exist. |
| Customs Parameters (`section_break_customs_params`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Customs Authority (`customs_authority`) | Link | **Purpose:** Creates a controlled reference to **Customs Authority** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customs Authority**. Create the master first if it does not exist. |
| Declaration Type (`declaration_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Transit, Bonded. |
| Customs Broker (`customs_broker`) | Link | **Purpose:** Creates a controlled reference to **Supplier** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Supplier**. Create the master first if it does not exist. |
| Charge Category (`customs_charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Customs Clearance, Documentation, Storage, Other. |
| Revenue & Cost (`section_break_revenue_cost`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Revenue (`revenue_column`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Calculation Method (`calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Base Plus Additional, First Plus Additional, Percentage. |
| Unit Rate (`unit_rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Unit Type (`unit_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Distance, Weight, Chargeable Weight, Volume, Package, Piece, Container, TEU, Item Count, Operation Time, Job, Trip, Handling Unit. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Quantity (`minimum_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Charge (`minimum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Maximum Charge (`maximum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Base Amount (`base_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Estimated Revenue (`estimated_revenue`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Revenue Calc Notes (`revenue_calc_notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Cost (`cost_column`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Calculation Method (`cost_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Flat Rate, Base Plus Additional, First Plus Additional, Percentage, Location-based. |
| Unit Cost (`unit_cost`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Unit Type (`cost_unit_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Distance, Weight, Chargeable Weight, Volume, Package, Piece, Container, TEU, Item Count, Operation Time, Job, Trip, Handling Unit. |
| Currency (`cost_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Quantity (`cost_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Quantity (`cost_minimum_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Charge (`cost_minimum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Maximum Charge (`cost_maximum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Base Amount (`cost_base_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| UOM (`cost_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Estimated Cost (`estimated_cost`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Cost Calc Notes (`cost_calc_notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Cost Sheet Source (`cost_sheet_source`) | Link | **Purpose:** Creates a controlled reference to **Cost Sheet** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Sheet**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Sales Quote Warehouse (field `warehousing` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item (`item`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `item.item_name` when the link/source changes — verify after edits. |
| Charge Type (`charge_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Margin, Disbursement, Revenue, Cost. |
| Charge Category (`charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Freight, Fuel Surcharge, Terminal Handling, Customs Clearance, Documentation, Insurance, Storage, Handling, Other. |
| Storage Charge (`storage_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.custom_storage_charge` when the link/source changes — verify after edits. |
| Inbound Charge (`inbound_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.custom_inbound_charge` when the link/source changes — verify after edits. |
| Outbound Charge (`outbound_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.custom_outbound_charge` when the link/source changes — verify after edits. |
| VAS Charge (`vas_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.custom_vas_charge` when the link/source changes — verify after edits. |
| Stocktake Charge (`stocktake_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.custom_stocktake_charge` when the link/source changes — verify after edits. |
| `column_break_rbqm` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Handling Unit Type (`handling_unit_type`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit Type**. Create the master first if it does not exist. |
| Storage Type (`storage_type`) | Link | **Purpose:** Creates a controlled reference to **Storage Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Type**. Create the master first if it does not exist. |
| Calculation Method (`calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Base Plus Additional, First Plus Additional, Percentage. |
| Unit Type (`unit_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Handling Unit, Weight, Chargeable Weight, Volume, Package, Piece, Job, TEU, Operation Time. |
| Volume Calculation Method (`volume_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Daily Volume, Peak Volume, Average Volume, End Volume. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| `column_break_gyhp` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Billing Time Unit (`billing_time_unit`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Day, Week, Hour. |
| Billing Time Multiplier (`billing_time_multiplier`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Billing Time (`minimum_billing_time`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Quantity (`minimum_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Charge (`minimum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Maximum Charge (`maximum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Base Amount (`base_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `section_break_btnr` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Currency (`selling_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Unit Rate (`unit_rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `column_break_vkhw` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Currency (`cost_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Unit Cost (`unit_cost`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Auto-filled from `item.custom_standard_unit_cost` when the link/source changes — verify after edits. |

#### Child table: Sales Quote Resource (field `project_resources` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Resource Type (`resource_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Personnel, Equipment, Third Party, Other. |
| Role/Description (`resource_role`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Planned Hours (`planned_hours`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| In House (`in_house`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Supplier (`supplier`) | Link | **Purpose:** Creates a controlled reference to **Supplier** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Supplier**. Create the master first if it does not exist. |
| Cost Per Unit (`cost_per_unit`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Rate Per Unit (`rate_per_unit`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Notes (`notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

#### Child table: Sales Quote Product (field `project_products` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item (`item`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Description (`description`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Rate (`rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Notes (`notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

<!-- wiki-field-reference:end -->

## 5. Related Topics

- [Recent Platform Updates](welcome/recent-platform-updates) – charge copy from quote to bookings/orders, billing, and recognition notes
- [Sales Quote – Calculation Method Guide](welcome/sales-quote-calculation-method) – full formulas, required fields, and examples
- [Sales Quote – Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job) – Separate Billings per Service Type, charge allocation, and Internal Job rules
- [Sea Booking](welcome/sea-booking)
- [Air Booking](welcome/air-booking)
- [Transport Order](welcome/transport-order)
