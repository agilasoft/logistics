# Air Booking

**Air Booking** is the customer-facing booking document for air freight. It captures shipper, consignee, origin/destination ports, ETD/ETA, packages, routing legs, charges, and documents. Air Shipments are created from Air Bookings.

To access: **Home > Air Freight > Air Booking**

## 1. Prerequisites

- [Air Freight Settings](welcome/air-freight-settings)
- [ULD Type](welcome/uld-type)
- Airline, Shipper, Consignee masters
- Port/Airport masters

## 2. Key Fields

- **House Type** – Direct or Consolidation
- **Direction** – Import, Export, Domestic
- **Entry Type** – Direct, Transit, Transshipment
- **Routing Legs** – Flight segments (origin, destination, ETD, ETA)
- **Packages** – Weight, volume, chargeable weight
- **Charges** – Selling and cost charges with weight/qty breaks (unified calculation engine; revenue and cost calculation methods)
- **Documents** – Job Document child table; use Populate from Template

### 2.1 Charges from Sales Quote

When the booking is created from a [Sales Quote](welcome/sales-quote), charge lines copy **Item Code**, **Item Name**, **charge category**, **description**, **Item Tax Template**, and **Invoice Type** (from the Item where applicable) from the quote charges so invoicing and categories stay aligned.

## 3. Workflow

1. Create Air Booking from [Sales Quote](welcome/sales-quote) or manually.
2. Add routing legs, packages, charges.
3. Submit when ready.
4. Create [Air Shipment](welcome/air-shipment) from the booking.

## 4. Related Topics

- [Recent Platform Updates](welcome/recent-platform-updates)
- [Air Shipment](welcome/air-shipment)
- [Air Consolidation](welcome/air-consolidation)
- [Master Air Waybill](welcome/master-air-waybill)
- [Air Freight Module](welcome/air-freight-module)
- [Document Management](welcome/document-management)
