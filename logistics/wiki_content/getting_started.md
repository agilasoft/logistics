# Getting Started with CargoNext

**CargoNext** is a comprehensive logistics management platform built on the Frappe framework. This guide walks you through initial setup and configuration.

To access CargoNext, go to:

**Home > [Module]** (Sea Freight, Air Freight, Transport, Customs, Warehousing, Pricing Center)

## 1. Prerequisites

- **ERPNext** (v16+) installed and configured
- **Frappe Framework** (v16+)
- Company, Customer, Item masters in ERPNext
- User accounts and roles configured

## 2. Initial Setup Order

### 2.1 Global Settings

1. **[Logistics Settings](welcome/logistics-settings)** – Default company, branch, cost center, naming series, portal options
2. **[Logistics Document Type](welcome/logistics-document-type)** – Document types for document tracking (CI, PL, BL, AWB, etc.)
3. **[Document List Template](welcome/document-list-template)** – Document requirements per product type
4. **[Logistics Milestone](welcome/logistics-milestone)** – Milestones for job tracking

### 2.2 Sea Freight Setup

1. **[Sea Freight Settings](welcome/sea-freight-settings)** – Defaults, calculation, penalties, integration
2. **[Container Type](welcome/container-type)** – 20ft, 40ft, 40ft HC, etc.
3. **[Freight Routing](welcome/freight-routing)** – Route masters (if used)
4. Port masters (from ERPNext or custom)
5. Shipping Line, Freight Agent (if applicable)

### 2.3 Air Freight Setup

1. **[Air Freight Settings](welcome/air-freight-settings)** – Defaults, calculation, document generation
2. **[ULD Type](welcome/uld-type)** – AKE, AKN, PMC, etc.
3. **[IATA Settings](welcome/iata-settings)** – IATA integration (if used)
4. Airport masters (from ERPNext or custom)
5. Airline masters

### 2.4 Transport Setup

1. **[Transport Settings](welcome/transport-settings)** – Routing, constraints, carbon, automation
2. **[Transport Capacity Settings](welcome/transport-capacity-settings)** – Capacity management
3. **[Load Type](welcome/load-type)** – FCL, LCL, Palletized, etc.
4. **[Vehicle Type](welcome/vehicle-type)** – Truck, Van, etc.
5. **[Transport Zone](welcome/transport-zone)** – For pricing (Pricing Center)
6. **[Transport Template](welcome/transport-template)** – Predefined configurations (optional)

### 2.5 Customs Setup

1. **[Customs Settings](welcome/customs-settings)** – Defaults, compliance
2. **[Customs Authority](welcome/customs-authority)** – Customs authorities
3. **[Commodity](welcome/commodity)** – HS codes and commodity masters
4. **[Customs Rate](welcome/customs-rate)** – Duty and tax rates (if used)

### 2.6 Warehousing Setup

1. **[Warehouse Settings](welcome/warehouse-settings)** – Defaults, billing, capacity
2. **[Storage Location](welcome/storage-location)** – Warehouse location hierarchy
3. **[Handling Unit Type](welcome/handling-unit-type)** – Pallet, Box, etc.
4. **[VAS Order Type](welcome/vas-order-type)** – Value-added service types
5. Warehouse (from ERPNext Stock)

## 3. Typical Workflow

1. **Quote** – Create [Sales Quote](welcome/sales-quote) or [One Off Quote](welcome/one-off-quote)
2. **Order** – Create [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking), [Transport Order](welcome/transport-order), [Declaration Order](welcome/declaration-order), [Inbound Order](welcome/inbound-order), or [Release Order](welcome/release-order)
3. **Job** – Create [Sea Shipment](welcome/sea-shipment), [Air Shipment](welcome/air-shipment), [Transport Job](welcome/transport-job), [Declaration](welcome/declaration), or [Warehouse Job](welcome/warehouse-job)
4. **Documents** – Track documents in the Documents tab
5. **Milestones** – Track progress in the Milestones tab
6. **Billing** – Create Sales Invoice from the job

## 4. Related Topics

- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
- [Customer Portal](welcome/customer-portal)
- [Reports Overview](welcome/reports-overview)
