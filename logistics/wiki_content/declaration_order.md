# Declaration Order

**Declaration Order** is the customs order document that captures the customer's declaration requirements before the actual customs declaration is submitted. It serves as the order layer in the customs workflow: Sales Quote → Declaration Order → Declaration. A Declaration Order records parties, shipment details, commercial invoice data, line items, charges, documents, permits, and exemptions. Once confirmed, it flows into one or more [Declarations](welcome/declaration) for submission to customs authorities.

To access: **Home > Customs > Declaration Order**

## 1. Prerequisites

Before creating a Declaration Order, set up:

- [Customs Settings](welcome/customs-settings) – Default values and compliance settings
- [Customs Authority](welcome/customs-authority) – Target authority for the declaration
- [Declaration Product Code](welcome/declaration-product-code) – Product codes per item, importer, and exporter
- [CI Charge Code](welcome/ci-charge-code) – Charge codes for commercial invoice charges
- [Shipper](welcome/shipper), [Consignee](welcome/consignee) – Exporter and Importer parties
- [Commodity](welcome/commodity) – HS codes and commodity classifications
- [Document List Template](welcome/document-list-template) – Optional template for document checklist

## 2. Main Sections

### 2.1 Header

- **Order Date** – Date of the order
- **Sales Quote** – Link to source quote (if created from quote)
- **Customer** – Customer (required)
- **Customs Authority** – Target customs authority
- **Currency**, **Exchange Rate** – Currency for the declaration
- **Status** – Draft, Submitted, Under Review, Cleared, Released, Rejected, Cancelled
- **Customs Broker**, **Notify Party** – Optional parties

### 2.2 Shipment Details

- **Exporter/Shipper** – Link to [Shipper](welcome/shipper)
- **Importer/Consignee** – Link to [Consignee](welcome/consignee)
- **Declaration Type** – Import, Export, Transit, Bonded
- **Transport Mode** – Sea, Air, Road, Rail, Courier, Post
- **Air Shipment**, **Sea Shipment**, **Transport Order** – Links to freight for traceability

### 2.3 Transport Information

- **Vessel/Flight/Vehicle Number** – Transport identifier
- **Transport Document Number**, **Transport Document Type** – Bill of Lading, Air Waybill, CMR, etc.
- **Port of Loading/Entry**, **Port of Discharge/Exit** – UNLOCO ports
- **ETD**, **ETA** – Expected departure and arrival
- **Container Numbers** – Comma-separated list

### 2.4 Trade Information

- **Incoterm**, **Payment Terms**, **Trade Agreement** – Trade terms
- **Country of Origin**, **Country of Destination** – Country links
- **Priority Level** – Normal, Express, Urgent

### 2.5 Additional Information

- **Marks and Numbers**, **Special Instructions** – Free text
- **External Reference** – Reference from external systems

### 2.6 Service Level Agreement

- **Service Level** – Link to [Logistics Service Level](welcome/logistics-milestone)
- **SLA Target Date**, **SLA Status**, **SLA Target Source**, **SLA Notes** – SLA monitoring

## 3. Commercial Invoice Tab

The Commercial Invoice tab holds invoice header data and line items used for customs declaration.

### 3.1 Invoice Headers

- **Invoice No.**, **Supplier**, **Supplier Name** – Invoice identification
- **Inv. Date**, **Payment Date** – Dates
- **Inv. Importer**, **Agreed Place**, **Incoterm Place**, **Inv. Incoterm** – Invoice terms
- **Inv. Total Amount**, **Inv. Currency**, **Inv. Exchange Rate** – Currency and totals
- **Inv. Volume**, **Inv. Gross Weight**, **Inv. Net Weight**, **Packages** – Quantities
- **CIF**, **FOB**, **Charges Excl. from ITOT** – Financial breakdown
- **Settlement Details** – Bank account, LC, payment details

### 3.2 Line Items

