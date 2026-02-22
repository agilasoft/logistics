# Air Freight Settings

**Air Freight Settings** is a single-document configuration that defines default values and behavior for the Air Freight module. It controls company defaults, location defaults, calculation methods, document generation, consolidation, and billing.

To access Air Freight Settings, go to:

**Home > Air Freight > Air Freight Settings**

## 1. Prerequisites

Before configuring Air Freight Settings, ensure the following are set up:

- Company, Branch, Cost Center, Profit Center (from ERPNext)
- Airport masters (Origin, Destination)
- [ULD Type](welcome/uld-type) for default ULD
- [Logistics Service Level](welcome/logistics-service-level)

## 2. How to Configure

1. Go to **Air Freight Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Company** – Company for new Air Bookings and Air Shipments
- **Default Branch**, **Default Cost Center**, **Default Profit Center**
- **Default Currency**, **Default Incoterm**, **Default Service Level**
- **Default House Type** – Direct, Consolidation, Groupage
- **Default Direction** – Import, Export, Domestic
- **Default Entry Type** – Direct, Transit, Transshipment

### 3.2 Location Settings

- **Default Origin Airport**, **Default Destination Airport**
- **Default Origin Port**, **Default Destination Port**

### 3.3 Business Settings

- **Default Airline**, **Default Freight Agent**
- **Allow Creation of Sales Order**, **Auto Create Job Costing**
- **Enable Milestone Tracking**

### 3.4 Calculation Settings

- **Volume to Weight Factor** – Divisor for chargeable weight (typically 6000 for air)
- **Chargeable Weight Calculation** – Gross, Volumetric, Chargeable
- **Default Charge Basis**, **Default Weight UOM**, **Default Volume UOM**

### 3.5 Document Settings

- **Auto Generate House AWB** – Auto-generate house air waybill numbers
- **Auto Generate Master AWB** – Auto-generate master AWB numbers
- **Require DG Declaration** – Require dangerous goods declaration
- **Default ULD Type** – Default ULD type for packages

### 3.6 Consolidation Settings

- **Default Consolidation Type** – Type for air consolidations
- **Auto Assign to Consolidation** – Automatically assign shipments
- **Max Consolidation Weight**, **Max Consolidation Volume**

### 3.7 Billing Settings

- **Auto Billing Enabled** – Enable automated billing
- **Default Billing Currency** – Currency for billing
- **Enable Billing Alerts** – Alert for unbilled shipments

## 4. Related Topics

- [Air Booking](welcome/air-booking)
- [Air Shipment](welcome/air-shipment)
- [Air Consolidation](welcome/air-consolidation)
- [ULD Type](welcome/uld-type)
- [IATA Settings](welcome/iata-settings)
