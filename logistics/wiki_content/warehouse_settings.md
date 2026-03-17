# Warehouse Settings

**Warehouse Settings** is a single-document configuration that defines default values and behavior for the Warehousing module. It controls billing, capacity, storage, handling units, and integration options.

To access Warehouse Settings, go to:

**Home > Warehousing > Warehouse Settings**

## 1. Prerequisites

Before configuring Warehouse Settings, ensure the following are set up:

- Company, Branch, Cost Center (from ERPNext)
- Warehouse (from ERPNext Stock)
- [Storage Location](welcome/storage-location) – For storage hierarchy
- [Handling Unit Type](welcome/handling-unit-type) – For inventory tracking

## 2. How to Configure

1. Go to **Warehouse Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Company for new warehouse documents
- **Default Branch** – Branch for warehouse operations
- **Default Cost Center** – Cost center for warehouse costs
- **Default Warehouse** – Default warehouse for operations

### 3.2 Billing Settings

- **Enable Periodic Billing** – Enable automated periodic billing for storage
- **Billing Frequency** – Daily, Weekly, Monthly
- **Default Billing Currency** – Currency for warehouse charges

### 3.3 Capacity Settings

- **Enable Capacity Management** – Track and enforce capacity limits
- **Capacity Alert Threshold (%)** – Alert when capacity exceeds this percentage
- **Default Volume UOM** – CBM, CFT for capacity
- **Default Weight UOM** – kg, lb for capacity

### 3.4 Storage Settings

- **Default Storage Type** – Default storage type for locations
- **Default Storage Environment** – Ambient, Cold, Frozen, etc.
- **Enable Storage Location Configurator** – Use configurator for location setup

### 3.5 Handling Unit Settings

- **Default Handling Unit Type** – Default for inbound/outbound
- **Enable Handling Unit Tracking** – Track handling units (pallets, boxes)
- **Handling Unit Barcode Format** – Barcode format for scanning

### 3.6 Integration Settings

- **Enable Plate Scanner** – Enable license plate scanning at dock
- **Enable Count Sheet** – Enable count sheet for stocktake
- **Enable Gate Pass** – Enable gate pass for movements

### 3.7 Sustainability Settings

- **Enable Carbon Footprint** – Track carbon for warehouse operations
- **Enable Energy Consumption Tracking** – Track energy usage

## 4. Related Topics

- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Job](welcome/warehouse-job)
- [Warehouse Contract](welcome/warehouse-contract)
- [Storage Location](welcome/storage-location)
- [Handling Unit Type](welcome/handling-unit-type)