- **Commercial Invoice Line Items** – Table of items for declaration
  - **Declaration Product Code** – Link to [Declaration Product Code](welcome/declaration-product-code) (filtered by Importer/Exporter)
  - **Item**, **Product Code** – Fetched from Declaration Product Code
  - **Procedure Code**, **Tariff**, **Goods Description**, **Commodity Code**, **Goods Origin**, **Preference** – Customs classification
  - **Invoice Qty**, **Customs Qty**, **Price** – Quantities and pricing
  - **Gross Weight**, **Volume**, **Measurements** – Physical details

### 3.3 Invoice Charges

- **Commercial Invoice Charges** – Charge lines (freight, insurance, discounts, etc.)
  - **Charge Code** – Link to [CI Charge Code](welcome/ci-charge-code) (ADD, COM, DED, DIS, EXW, FIF, LCH, OFT, ONS, OTH)
  - **Amount**, **Currency** – Charge value
  - **Incl. in Inv. Lines?**, **Add to FOB?**, **VAT Apply**, **Included in Inv. Amt** – Distribution flags
  - **Distribute By** – Weight, Volume, Quantity, Value

## 4. Documents Tab

- **Document List Template** – Optional template to load document checklist
- **Documents** – Job Document child table; track Commercial Invoice, Packing List, Bill of Lading, Certificates of Origin, etc.
- Use **Populate from Template** to load document requirements based on product type and declaration type.
- Track status, date required, and attachments per document.

## 5. Permits Tab

- **Permit Requirements** – Child table for permit lines (type, authority, dates, status); aligned with the **Permit Requirement** master where used.
- **Exemptions** – Child table for declaration-specific exemptions, carried through to [Declaration](welcome/declaration) when the declaration is created.
- Track permits and exemptions required for the declaration.

## 6. Milestones Tab

- **Milestone Template** – Optional template for milestone structure
- **Milestones** – Declaration Order Milestone child table
- Track key milestones (Submitted, Under Review, Customs Clearance, Released).

## 7. Charges Tab

- **Charges** – Declaration Order Charges child table
- **Populate Charges from Sales Quote** – Load charges from linked Sales Quote
- Supports quantity breaks and weight breaks (unified calculation engine; revenue and cost calculation methods).

## 8. Accounts Tab

- **Company**, **Branch**, **Cost Center**, **Profit Center** – Accounting dimensions
- **Job Number**, **Project** – Optional job tracking

## 9. Status Workflow

| Status | Description |
|--------|-------------|
| Draft | Order is being prepared |
| Submitted | Submitted to customs |
| Under Review | Customs is reviewing |
| Cleared | Approved by customs |
| Released | Cargo released |
| Rejected | Rejected by customs |
| Cancelled | Order cancelled |

## 10. Creating a Declaration

