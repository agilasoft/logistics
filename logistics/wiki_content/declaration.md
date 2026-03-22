# Declaration

**Declaration** is the customs clearance document submitted to customs authorities. It is created from a [Declaration Order](welcome/declaration-order) and inherits parties, commercial invoice data, line items, charges, documents, permits, and exemptions. The Declaration tracks submission, processing, clearance, and billing status.

To access: **Home > Customs > Declaration**

For customs-related upgrades (status migrations, permit/exemption structure), see [Recent Platform Updates](welcome/recent-platform-updates).

## 1. Prerequisites

- [Declaration Order](welcome/declaration-order) – Source order (or create manually)
- [Declaration Product Code](welcome/declaration-product-code) – Product codes for line items
- [CI Charge Code](welcome/ci-charge-code) – Charge codes for invoice charges
- [Commodity](welcome/commodity) – HS codes and commodity classifications
- [Customs Authority](welcome/customs-authority) – Target authority
- [Document List Template](welcome/document-list-template) – Optional document checklist
- [Logistics Milestone](welcome/logistics-milestone) – For milestone tracking

## 2. Main Sections

### 2.1 Header

- **Declaration Date** – Date of the declaration
- **Sales Quote**, **Declaration Order** – Source links
- **Customer** – Customer (required)
- **Customs Authority** – Target authority (required)
- **Declaration Type** – Import, Export, Transit, Bonded
- **Declaration Number** – Number assigned by customs (after submission)
- **Total Declaration Value** – Calculated from commercial invoice line items or invoice total
- **Currency**, **Exchange Rate** – Currency for the declaration
- **Status** – Draft, Submitted, Under Review, Cleared, Released, Rejected, Cancelled
- **Customs Broker**, **Notify Party** – Optional parties

### 2.2 Shipment Details

- **Exporter/Shipper** – Link to [Shipper](welcome/shipper)
- **Importer/Consignee** – Link to [Consignee](welcome/consignee)
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
  - **Charge Code** – Link to [CI Charge Code](welcome/ci-charge-code)
  - **Amount**, **Currency** – Charge value
  - **Incl. in Inv. Lines?**, **Add to FOB?**, **VAT Apply**, **Included in Inv. Amt** – Distribution flags
  - **Distribute By** – Weight, Volume, Quantity, Value

## 4. Processing Information

- **Submission Date**, **Submission Time** – When submitted to customs
- **Approval Date** – When cleared
- **Rejection Date**, **Rejection Reason** – If rejected
- **Processing Officer** – Customs officer
- **Expected Clearance Date**, **Actual Clearance Date** – Clearance dates

## 5. Financial Information

- **Duty Amount**, **Tax Amount**, **Other Charges** – Customs charges
- **Total Payable** – Total amount payable
- **Payment Status** – Payment status

## 6. Service Level Agreement

- **Service Level** – Link to [Logistics Service Level](welcome/logistics-milestone)
- **SLA Target Date**, **SLA Status**, **SLA Target Source**, **SLA Notes** – SLA monitoring

## 7. Permits Tab

- **Permit Requirements** – Child table for permit lines (type, authority, dates, status); aligned with data created from the [Declaration Order](welcome/declaration-order) where applicable.
- **Exemptions** – Child table for exemptions carried from the order or maintained on the declaration.
- Track permits and exemptions for the declaration.

## 8. Charges Tab

- **Charges** – Declaration Charges child table
- Supports quantity breaks and weight breaks (unified calculation engine). Each charge row has **Estimated Revenue** and **Estimated Cost** (from the Declaration Order; used for WIP and accrual) and **Actual Revenue** and **Actual Cost** (calculated on the declaration; used for Sales Invoice and Purchase Invoice when present). Use **Recalculate All Charges** to refresh actual amounts; estimated amounts are not changed.
- **Create Change Request** – Add additional charges via [Change Request](welcome/change-request)

## 8.1 Profitability (from GL)

When **Job Costing Number** and **Company** are set, the form displays a Profitability section with revenue, cost, gross profit, WIP, and accrual from the General Ledger. See [Job Management Module](welcome/job-management-module).

## 9. Milestones Tab

- **Milestone Template** – Optional template for milestone structure
- **Milestones** – Declaration Milestone child table
- Visual timeline (Submitted, Under Review, Customs Clearance, Released).
- Use **Generate from Template** to populate from template.

## 10. Documents Tab

- **Document List Template** – Optional template to load document checklist
- **Documents** – Job Document child table
- Commercial Invoice, Packing List, Bill of Lading, Certificates of Origin, etc.
- Use **Populate from Template** to load document requirements.
- Track status, date required, and attachments per document.

## 11. Accounts Tab

- **Company**, **Branch**, **Cost Center**, **Profit Center** – Accounting dimensions
- **Job Costing Number**, **Project** – Optional job tracking

## 12. Invoice Monitoring

- **Sales Invoice**, **Purchase Invoice** – Linked invoices
- **Fully Invoiced**, **Date Fully Invoiced** – Invoice status
- **Fully Paid**, **Date Fully Paid** – Payment status
- **Date Sales Invoice Requested** / **Submitted** – Invoice lifecycle
- **Date Purchase Invoice Requested** / **Submitted** – Cost invoice lifecycle

## 13. Recognition (WIP / Accrual)

- **WIP Recognition** – Work-in-progress recognition settings (uses **Estimated Revenue** only)
- **Accrual Recognition** – Cost accrual settings (uses **Estimated Cost** only)
- **Estimated Revenue**, **WIP Amount**, **Recognized Revenue** – Revenue tracking
- **Estimated Costs**, **Accrual Amount**, **Recognized Costs** – Cost tracking
- **Sales Invoice** and **Purchase Invoice** creation use **Actual Revenue** and **Actual Cost** when present and &gt; 0; otherwise they fall back to estimated amounts.

## 14. Status Workflow

| Status | Description |
|--------|-------------|
| Draft | Declaration is being prepared |
| Submitted | Submitted to customs |
| Under Review | Customs is reviewing |
| Cleared | Approved by customs |
| Released | Cargo released |
| Rejected | Rejected by customs |
| Cancelled | Declaration cancelled |

## 15. Workflow

1. Create Declaration from Declaration Order (or manually).
2. Set Exporter/Shipper and Importer/Consignee.
3. Add Commercial Invoice Line Items – select **Declaration Product Code** (filtered by importer/exporter); Item, Product Code, Tariff, Goods Description, etc. are auto-filled.
4. Add Commercial Invoice Charges – select **CI Charge Code**.
5. Attach documents (Commercial Invoice, Packing List, BL, etc.).
6. Add Permits and Exemptions as required.
7. Submit to Customs Authority.
8. Track milestones (Submitted → Under Review → Released).
9. Create Sales Invoice for billing.

## 16. Amendments

- Use **Amended From** to link an amended declaration to the original.
- Amendments follow the standard Frappe amendment workflow.

## 17. Related Topics

- [Declaration Order](welcome/declaration-order)
- [Declaration Product Code](welcome/declaration-product-code)
- [CI Charge Code](welcome/ci-charge-code)
- [Customs Workflow Guide](welcome/customs-workflow-guide)
- [Commodity](welcome/commodity)
- [Customs Authority](welcome/customs-authority)
- [Milestone Tracking](welcome/milestone-tracking)
- [Document Management](welcome/document-management)
- [Change Request](welcome/change-request)
- [Job Management Module](welcome/job-management-module)
- [Customs Module](welcome/customs-module)
