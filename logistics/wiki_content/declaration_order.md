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
- **Job Costing Number**, **Project** – Optional job tracking

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
