# Sea Freight Settings

**Sea Freight Settings** is a single-document configuration that defines default values and behavior for the Sea Freight module. It controls company defaults, location defaults, penalty rates, calculation methods, and integration options.

To access Sea Freight Settings, go to:

**Home > Sea Freight > Sea Freight Settings**

## 1. Prerequisites

Before configuring Sea Freight Settings, ensure the following are set up:

- Company, Branch, Cost Center, Profit Center (from ERPNext)
- Port masters (Origin Port, Destination Port)
- Shipping Line, Freight Agent (if applicable)
- [Logistics Service Level](welcome/logistics-service-level) for default service level

## 2. How to Configure

1. Go to **Sea Freight Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Company for new Sea Bookings and Sea Shipments
- **Default Branch** – Branch for new documents
- **Default Cost Center** – Cost center for job costing
- **Default Profit Center** – Profit center for revenue allocation
- **Default Currency** – Currency for charges
- **Default Incoterm** – Trade terms (FOB, CIF, etc.)
- **Default Service Level** – Logistics Service Level for sea freight

### 3.2 Location Settings

- **Default Origin Location** – Default origin for new bookings
- **Default Destination Location** – Default destination
- **Default Origin Port** – Default origin port
- **Default Destination Port** – Default destination port

### 3.3 Business Settings

- **Default Shipping Line** – Default shipping line
- **Default Freight Agent** – Default freight agent
- **Allow Creation of Sales Order** – Enable creating Sales Order from Sea Booking
- **Auto Create Job Costing** – Automatically create job costing records
- **Enable Milestone Tracking** – Enable Job Milestone on Sea Shipments

### 3.4 Penalty Settings

- **Default Free Time Days** – Free time before detention/demurrage
- **Detention Rate Per Day** – Detention charge rate
- **Demurrage Rate Per Day** – Demurrage charge rate

### 3.5 Calculation Settings

- **Volume to Weight Factor** – Divisor for volumetric weight
- **Chargeable Weight Calculation** – Method (Gross, Volumetric, Chargeable)
- **Default Charge Basis** – TEU Count, Container Count, Weight, Volume
- **Default Weight UOM**, **Default Volume UOM** – Units of measure

### 3.6 Integration Settings

- **Enable Vessel Tracking** – Integrate vessel tracking
- **Enable Customs Clearance Tracking** – Track customs clearance status
- **Enable EDI Integration** – Enable EDI for shipping lines

## 4. Related Topics

- [Sea Booking](welcome/sea-booking)
- [Sea Shipment](welcome/sea-shipment)
- [Sea Freight Consolidation](welcome/sea-freight-consolidation)
- [Logistics Service Level](welcome/logistics-service-level)
