# Warehousing Module

**Warehousing** covers receiving, putaway, picking, release, transfers, value-added services (VAS), and stocktake. In CargoNext, the Warehousing module manages: Inbound Order → Warehouse Job (receiving/putaway) | Release Order → Warehouse Job (pick/release) | Transfer Order, VAS Order, Stocktake Order → Warehouse Job.

Industry terms: **3PL** (Third-Party Logistics), **VAS** (Value-Added Services), **Putaway**, **Pick**, **Cycle Count**, **ABC Analysis**, **Storage Location**.

To access the Warehousing workspace, go to:

**Home > Warehousing**

## 1. Typical Workflow

### 1.1 Inbound (Receiving)

1. Create [Inbound Order](welcome/inbound-order)
2. Create [Warehouse Job](welcome/warehouse-job) (type: Putaway)
3. Execute receiving and putaway operations
4. Use [Warehouse Job Card](welcome/warehouse-job-card) or [Plate Scanner](welcome/plate-scanner) for mobile execution

### 1.2 Outbound (Release)

1. Create [Release Order](welcome/release-order)
2. Create [Warehouse Job](welcome/warehouse-job) (type: Pick)
3. Execute pick and release operations

### 1.3 Internal Transfer

1. Create [Transfer Order](welcome/transfer-order)
2. Create [Warehouse Job](welcome/warehouse-job) (type: Transfer)

### 1.4 VAS (Value-Added Services)

1. Create [VAS Order](welcome/vas-order)
2. Create [Warehouse Job](welcome/warehouse-job) (type: VAS)

### 1.5 Stocktake

1. Create [Stocktake Order](welcome/stocktake-order)
2. Create [Warehouse Job](welcome/warehouse-job) (type: Stocktake)
3. Use [Count Sheet](welcome/count-sheet) for counting

## 2. Key Concepts

### 2.1 Storage Location Hierarchy

Warehouse → Zone → Aisle → Rack → Level → Bin. Configure in [Storage Location](welcome/storage-location).

### 2.2 Handling Units

Track inventory by [Handling Unit Type](welcome/handling-unit-type) (Pallet, Box, etc.). Supports UOM conversions.

### 2.3 Periodic Billing

[Periodic Billing](welcome/periodic-billing) automates storage charges based on [Warehouse Contract](welcome/warehouse-contract).

## 3. Workspace Structure

### 3.1 Quick Access

- Sales Quote, Warehouse Contract, Inbound Order, Release Order, Transfer Order, VAS Order, Stocktake Order, Warehouse Job, Periodic Billing, Gate Pass

### 3.2 Mobile Pages

- [Warehouse Job Card](welcome/warehouse-job-card) – Mobile job execution
- [Plate Scanner](welcome/plate-scanner) – License plate scanning at dock
- [Count Sheet](welcome/count-sheet) – Stocktake counting

### 3.3 Reports

- **Stock:** Warehouse Stock Balance, Warehouse Stock Ledger, Batch Expiry Risk
- **Capacity:** Storage Location Usage, Handling Unit Capacity, Capacity Forecasting Report, ABC Report
- **Productivity:** Labor Productivity Report, Machine Productivity Report

## 4. Related Topics

- [Getting Started](welcome/getting-started)
- [Warehouse Settings](welcome/warehouse-settings)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Job](welcome/warehouse-job)
- [Glossary](welcome/glossary)
