# Sea Booking

**Sea Booking** is the customer-facing booking document for sea freight. It captures shipper, consignee, origin/destination ports, ETD/ETA, house BL, packages, charges, cutoffs, and documents. Sea Shipments are created from Sea Bookings.

To access: **Home > Sea Freight > Sea Booking**

## 1. Prerequisites

- [Sea Freight Settings](welcome/sea-freight-settings)
- [Container Type](welcome/container-type)
- [Shipper](welcome/shipper), [Consignee](welcome/consignee)
- Shipping Line, Freight Agent, Port masters

## 2. Key Fields

- **House Type** – Direct or Consolidation (FCL/LCL)
- **Direction** – Import, Export, Domestic
- **Entry Type** – Direct, Transit, Transshipment
- **Cutoffs** – Cargo, Document, VGM, Gate-In, Empty Return
- **Packages** – Weight, volume, chargeable
- **Charges** – Selling and cost charges with weight/qty breaks (unified calculation engine; revenue and cost calculation methods)
- **Documents** – Job Document child table; Populate from Template

## 3. Workflow

1. Create Sea Booking from [Sales Quote](welcome/sales-quote) or manually.
2. Add packages, charges, cutoffs.
3. Submit when ready.
4. Create [Sea Shipment](welcome/sea-shipment) from the booking.

## 4. Related Topics

- [Sea Shipment](welcome/sea-shipment)
- [Sea Consolidation](welcome/sea-consolidation)
- [Master Bill](welcome/master-bill)
- [Sea Freight Module](welcome/sea-freight-module)
- [Document Management](welcome/document-management)
