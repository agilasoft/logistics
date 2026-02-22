# Sea Booking

**Sea Booking** is a transaction that captures ocean freight booking details from the customer before execution. It serves as the order document that flows into Sea Shipment for job execution.

A Sea Booking records the customer's freight requirements including origin/destination ports, cargo details, routing, containers, packages, and commercial terms. It can be created from a Sales Quote or entered directly. Once confirmed, it typically links to one or more Sea Shipments for the actual cargo movement.

To access Sea Booking, go to:

**Home > Sea Freight > Sea Booking**

## 1. Prerequisites

Before creating a Sea Booking, it is advised to set up the following:

- [Sea Freight Setup](welcome/sea-freight-setup) – Configure shipping lines, ports, and basic settings
- [Sea Freight Master Data](welcome/sea-freight-master-data) – Container types, services, charge types
- Customer, Shipper, Consignee (from ERPNext)
- Port masters (Origin Port, Destination Port)

## 2. How to Create a Sea Booking

1. Go to the Sea Booking list, click **New**.
2. Enter **Booking Date** and select **Customer**.
3. Select **Direction** (Import, Export, Domestic) and **Entry Type** (Direct, Transit, Transshipment, etc.).
4. Select **Shipper** and **Consignee** addresses.
5. Enter **Origin Port**, **Destination Port**, **ETD**, and **ETA**.
6. Add **Routing Legs** if multi-port routing is required.
7. Add **Containers** or **Packages** with weights, dimensions, and marks.
8. Add **Services** and **Charges** as needed.
9. **Save** the document.

### 2.1 Creating from Sales Quote

You can create a Sea Booking from an existing Sales Quote. Use the **Create from Sales Quote** button or action to auto-fill customer, routing, and cargo details from the quote.

### 2.2 Statuses

- **Draft** – Booking is being prepared
- **Submitted** – Booking is confirmed (when submittable)
- **Cancelled** – Booking has been cancelled

## 3. Features

### 3.1 House and Master Details

- **House Type** – Direct, Consolidation, or Groupage
- **House BL** – House bill of lading reference
- **Incoterm** – Trade terms (FOB, CIF, etc.)
- **Goods Value**, **Insurance** – For documentation and customs

### 3.2 Documents Tab

The Documents tab allows you to track required documents (Commercial Invoice, Packing List, Bill of Lading, etc.) with status, date required, and attachments. Use **Populate from Template** to load document requirements based on product type and direction.

### 3.3 Integration with Sea Shipment

Once a Sea Booking is confirmed, create a Sea Shipment and link it to this booking. The shipment inherits routing, cargo, and party details for execution.

## 4. Related Topics

- [Sea Shipment](welcome/sea-shipment)
- [Sea Freight Consolidation](welcome/sea-freight-consolidation)
- [Master Bill](welcome/master-bill)
- [Sea Freight Settings](welcome/sea-freight-settings)
