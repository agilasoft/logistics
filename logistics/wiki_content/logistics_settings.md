# Logistics Settings

**Logistics Settings** is a single-document configuration that defines global defaults and behavior shared across CargoNext modules. It controls company defaults, numbering, recognition, and cross-module options.

To access Logistics Settings, go to:

**Home > Logistics > Logistics Settings**

## 1. Prerequisites

Before configuring Logistics Settings, ensure the following are set up:

- Company, Branch, Cost Center, Profit Center (from ERPNext)
- Naming Series for key doctypes (if custom)

## 2. How to Configure

1. Go to **Logistics Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Default company for new logistics documents
- **Default Branch** – Default branch
- **Default Cost Center** – Default cost center for job costing
- **Default Profit Center** – Default profit center
- **Default Currency** – Default currency for charges

### 3.2 Naming Settings

- **Sea Booking Naming Series** – Naming for Sea Booking
- **Sea Shipment Naming Series** – Naming for Sea Shipment
- **Air Booking Naming Series** – Naming for Air Booking
- **Air Shipment Naming Series** – Naming for Air Shipment
- **Transport Order Naming Series** – Naming for Transport Order
- **Transport Job Naming Series** – Naming for Transport Job
- **Declaration Order Naming Series** – Naming for Declaration Order
- **Declaration Naming Series** – Naming for Declaration
- **Warehouse Job Naming Series** – Naming for Warehouse Job

### 3.3 Recognition Settings

- **Enable WIP Recognition** – Enable work-in-progress recognition for jobs
- **Default Recognition Policy** – Policy for revenue/cost recognition
- **Recognition Date Basis** – Basis for recognition (ETD, ETA, Job Date)

### 3.4 Integration Settings

- **Enable ERPNext Sales Order Integration** – Link to ERPNext Sales Order
- **Enable ERPNext Purchase Integration** – Link to ERPNext Purchase
- **Default Item Group** – Default for logistics items

### 3.5 Portal Settings

- **Enable Customer Portal** – Enable portal for customers
- **Portal Default Route** – Default route after login
- **Enable Transport Jobs Portal** – Enable transport jobs on portal
- **Enable Warehouse Jobs Portal** – Enable warehouse jobs on portal
- **Enable Stock Balance Portal** – Enable stock balance on portal

## 4. Related Topics

- [Sea Freight Settings](welcome/sea-freight-settings)
- [Air Freight Settings](welcome/air-freight-settings)
- [Transport Settings](welcome/transport-settings)
- [Warehouse Settings](welcome/warehouse-settings)
- [Customer Portal](welcome/customer-portal)
