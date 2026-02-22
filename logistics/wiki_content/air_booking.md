# Air Booking

**Air Booking** is a transaction that captures air freight booking details from the customer before execution. It serves as the order document that flows into Air Shipment for job execution.

An Air Booking records the customer's air cargo requirements including origin/destination airports, cargo details, routing, packages, and commercial terms. It can be created from a Sales Quote or entered directly. Once confirmed, it typically links to one or more Air Shipments for the actual cargo movement.

To access Air Booking, go to:

**Home > Air Freight > Air Booking**

## 1. Prerequisites

Before creating an Air Booking, it is advised to set up the following:

- [Air Freight Setup](welcome/air-freight-setup) – Configure airlines, airports, and basic settings
- [Air Freight Master Data](welcome/air-freight-master-data) – ULD types, services, charge types
- Customer, Shipper, Consignee (from ERPNext)
- Airport masters (Origin, Destination)

## 2. How to Create an Air Booking

1. Go to the Air Booking list, click **New**.
2. Enter **Booking Date** and select **Customer**.
3. Select **Direction** (Import, Export, Domestic) and **Entry Type** (Direct, Transit, Transshipment, etc.).
4. Select **Shipper** and **Consignee** addresses.
5. Enter **Origin Airport**, **Destination Airport**, **ETD**, and **ETA**.
6. Add **Routing Legs** if multi-leg routing is required.
7. Add **Packages** with weights, dimensions, and ULD types.
8. Add **Services** and **Charges** as needed.
9. **Save** the document.

### 2.1 Creating from Sales Quote

You can create an Air Booking from an existing Sales Quote. Use the **Create from Sales Quote** button or action to auto-fill customer, routing, and cargo details from the quote.

### 2.2 Statuses

- **Draft** – Booking is being prepared
- **Submitted** – Booking is confirmed (when submittable)
- **Cancelled** – Booking has been cancelled

## 3. Features

### 3.1 House and Master Details

- **House Type** – Direct, Consolidation, or Groupage
- **Incoterm** – Trade terms (FOB, CIF, etc.)
- **Goods Value**, **Insurance** – For documentation and customs
- **Chargeable Weight** – Calculated from volumetric and gross weight

### 3.2 Documents Tab

The Documents tab allows you to track required documents (Commercial Invoice, Packing List, Air Waybill, etc.) with status, date required, and attachments. Use **Populate from Template** to load document requirements based on product type and direction.

### 3.3 Integration with Air Shipment

Once an Air Booking is confirmed, create an Air Shipment and link it to this booking. The shipment inherits routing, cargo, and party details for execution.

## 4. Related Topics

- [Air Shipment](welcome/air-shipment)
- [Air Consolidation](welcome/air-consolidation)
- [Master Air Waybill](welcome/master-air-waybill)
- [Air Freight Settings](welcome/air-freight-settings)