1. Save the Declaration Order.
2. Click **Create Declaration** (or **View Declaration** if one exists).
3. The Declaration inherits all data from the order: parties, commodities, commercial invoice, charges, documents, permits, exemptions.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Declaration Order** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Dashboard (`dashboard_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Dashboard (`dashboard_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Details (`details`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `section_break_main` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: DCO-.#########. |
| Order Date (`order_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Customs Authority (`customs_authority`) | Link | **Purpose:** Creates a controlled reference to **Customs Authority** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customs Authority**. Create the master first if it does not exist. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Exchange Rate (`exchange_rate`) | Float | **From definition:** Exchange rate if different from base currency **Purpose:** Unit rate or ratio used with quantity/UOM in charge calculations. **What to enter:** Decimal per your pricing rules; respect minimums/maximums on the charge line if shown. |
| `column_break_pemj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Customs Broker (`customs_broker`) | Link | **Purpose:** Creates a controlled reference to **Broker** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Broker**. Create the master first if it does not exist. |
| Freight Agent (`freight_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| Notify Party (`notify_party`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Status (`status`) | Select | **From definition:** Draft=preparing, Submitted=to customs, Under Review=customs reviewing, Cleared=approved, Released=cargo released **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Draft, Submitted, Under Review, Cleared, Released, Rejected, Cancelled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Shipment Details (`section_break_shipment_type`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Exporter/Shipper (`exporter_shipper`) | Link | **Purpose:** Creates a controlled reference to **Shipper** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipper**. Create the master first if it does not exist. |
| Importer/Consignee (`importer_consignee`) | Link | **Purpose:** Creates a controlled reference to **Consignee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Consignee**. Create the master first if it does not exist. |
| `column_break_knri` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Declaration Type (`declaration_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Transit, Bonded. |
| Transport Mode (`transport_mode`) | Link | **Purpose:** Creates a controlled reference to **Transport Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Mode**. Create the master first if it does not exist. |
| Transport Information (`section_break_transport`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `column_break_transport` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Vessel/Flight/Vehicle Number (`vessel_flight_number`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Transport Document Number (`transport_document_number`) | Data | **From definition:** Bill of Lading, Air Waybill, CMR, etc. **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Transport Document Type (`transport_document_type`) | Link | **Purpose:** Creates a controlled reference to **Transport Document Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Document Type**. Create the master first if it does not exist. |
| Container Numbers (`container_numbers`) | Small Text | **From definition:** Comma-separated list of container numbers **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| `column_break_hyfv` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Port of Loading/Entry (`port_of_loading`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| ETD (Expected Departure) (`etd`) | Date | **Purpose:** Planned departure date for planning, cut-offs, and customer communication. **What to enter:** Pick the expected departure date (local or agreed time zone). |
| `column_break_erxo` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Port of Discharge/Exit (`port_of_discharge`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| ETA (Expected Arrival) (`eta`) | Date | **Purpose:** Planned arrival for routing and consignee readiness. **What to enter:** Expected arrival date at destination. |
| Trade Information (`section_break_trade`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Incoterm (`incoterm`) | Link | **Purpose:** Creates a controlled reference to **Incoterm** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Incoterm**. Create the master first if it does not exist. |
| Payment Terms (`payment_terms`) | Link | **Purpose:** Creates a controlled reference to **Payment Terms Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Payment Terms Template**. Create the master first if it does not exist. |
| Trade Agreement/Preference (`trade_agreement`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Special Instructions (`special_instructions`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| `column_break_trade` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Country of Origin (`country_of_origin`) | Link | **Purpose:** Creates a controlled reference to **Country** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Country**. Create the master first if it does not exist. |
| Country of Destination (`country_of_destination`) | Link | **Purpose:** Creates a controlled reference to **Country** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Country**. Create the master first if it does not exist. |
| Priority Level (`priority_level`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Normal, Express, Urgent. |
| Marks and Numbers (`marks_and_numbers`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| External Reference Number (`external_reference`) | Data | **From definition:** Reference from external systems or customs authority **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Commercial Invoice (`commercial_invoice_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `section_break_commercial_invoice_headers` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `column_break_otwm` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Invoice No. (`invoice_no`) | Data | **Purpose:** Carrier, customs, or commercial reference printed on transport or customs documents. **What to enter:** The exact identifier from the MAWB/HAWB, B/L, container interchange, or tax invoice. |
| Exporter (`exporter`) | Link | **Purpose:** Creates a controlled reference to **Shipper** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipper**. Create the master first if it does not exist. |
| Exporter Name (`exporter_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `exporter.shipper_name` when the link/source changes — verify after edits. |
| Inv. Date (`inv_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Payment Date (`payment_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| `column_break_quah` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Importer (`inv_importer`) | Link | **Purpose:** Creates a controlled reference to **Consignee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Consignee**. Create the master first if it does not exist. |
| Importer Name (`importer_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `inv_importer.consignee_name` when the link/source changes — verify after edits. |
| Agreed Place (`agreed_place`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Incoterm Place (`incoterm_place`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Incoterm (`inv_incoterm`) | Link | **Purpose:** Creates a controlled reference to **Incoterm** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Incoterm**. Create the master first if it does not exist. |
| `column_break_zsjh` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Currency (`inv_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Invoice Total (`inv_total_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **inv_currency** on this form (or company default). |
| Exchange Rate (`inv_exchange_rate`) | Float | **Purpose:** Unit rate or ratio used with quantity/UOM in charge calculations. **What to enter:** Decimal per your pricing rules; respect minimums/maximums on the charge line if shown. |
| Balance (`balance`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Invoice Details (`invoice_details_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `column_break_inv_headers` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Volume (`inv_volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Volume UOM (`inv_volume_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Inv. Gross Weight (`inv_gross_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Inv. Gross Weight UOM (`inv_gross_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Inv. Net Weight (`inv_net_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Inv. Net Weight UOM (`inv_net_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Packages (`packages`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Packages UOM (`packages_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| `column_break_inv_financial` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| CIF (`cif`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| FOB (`fob`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Charges excl. from ITOT (`charges_excl_from_itot`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Expected Invoice Line Total (`expected_invoice_line_total`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `column_break_fevp` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Remarks (`remarks`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Settlement Details (`settlement_details_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `column_break_inv_bank` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Exporters Bank Account No (`exporters_bank_account_no`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Exporters Bank Name (`exporters_bank_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Exporters Bank SWIFT Code (`exporters_bank_swift_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| `column_break_inv_lc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Letter of Credit Number (`letter_of_credit_number`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Letter of Credit Date (`letter_of_credit_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| LC Ex Rate (`lc_ex_rate`) | Float | **Purpose:** Unit rate or ratio used with quantity/UOM in charge calculations. **What to enter:** Decimal per your pricing rules; respect minimums/maximums on the charge line if shown. |
| `column_break_lirr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Payment # (`payment_number`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Currency (`payment_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Payment Amount (`payment_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **payment_currency** on this form (or company default). |
| Payment Ex Rate (`payment_ex_rate`) | Float | **Purpose:** Unit rate or ratio used with quantity/UOM in charge calculations. **What to enter:** Decimal per your pricing rules; respect minimums/maximums on the charge line if shown. |
| Invoice Charges (`section_break_invoice_charges`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Invoice Charges (`commercial_invoice_charges`) | Table | **Purpose:** Stores repeating **Commercial Invoice Charges** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Line Items (`section_break_line_items`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Line Items (`commercial_invoice_line_items`) | Table | **Purpose:** Stores repeating **Commercial Invoice Line Item** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Documents (`documents_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Document Checklist (`documents_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Document Summary (`documents_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Document Template (`document_list_template`) | Link | **From definition:** Override default template. Leave empty to use product default. **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Documents (`documents`) | Table | **Purpose:** Stores repeating **Job Document** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Permits and Exemptions (`permits_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Permit Requirements (`permits_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Permit Requirements (`permit_requirements`) | Table | **Purpose:** Stores repeating **Declaration Order Permit Requirement** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Exemptions (`exemptions_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Exemptions (`exemptions`) | Table | **Purpose:** Stores repeating **Declaration Order Exemption** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Milestones (`milestones_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Milestones (`section_break_milestones`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Milestone View (`milestone_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Milestone Template (`milestone_template`) | Link | **From definition:** Optional. Leave blank to use default template for this product type. **Purpose:** Creates a controlled reference to **Milestone Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Milestone Template**. Create the master first if it does not exist. |
| Milestones (`milestones`) | Table | **Purpose:** Stores repeating **Declaration Order Milestone** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Charges (`charges_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `column_break_logistics_reps` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| `column_break_accounts` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Project (`project`) | Link | **From definition:** ERPNext Project for Special Projects integration **Purpose:** Creates a controlled reference to **Project** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Project**. Create the master first if it does not exist. |
| Job Number (`job_number`) | Link | **From definition:** For revenue/cost recognition **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. |
| `column_break_yhuu` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Sales Rep (`sales_rep`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| Operations Rep (`operations_rep`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| Customer Service Rep (`customer_service_rep`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| Charges (`charges_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `column_break_qkdg` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Charges (`charges`) | Table | **From definition:** New charges must be added via Create Change Request. You can still adjust Estimated Revenue and Estimated Cost on existing lines. **Purpose:** Stores repeating **Declaration Order Charges** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Job Details (`quote_reference`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Main Service (`is_main_service`) | Check | **From definition:** Primary operational job for this Sales Quote leg: when Separate Billings per Service Type is off, quote charges from all service types can roll into this document. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Sales Quote (`sales_quote`) | Link | **Purpose:** Creates a controlled reference to **Sales Quote** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Quote**. Create the master first if it does not exist. |
| `column_break_quote_ref` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Internal Job (`is_internal_job`) | Check | **From definition:** Set when created from Sales Quote for a leg with no charges for this service; revenue = cost of Main Job, cost as per tariff. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Main Job Type (`main_job_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Air Shipment, Sea Shipment, Transport Job, Declaration. |
| Main Job (`main_job`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **main_job_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Internal Jobs (`internal_job_details_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Internal Jobs (`internal_job_details`) | Table | **Purpose:** Stores repeating **Internal Job Detail** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| More Info (`more_info_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Notes (`notes_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Internal Notes (`internal_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| `column_break_parties` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| External Notes (`external_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Declaration Order** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Declaration Order**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Service Level Agreement (`section_break_sla`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Service Level (`service_level`) | Link | **Purpose:** Creates a controlled reference to **Logistics Service Level** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Service Level**. Create the master first if it does not exist. |
| `column_break_xsrb` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| SLA Target Date (`sla_target_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| SLA Status (`sla_status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: On Track, At Risk, Breached, Not Applicable. |
| SLA Target Source (`sla_target_source`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: From Service Level, Manual. |
| `column_break_sla` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| SLA Notes (`sla_notes`) | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |
| Connections (`connections_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |

#### Child table: Commercial Invoice Charges (field `commercial_invoice_charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Code (`charge_code`) | Link | **Purpose:** Creates a controlled reference to **CI Charge Code** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **CI Charge Code**. Create the master first if it does not exist. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Amount (`amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Incl. in Inv.Lines? (`incl_in_inv_lines`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Add to FOB? (`add_to_fob`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| VAT Apply (`vat_apply`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Included in Inv. Amt (`included_in_inv_amt`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Distribute By (`distribute_by`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: WGT: Weight, VOL: Volume, QTY: Quantity, VAL: Value. |

#### Child table: Commercial Invoice Line Item (field `commercial_invoice_line_items` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Declaration Product Code (`declaration_product_code`) | Link | **From definition:** Select from Declaration Product Code (filtered by importer/exporter) **Purpose:** Creates a controlled reference to **Declaration Product Code** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Declaration Product Code**. Create the master first if it does not exist. |
| Item (`item`) | Link | **From definition:** Fetched from Declaration Product Code **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Product Code (`product_code`) | Data | **From definition:** Fetched from Declaration Product Code **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Procedure Code (`procedure_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Tariff (`tariff`) | Link | **Purpose:** Creates a controlled reference to **Customs Tariff Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customs Tariff Number**. Create the master first if it does not exist. |
| Goods Description (`goods_description`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Goods Origin (`goods_origin`) | Link | **Purpose:** Creates a controlled reference to **Country** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Country**. Create the master first if it does not exist. |
| Preference (`preference`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Commodity Code (`commodity_code`) | Link | **Purpose:** Creates a controlled reference to **Commodity** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Commodity**. Create the master first if it does not exist. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Invoice Qty (`invoice_qty`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Invoice Qty UOM (`invoice_qty_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Customs Qty (`customs_qty`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Customs Qty UOM (`customs_qty_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Additional Qty 1 (`additional_qty_1`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Additional Qty 1 UOM (`additional_qty_1_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Additional Qty 2 (`additional_qty_2`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Additional Qty 2 UOM (`additional_qty_2_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Additional Qty 3 (`additional_qty_3`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Additional Qty 3 UOM (`additional_qty_3_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Price (`price`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **inv_currency** on this form (or company default). |
| Tax Type Code (`tax_type_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Gross Weight (`gross_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Gross Weight UOM (`gross_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Volume (`volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Volume UOM (`volume_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Measurements (`measurements_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| No of Packs (`no_of_packs`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Package Type (`package_type`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Dimension UOM (`dimension_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Length (`length`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Width (`width`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Height (`height`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Chargeable Weight (`chargeable_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Chargeable Weight UOM (`chargeable_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Reference No (`reference_no`) | Data | **Purpose:** Carrier, customs, or commercial reference printed on transport or customs documents. **What to enter:** The exact identifier from the MAWB/HAWB, B/L, container interchange, or tax invoice. |

#### Child table: Job Document (field `documents` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Document Type (`document_type`) | Link | **Purpose:** Creates a controlled reference to **Logistics Document Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Document Type**. Create the master first if it does not exist. |
| Document Name (`document_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `document_type.document_name` when the link/source changes — verify after edits. |
| Document Number (`document_number`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Pending, Uploaded, Done, Received, Verified, Overdue, Expired, Rejected. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Date Required (`date_required`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Date Received (`date_received`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Date Verified (`date_verified`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Expiry Date (`expiry_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Attachment (`attachment_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Attachment (`attachment`) | Attach | **Purpose:** Stores evidence: B/L, AWB, permits, POD scans, certificates. **What to enter:** Upload PDF/image from disk or drag-and-drop; use clear filenames; respect max size limits. |
| `column_break_attachment` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Required (`is_required`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Verified (`is_verified`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Verified By (`verified_by`) | Link | **Purpose:** Creates a controlled reference to **User** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **User**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Issued By (`issued_by`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Overdue Days (`overdue_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Notes (`notes_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Notes (`notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| `column_break_meta` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Source (`source`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Manual, Fetched. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Created At (`created_at`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Declaration Order Permit Requirement (field `permit_requirements` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Permit Application (`permit_application`) | Link | **Purpose:** Creates a controlled reference to **Permit Application** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Permit Application**. Create the master first if it does not exist. |
| Permit Type (`planned_permit_type`) | Link | **From definition:** Set before a Permit Application is linked. Copied to Declaration. Default for Create > Permit Application. **Purpose:** Creates a controlled reference to **Permit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Permit Type**. Create the master first if it does not exist. |
| Permit Type (`permit_type`) | Data | **From definition:** From linked Permit Application (code). Virtual: evaluated if controller property is absent. **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Application Status (`status`) | Data | **From definition:** Workflow status from linked Permit Application. **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Is Required (`is_required`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Is Obtained (`is_obtained`) | Check | **From definition:** Derived from Permit Application status (Approved / Renewed). **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Required Date (`required_date`) | Date | **From definition:** Target date the permit is required (planning). Copied to Declaration. **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| `column_break_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Obtained Date (`obtained_date`) | Date | **From definition:** From Permit Application approval date. **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Expiry Date (`expiry_date`) | Date | **From definition:** From Permit Application valid to. **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Permit Number (`permit_number`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Application Notes (`notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Declaration Order Exemption (field `exemptions` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Exemption Certificate (`exemption_certificate`) | Link | **Purpose:** Creates a controlled reference to **Exemption Certificate** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Exemption Certificate**. Create the master first if it does not exist. |
| Exemption Type (`planned_exemption_type`) | Link | **From definition:** Set before a certificate is linked. Copied to Declaration. Default for Create > Exemption Certificate. **Purpose:** Creates a controlled reference to **Exemption Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Exemption Type**. Create the master first if it does not exist. |
| Is Required (`is_required`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Required Date (`required_date`) | Date | **From definition:** Target date the exemption/certificate is required (planning). Copied to Declaration. **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Type (Certificate) (`exemption_type`) | Data | **From definition:** From linked Exemption Certificate. **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Certificate Number (`certificate_number`) | Data | **From definition:** From linked Exemption Certificate. **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Exemption Basis (`exemption_basis`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Trade Agreement, Certificate, Country, Commodity, Other. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Exemption Percentage (`exemption_percentage`) | Percent | **From definition:** Default percentage from Exemption Type on the certificate. **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Exempted Duty (`exempted_duty`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `column_break_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Exempted Tax (`exempted_tax`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Exempted Fee (`exempted_fee`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Total Exempted (`total_exempted`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Verification (`verification_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Certificate Verified (`certificate_verified`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_verification` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Verification Date (`verification_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Notes (`notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

#### Child table: Declaration Order Milestone (field `milestones` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Milestone (`milestone`) | Link | **Purpose:** Creates a controlled reference to **Logistics Milestone** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Milestone**. Create the master first if it does not exist. |
| Status (`status`) | Select | **From definition:** Set by system: Started when Actual Start is set, Completed when Actual End is set. **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Planned, Started, Completed, Delayed. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Planned Start (`planned_start`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Planned End (`planned_end`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `column_break_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Actual Start (`actual_start`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Actual End (`actual_end`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `column_break_3` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Source (`source`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Manual, Fetched. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Fetched At (`fetched_at`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Created At (`created_at`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Automation (`section_break_automation`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Planned Date Basis (`automation_planned_date_basis`) | Data | **From definition:** From Milestone Template: basis for planned_end **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Update Trigger (`automation_update_trigger_type`) | Data | **From definition:** From template: None / Date Based / Field Based **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Sync Parent Date Field (`automation_sync_parent_date_field`) | Data | **From definition:** Date Based: parent field synced with actual_end **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Sync Direction (`automation_sync_direction`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Trigger Field (`automation_trigger_field`) | Data | **From definition:** Field Based: parent field for condition **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Trigger Condition (`automation_trigger_condition`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Trigger Value (`automation_trigger_value`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Trigger Action (`automation_trigger_action`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Declaration Order Charges (field `charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `column_break_other_svc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Service Type (`service_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Air, Sea, Transport, Customs, Warehousing. |
| Item Code (`item_code`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `item_code.item_name` when the link/source changes — verify after edits. |
| Charge Type (`charge_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Margin, Disbursement, Revenue, Cost. |
| Charge Category (`charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Freight, Fuel Surcharge, Security Surcharge, War Risk Surcharge, Terminal Handling, Port Charges, Customs Clearance, Documentation, Insurance, Storage, Detention, Demurrage, Other. |
| `column_break_zxoy` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Description (`description`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Auto-filled from `charge_item.description` when the link/source changes — verify after edits. |
| Sales Quote Link (`sales_quote_link`) | Link | **Purpose:** Creates a controlled reference to **Sales Quote** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Quote**. Create the master first if it does not exist. |
| Other Services (`is_other_service`) | Check | **From definition:** Automatically determined from the selected item. This field cannot be edited. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `charge_item.custom_is_other_service` when the link/source changes — verify after edits. |
| `section_break_wicx` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Revenue (`column_break_ruye`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Bill To (`bill_to`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Estimated Revenue (`estimated_revenue`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Use Tariff in Revenue (`use_tariff_in_revenue`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Revenue Tariff (`revenue_tariff`) | Link | **Purpose:** Creates a controlled reference to **Tariff** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Tariff**. Create the master first if it does not exist. |
| Cost (`column_break_lday`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Pay To (`pay_to`) | Link | **Purpose:** Creates a controlled reference to **Supplier** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Supplier**. Create the master first if it does not exist. |
| Estimated Cost (`estimated_cost`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Use Tariff in Cost (`use_tariff_in_cost`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Cost Tariff (`cost_tariff`) | Link | **Purpose:** Creates a controlled reference to **Tariff** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Tariff**. Create the master first if it does not exist. |
| Revenue & Cost (`section_break_revenue_cost`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Revenue (`revenue_column`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Revenue Calculation Method (`revenue_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Flat Rate, Base Plus Additional, First Plus Additional, Percentage, Location-based, Weight Break, Qty Break. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Unit Rate (`rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Unit Type (`unit_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Distance, Weight, Chargeable Weight, Volume, Package, Piece, Job, Trip, TEU, Container, Operation Time. |
| Minimum Quantity (`minimum_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Unit Rate (`minimum_unit_rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Minimum Charge (`minimum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Maximum Charge (`maximum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Base Amount (`base_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Base Quantity (`base_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Cost (`column_break_cost_calc`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Calculation Method (`cost_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Flat Rate, Base Plus Additional, First Plus Additional, Percentage, Location-based, Weight Break, Qty Break. |
| Quantity (`cost_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| UOM (`cost_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Currency (`cost_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Unit Cost (`unit_cost`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Unit Type (`cost_unit_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Distance, Weight, Chargeable Weight, Volume, Package, Piece, Job, Trip, TEU, Container, Operation Time. |
| Minimum Quantity (`cost_minimum_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Unit Rate (`cost_minimum_unit_rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Minimum Charge (`cost_minimum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Maximum Charge (`cost_maximum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Base Amount (`cost_base_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **cost_currency** on this form (or company default). |
| Base Quantity (`cost_base_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Calculation Notes (`section_break_calculation_notes`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Revenue Calc Notes (`revenue_calc_notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_vplm` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Cost Calc Notes (`cost_calc_notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Weight Breaks (`section_break_weight_breaks`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Manage Selling Weight Breaks (`selling_weight_break`) | Button | **Purpose:** Runs an action (open a dialog, populate child rows, recalculate, sync from template). **What to enter:** Click the button; follow prompts. Any data you add is usually stored in other fields or child tables. |
| Manage Selling Qty Breaks (`selling_qty_break`) | Button | **Purpose:** Runs an action (open a dialog, populate child rows, recalculate, sync from template). **What to enter:** Click the button; follow prompts. Any data you add is usually stored in other fields or child tables. |
| `column_break_calc_notes` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Manage Cost Weight Breaks (`cost_weight_break`) | Button | **Purpose:** Runs an action (open a dialog, populate child rows, recalculate, sync from template). **What to enter:** Click the button; follow prompts. Any data you add is usually stored in other fields or child tables. |
| Manage Cost Qty Breaks (`cost_qty_break`) | Button | **Purpose:** Runs an action (open a dialog, populate child rows, recalculate, sync from template). **What to enter:** Click the button; follow prompts. Any data you add is usually stored in other fields or child tables. |
| Other Services (`other_services_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Other Service Type (`other_service_type`) | Link | **Purpose:** Creates a controlled reference to **Other Service** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Other Service**. Create the master first if it does not exist. |
| Date Started (`date_started`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Date Ended (`date_ended`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| `column_break_ncht` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Reference No (`other_service_reference_no`) | Data | **Purpose:** Carrier, customs, or commercial reference printed on transport or customs documents. **What to enter:** The exact identifier from the MAWB/HAWB, B/L, container interchange, or tax invoice. |
| Notes (`other_service_notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

#### Child table: Internal Job Detail (field `internal_job_details` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Service Type (`service_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Air, Sea, Transport, Customs, Warehousing. |
| `column_break_ident` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Job Type (`job_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Air Booking, Sea Booking, Transport Order, Declaration Order, Inbound Order. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Job No (`job_no`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **job_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
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
| Container No. (`container_no`) | Data | **From definition:** Sea container number for Transport Order created from Sea Shipment (cargo scoped to this unit). **Purpose:** Carrier, customs, or commercial reference printed on transport or customs documents. **What to enter:** The exact identifier from the MAWB/HAWB, B/L, container interchange, or tax invoice. |
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

<!-- wiki-field-reference:end -->

## 11. Related Topics

- [Declaration](welcome/declaration)
- [Declaration Product Code](welcome/declaration-product-code)
- [CI Charge Code](welcome/ci-charge-code)
- [Commodity](welcome/commodity)
- [Customs Authority](welcome/customs-authority)
- [Customs Settings](welcome/customs-settings)
- [Customs Module](welcome/customs-module)
- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
