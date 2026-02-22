# Declaration Order

**Declaration Order** is a transaction that captures customs declaration requirements from the customer before the actual declaration is submitted. It serves as the order document that flows into Declaration for customs clearance execution.

A Declaration Order records the customer's customs requirements including import/export details, commodities, parties, and documents. It can be created from a Sales Quote or entered directly. Once confirmed, it links to one or more Declarations for submission to customs authorities.

To access Declaration Order, go to:

**Home > Customs > Declaration Order**

## 1. Prerequisites

Before creating a Declaration Order, it is advised to set up the following:

- [Customs Setup](welcome/customs-setup) – Configure customs authorities and basic settings
- [Customs Master Data](welcome/customs-master-data) – HS codes, commodity classifications, document types
- Customer, Shipper, Consignee (from ERPNext)
- Customs Authority

## 2. How to Create a Declaration Order

1. Go to the Declaration Order list, click **New**.
2. Enter **Order Date** and select **Customer**.
3. Select **Declaration Type** (Import, Export, Transit, etc.).
4. Select **Customs Authority** and **Port of Entry/Exit**.
5. Add **Commodities** with HS codes, descriptions, quantities, and values.
6. Add **Parties** (Importer, Exporter, Declarant, etc.).
7. Add **Charges** as needed.
8. **Save** the document.

### 2.1 Statuses

- **Draft** – Order is being prepared
- **Submitted** – Order is confirmed (when submittable)
- **Cancelled** – Order has been cancelled

## 3. Features

### 3.1 Documents Tab

The Documents tab allows you to track required customs documents (Commercial Invoice, Packing List, Bill of Lading, Certificates of Origin, etc.) with status, date required, and attachments. Use **Populate from Template** to load document requirements based on product type and declaration type.

### 3.2 Integration with Declaration

Once a Declaration Order is confirmed, create a Declaration and link it to this order. The declaration inherits commodities, parties, and document requirements for submission to customs.

## 4. Related Topics

- [Declaration](welcome/declaration)
- [Commodity](welcome/commodity)
- [Customs Authority](welcome/customs-authority)
- [Customs Settings](welcome/customs-settings)
