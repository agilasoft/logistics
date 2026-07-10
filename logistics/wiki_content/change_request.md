# Change Request

**Change Request** is a document used to add additional charges to an existing job (Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration). On **submit**, cost charge rows are applied to the linked job; revenue is filled in when the linked Additional Charge Sales Quote is submitted.

To access Change Request, go to:

**Home > Pricing Center > Change Request**

## 1. How to Use

1. Open a job (e.g., Air Shipment, Transport Job).
2. Click **Create Change Request** (from the Additional Charges or custom button).
3. On the **Services** tab, add only the **new** additional services you need (e.g. an extra transport leg or customs clearance). The tab starts **empty** — existing services on the shipment or job are **not** copied in.
4. Add charge lines in the **Charges** child table (set **Service Type** to match the fee — Air, Sea, Transport, Customs, or Warehousing). Use **Scope = Linked** and pick a service from the Services tab when the charge belongs to a new linked leg.
5. **Submit** the Change Request — cost rows are pushed to the linked job's **Charges** table (tagged with `change_request` and `change_request_charge`). Revenue on those rows starts at zero until a Sales Quote is submitted.
6. Create a **Sales Quote** from the Change Request (button on the submitted Change Request).
7. **Submit** the Additional Charge Sales Quote — revenue is merged onto the existing Change Request charge rows on the job (matched by `change_request_charge`).

Charges do **not** appear on the job until step 5 (Change Request submit). Revenue does **not** appear until step 7 (Sales Quote submit).

### Services tab (new additional services only)

When you create a Change Request from a shipment or job, the **Services** tab is **empty**. CargoNext does **not** copy the job's existing Linked Services into the Change Request.

Use the Services tab like a mini quotation workspace: define only the **new** subsidiary services you are adding (transport leg, customs brokerage, warehousing, and so on). Each row you add creates a Change Request–owned Linked Service. Charges that belong to one of those new legs should use **Scope = Linked** and reference the matching service row.

Charges for fees on the **main** job itself (no new subsidiary leg) can stay on **Scope = Main** without adding a Services row.

### Multimodal jobs (Air Shipment / Sea Shipment)

Air Shipment and Sea Shipment support multiple service types on one job (e.g. Air freight, Customs brokerage, Transport delivery, Warehousing storage). Change Request charge rows may use any supported **Service Type**; all rows are applied to the main job's Charges table regardless of whether the service type is Air/Sea or another mode.

### Verified reference: ASP-000000238 (GitHub issue #997)

[Issue #997](https://github.com/agilasoft/logistics/issues/997) reported that additional charges from a Change Request were not appearing on Air Shipment **ASP-000000238** (DEMO CARGO, high-value). Verified on **logistics.agilasoft.com**, 2026-06-23.

#### Linked documents

| Document | Value |
| --- | --- |
| Air Shipment | ASP-000000238 — high-value, customer **ElectroWorld PH**, original Sales Quote SQU000000997 |
| Change Request | CR-000000182 — submitted 2026-06-02 15:56, status **Sales Quote Created** |
| Additional Charge Sales Quote | OOQ00319 — submitted 2026-06-02 16:01 |
| Charge added via Change Request | **AMBRACK** — Service Type **Warehousing**, qty 335, cost 78,390, revenue 197,650 |

#### ASP-000000238 Charges table (as verified)

| # | Item | Service Type | Source | Change Request | Sales Quote | Est. Revenue | Est. Cost |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| 1 | FREIGHT | Air | Original quote | — | SQU000000997 | 165,000 | 75,000 |
| 2 | BROKERAGE FEE | Customs | Original quote | — | SQU000000997 | 10,000 | 5,000 |
| 3 | DELIVERY | Transport | Original quote | — | SQU000000997 | 180,000 | 75,000 |
| 4 | AMBRACK | Warehousing | Change Request | CR-000000182 | OOQ00319 | 197,650 | 78,390 |

Row 4 is tagged with `change_request_charge = 2mipjiaefb`, matching the sole Change Request charge row. `change_request_cost_rows_missing_on_main_job` returns **false** (no missing rows).

#### Verification result

**Cannot reproduce — working as designed.** All Change Request charge rows are present on the job with cost and revenue populated. The reported behaviour is most consistent with the two-step workflow not yet completed when the issue was filed:

| Step | When (site time) | What the user sees |
| --- | --- | --- |
| Issue #997 opened | 2026-06-02 ~15:56 | Charges not yet on job |
| Change Request submitted | 2026-06-02 15:56 | Cost row appears; revenue still 0 |
| Sales Quote OOQ00319 submitted | 2026-06-02 16:01 | Revenue merged onto existing row |

Charges do **not** appear until the Change Request is **submitted**. Revenue stays at zero until the Additional Charge Sales Quote is **submitted**. Reload the Air Shipment form after each submit.

#### If charges still appear missing

1. Confirm the Change Request is **submitted** (docstatus = 1), not Draft.
2. Confirm a Sales Quote was **created from** the Change Request and **submitted** if revenue is expected.
3. Reload the Air Shipment form (or hard-refresh) after submit.
4. For multimodal jobs, set **Service Type** on each Change Request charge row to match the fee (e.g. Warehousing for storage fees on an Air Shipment) — non-Air service types are supported on Air Shipment.

## 2. Supported Job Types

- Air Shipment
- Sea Shipment (via Sea Shipment Charges)
- Transport Job
- Warehouse Job
- Declaration


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Change Request** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: CR-.#########. |
| Job Type (`job_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration. |
| Job (`job`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **job_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| `column_break_cr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Draft, Submitted, Approved, Sales Quote Created. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Costs (`section_break_charges`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Charges (`charges`) | Table | **Purpose:** Stores repeating **Change Request Charge** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Remarks (`section_break_remarks`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Remarks (`remarks`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Sales Quote (`sales_quote`) | Link | **Purpose:** Creates a controlled reference to **Sales Quote** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Quote**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Change Request** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Change Request**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Change Request Charge (field `charges` on parent)

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
| Transport Mode (`transport_mode`) | Link | **Purpose:** Creates a controlled reference to **Transport Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Mode**. Create the master first if it does not exist. **Behaviour:** Hidden in default layout; may still be set by import, API, or script. |
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
| Customs Broker (`customs_broker`) | Link | **Purpose:** Creates a controlled reference to **Broker** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Broker**. Create the master first if it does not exist. |
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

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Sales Quote](welcome/sales-quote)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- [Declaration](welcome/declaration)
