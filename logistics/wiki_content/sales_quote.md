# Sales Quote

**Sales Quote** is a multi-product pricing document that can include Sea Freight, Air Freight, Transport, Warehousing, and Customs services. It serves as the commercial offer to the customer and can flow into Bookings, Orders, and Jobs.

A Sales Quote records pricing for one or more services per leg, with weight breaks, quantity breaks, routing, and charges. It integrates with ERPNext Sales Order and can create Air Booking, Sea Booking, Transport Order, Declaration Order, Inbound Order, or Release Order.

To access Sales Quote, go to:

**Home > Pricing Center > Sales Quote**

## 1. Prerequisites

Before creating a Sales Quote, it is advised to set up the following:

- Customer (from ERPNext)
- Port/Airport masters (for freight)
- [Transport Zone](welcome/transport-zone) (for transport)
- Warehouse (for warehousing)

## 2. How to Create a Sales Quote

1. Go to the Sales Quote list, click **New**.
2. Enter **Quote Date** and select **Customer**.
3. Add **Routing Legs** (Sea, Air, Transport, Customs, Warehouse) as needed.
4. Add **Weight Breaks** for freight pricing.
5. Add **Charges** per service.
6. **Save** the document.

### 2.1 Statuses

- **Draft** – Quote is being prepared
- **Submitted** – Quote is sent to customer
- **Lost** – Quote was not accepted
- **Ordered** – Quote was converted to order

## 3. Features

### 3.1 Creating Documents from Sales Quote

From a submitted Sales Quote, you can create:
- Air Booking, Sea Booking
- Transport Order
- Declaration Order
- Inbound Order, Release Order

### 3.2 Integration with ERPNext

Sales Quote can be linked to ERPNext Sales Order. When the order is confirmed, you can create the corresponding logistics documents.

## 4. Related Topics

- [One Off Quote](welcome/one-off-quote)
- [Sea Booking](welcome/sea-booking)
- [Air Booking](welcome/air-booking)
- [Transport Order](welcome/transport-order)
- [Change Request](welcome/change-request)
