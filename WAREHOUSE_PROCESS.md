# Warehouse Process Documentation

## Table of Contents
1. [Overview](#overview)
2. [Initial Setup and Configuration](#initial-setup-and-configuration)
3. [Warehouse Contract](#warehouse-contract)
4. [Order Types](#order-types)
5. [Warehouse Job Types](#warehouse-job-types)
6. [Putaway Process (Inbound)](#putaway-process-inbound)
7. [Pick Process (Outbound)](#pick-process-outbound)
8. [Transfer Process](#transfer-process)
9. [VAS (Value Added Services) Process](#vas-value-added-services-process)
10. [Stocktake Process](#stocktake-process)
11. [Key Concepts](#key-concepts)
12. [Workflow Summary](#workflow-summary)

---

## Overview

The Warehouse Management System provides comprehensive control over warehouse locations, stock operations, and value-added services. The system manages the complete lifecycle of goods from receiving through storage to shipping, with support for inventory movements, value-added services, and stocktaking.

### Core Components
- **Storage Location Hierarchy**: Site → Building → Zone → Aisle → Bay → Level
- **Handling Units**: Physical containers (pallets, boxes, etc.) that hold items
- **Storage Locations**: Specific physical locations within the warehouse
- **Warehouse Jobs**: Execution units that coordinate warehouse operations
- **Stock Ledger**: Real-time tracking of inventory movements

---

## Initial Setup and Configuration

Before using the warehouse system, the following must be configured:

### 1. Warehouse Settings
- Company-specific warehouse configuration
- Default cost centers, sites, and facilities
- Capacity management settings
- Billing configurations
- Volume and weight UOM defaults
- Sustainability tracking settings

### 2. Storage Location Configurator
Define the warehouse hierarchy:
- **Site**: Top-level location (e.g., "Warehouse A")
- **Building**: Building within a site
- **Zone**: Area within a building
- **Aisle**: Aisle within a zone
- **Bay**: Bay within an aisle
- **Level**: Level within a bay

### 3. Storage Types
Define storage characteristics:
- Storage environment requirements
- Security and compliance types
- Capacity limits (volume, weight)
- Temperature and handling requirements

### 4. Storage Environments
Configure environmental conditions:
- Temperature ranges
- Humidity requirements
- Special handling needs

### 5. Security and Compliance Types
Define security and compliance requirements:
- Access restrictions
- Regulatory compliance needs
- Certification requirements

### 6. Handling Unit Types
Define physical container types:
- Pallets, boxes, crates, etc.
- Volume and weight capacities
- UOM configurations

### 7. Handling Units
Create physical handling units that will hold items during warehouse operations.

### 8. Storage Locations
Create specific storage locations within the warehouse hierarchy with:
- Location code
- Storage type
- Capacity limits
- Status (Active, Inactive, Quarantine, etc.)

### 9. Dock Doors
Configure dock doors for inbound and outbound operations:
- Door code and description
- Site and facility assignment
- Inbound/Outbound designation
- Door type (Leveler, Ramp, Flush Dock, Grade-Level)

### 10. Warehouse Items
Configure items that will be stored in the warehouse:
- Item master data
- Storage type restrictions
- Handling unit type requirements

### 11. VAS Order Types
Define Value Added Services:
- Service types (labeling, repacking, kitting, etc.)
- Pricing and billing rules

### 12. Warehousing Charge Items
Configure chargeable services:
- Storage charges
- Handling charges
- VAS charges

### 13. Warehouse Operation Items
Define operational activities:
- Putaway operations
- Pick operations
- Move operations

---

## Warehouse Contract

A **Warehouse Contract** is the master agreement between the company and customer for warehouse services.

### Key Fields
- **Customer**: The customer for the contract
- **Date**: Contract start date
- **Valid Until**: Contract expiration date
- **Site**: Warehouse site
- **Sales Quote**: Optional link to originating sales quote
- **Shipper** and **Consignee**: Related parties
- **Items**: Contract line items with rates and terms

### Process
1. Create Warehouse Contract (can be linked to Sales Quote)
2. Add contract items with rates
3. Optionally import rates from Sales Quote using "Get Rates" button
4. Submit the contract

### Linked Documents
A Warehouse Contract can generate:
- Warehouse Jobs
- Inbound Orders
- Release Orders
- Transfer Orders
- VAS Orders
- Stocktake Orders

---

## Order Types

### 1. Inbound Order
**Purpose**: Receive goods into the warehouse

**Key Fields**:
- Customer
- Contract (links to Warehouse Contract)
- Order Date, Planned Date, Due Date
- Priority (Low, Normal, High)
- Items (with quantities, UOM, handling units)
- Charges
- Dock assignments (with ETA, vehicle details)

**Process**:
1. Create Inbound Order
2. Add items to be received
3. Assign dock doors and schedule receiving
4. Create Warehouse Job (type: Putaway) from Inbound Order

### 2. Release Order
**Purpose**: Ship goods out of the warehouse

**Key Fields**:
- Customer
- Contract
- Order Date, Planned Date, Due Date
- Priority
- Items (with quantities, locations, handling units)
- Charges
- Dock assignments

**Process**:
1. Create Release Order
2. Add items to be shipped
3. Assign dock doors
4. Create Warehouse Job (type: Pick) from Release Order

### 3. Transfer Order
**Purpose**: Move goods within the warehouse

**Key Fields**:
- Transfer Type (Internal, Customer, Others)
- Customer (if applicable)
- Contract
- Reason (Re-slot, Re-org, Staging, Quality, Quarantine, Returns, Others)
- Items (with source and destination locations)

**Process**:
1. Create Transfer Order
2. Add items to be moved
3. Create Warehouse Job (type: Move) from Transfer Order

### 4. VAS Order
**Purpose**: Perform value-added services on stored goods

**Key Fields**:
- Type (links to VAS Order Type)
- Customer
- Contract
- Planned Date, Due Date
- Priority
- Items (with VAS inputs)

**Process**:
1. Create VAS Order
2. Select VAS Order Type
3. Add items requiring VAS
4. Create Warehouse Job (type: VAS) from VAS Order

### 5. Stocktake Order
**Purpose**: Count and verify inventory

**Key Fields**:
- Type (Full, Cycle, Blind, Investigative, Ad-hoc)
- Scope (Site, Building, Zone, Aisle, Bay, Level)
- Customer
- Contract
- Blind Count flag
- QA Required flag
- Stocktake Days Past Zero

**Process**:
1. Create Stocktake Order
2. Define scope and type
3. Create Warehouse Job (type: Stocktake) from Stocktake Order

---

## Warehouse Job Types

A **Warehouse Job** is the execution unit that coordinates warehouse operations. Each job type corresponds to a specific operation:

### 1. Putaway Job
- **Source**: Inbound Order
- **Purpose**: Receive goods and store them in warehouse locations
- **Workflow**: Receiving → Staging → Putaway → Storage

### 2. Pick Job
- **Source**: Release Order
- **Purpose**: Retrieve goods from storage and prepare for shipping
- **Workflow**: Pick from Storage → Staging → Release

### 3. Move Job
- **Source**: Transfer Order
- **Purpose**: Move goods between locations within warehouse
- **Workflow**: Pick from Source → Putaway to Destination

### 4. VAS Job
- **Source**: VAS Order
- **Purpose**: Perform value-added services on stored goods
- **Workflow**: Pick → VAS Processing → Putaway

### 5. Stocktake Job
- **Source**: Stocktake Order
- **Purpose**: Count and verify inventory
- **Workflow**: Count items at locations → Compare with system → Adjust if needed

---

## Putaway Process (Inbound)

The Putaway process handles receiving goods into the warehouse and storing them in appropriate locations.

### Step-by-Step Process

#### 1. Create Inbound Order
- Navigate to **Inbound Order**
- Enter customer, contract, dates, and priority
- Add items with:
  - Item code
  - Quantity and UOM
  - Handling Unit Type
  - Batch/Serial numbers (if applicable)
- Add dock door assignments with ETA and vehicle details
- Add charges if applicable
- Save the Inbound Order

#### 2. Create Warehouse Job (Putaway)
- From Inbound Order, click **Create > Warehouse Job**
- The system automatically:
  - Sets job type to "Putaway"
  - Links reference order to Inbound Order
  - Copies items to "Orders" table
  - Copies charges to "Charges" table
  - Copies dock assignments to "Docks" table
- Set **Staging Area** (required for putaway operations)
- Save the Warehouse Job

#### 3. Allocate Handling Units (Optional)
If items don't have handling units assigned:
- Click **Allocate Handling Units** button
- System creates handling units based on:
  - Handling Unit Type from items
  - Capacity limits
  - Available handling units
- Items are assigned to handling units
- Items may be split if capacity is exceeded

#### 4. Allocate Putaway
- Click **Allocate Putaway** button
- System creates putaway allocation rows in "Items" table:
  - Determines optimal storage locations based on:
    - Storage type restrictions
    - Capacity availability
    - Allocation policies (FIFO, LIFO, etc.)
    - Handling unit anchoring (one HU → one location)
  - Assigns destination locations
  - Validates capacity limits
- Review allocation results and warnings

#### 5. Post Receiving
- Click **Post Receiving** button
- System creates stock ledger entries:
  - **IN** to Staging Area (+quantity)
  - Marks items as "receiving_posted"
- Updates:
  - Storage Location status
  - Handling Unit status
  - Stock balances

#### 6. Post Putaway
- Click **Post Putaway** button
- System creates stock ledger entries:
  - **OUT** from Staging Area (-quantity)
  - **IN** to Destination Location (+quantity)
  - Marks items as "putaway_posted"
- Validates capacity limits before posting
- Updates:
  - Storage Location status and occupancy
  - Handling Unit status and location
  - Stock balances

### Key Validations
- Staging area must be set
- Handling units must be assigned (for HU-anchored putaway)
- Destination locations must have capacity
- Storage type restrictions must be satisfied
- One handling unit can only go to one destination location

---

## Pick Process (Outbound)

The Pick process handles retrieving goods from storage and preparing them for shipping.

### Step-by-Step Process

#### 1. Create Release Order
- Navigate to **Release Order**
- Enter customer, contract, dates, and priority
- Add items with:
  - Item code
  - Quantity and UOM
  - Source location (optional, system can allocate)
  - Handling Unit (if known)
  - Batch/Serial numbers (if applicable)
- Add dock door assignments
- Add charges if applicable
- Save the Release Order

#### 2. Create Warehouse Job (Pick)
- From Release Order, click **Create > Warehouse Job**
- The system automatically:
  - Sets job type to "Pick"
  - Links reference order to Release Order
  - Copies items to "Orders" table
  - Copies charges and docks
- Set **Staging Area** (required for pick operations)
- Save the Warehouse Job

#### 3. Allocate Pick
- Click **Allocate Pick** button
- System creates pick allocation rows in "Items" table:
  - Determines source locations based on:
    - Item availability
    - Allocation policies (FIFO, LIFO, etc.)
    - Location preferences
  - Assigns source locations
  - May split items across multiple locations if needed
- Review allocation results

#### 4. Post Pick
- Click **Post Pick** button
- System creates stock ledger entries:
  - **OUT** from Source Location (-quantity)
  - **IN** to Staging Area (+quantity)
  - Marks items as "pick_posted"
- Updates:
  - Storage Location status and occupancy
  - Handling Unit status
  - Stock balances

#### 5. Post Release
- Click **Post Release** button
- System creates stock ledger entries:
  - **OUT** from Staging Area (-quantity)
  - Marks items as "release_posted"
- Updates:
  - Storage Location status
  - Handling Unit status (marks as released)
  - Stock balances

### Key Validations
- Staging area must be set
- Sufficient stock must be available at source locations
- Items must be allocated before posting

---

## Transfer Process

The Transfer process moves goods between locations within the warehouse.

### Step-by-Step Process

#### 1. Create Transfer Order
- Navigate to **Transfer Order**
- Select transfer type (Internal, Customer, Others)
- Enter customer if applicable
- Select reason (Re-slot, Re-org, Staging, Quality, Quarantine, Returns, Others)
- Add items with:
  - Item code
  - Quantity
  - Source location
  - Destination location (optional, can be allocated)
- Save the Transfer Order

#### 2. Create Warehouse Job (Move)
- From Transfer Order, click **Create > Warehouse Job**
- System sets job type to "Move"
- Copies items to job
- Set **Staging Area** if needed
- Save the Warehouse Job

#### 3. Allocate Move
- Click **Allocate Move** button
- System creates move allocation rows:
  - Validates source locations have stock
  - Allocates destination locations if not specified
  - Creates pick and putaway rows

#### 4. Post Move
- Click **Post Move** button
- System creates stock ledger entries:
  - **OUT** from Source Location
  - **IN** to Destination Location
- Updates stock balances and location occupancy

---

## VAS (Value Added Services) Process

The VAS process performs value-added services on stored goods (e.g., labeling, repacking, kitting).

### Step-by-Step Process

#### 1. Create VAS Order
- Navigate to **VAS Order**
- Select VAS Order Type
- Enter customer, contract, dates
- Add items requiring VAS
- Add VAS inputs (service-specific data)
- Save the VAS Order

#### 2. Create Warehouse Job (VAS)
- From VAS Order, click **Create > Warehouse Job**
- System sets job type to "VAS"
- Links VAS Order Type
- Copies items and VAS inputs
- Set **Staging Area**
- Save the Warehouse Job

#### 3. Allocate VAS
- Click **Allocate VAS** button
- System:
  - Creates pick rows to retrieve items from storage
  - Creates VAS processing rows
  - Creates putaway rows to return items to storage (or staging for release)

#### 4. Execute VAS Operations
- Post pick operations to retrieve items
- Perform VAS services (may involve manual steps)
- Post putaway operations to return items

---

## Stocktake Process

The Stocktake process counts and verifies inventory accuracy.

### Step-by-Step Process

#### 1. Create Stocktake Order
- Navigate to **Stocktake Order**
- Select type (Full, Cycle, Blind, Investigative, Ad-hoc)
- Select scope (Site, Building, Zone, Aisle, Bay, Level)
- Set Blind Count flag (operators don't see system quantities)
- Set QA Required flag
- Configure stocktake days past zero
- Save the Stocktake Order

#### 2. Create Warehouse Job (Stocktake)
- From Stocktake Order, click **Create > Warehouse Job**
- System sets job type to "Stocktake"
- Copies stocktake configuration
- Set **Count Date**
- Save the Warehouse Job

#### 3. Generate Count Sheet
- System generates count rows based on:
  - Scope (location hierarchy)
  - Items at those locations
  - Stocktake type and settings

#### 4. Perform Counts
- Operators count items at locations
- Enter counted quantities
- System compares with expected quantities
- Flags variances

#### 5. Review and Adjust
- Review count results
- Investigate variances
- Create adjustments if needed
- Complete stocktake

---

## Key Concepts

### Staging Area
A designated storage location used as an intermediate holding area:
- **Putaway**: Goods arrive at staging, then move to storage
- **Pick**: Goods move from storage to staging, then ship out
- Required for all warehouse jobs

### Handling Units
Physical containers that hold items:
- Can be pallets, boxes, crates, etc.
- Have capacity limits (volume, weight)
- Can be tracked through warehouse
- In putaway: One HU typically goes to one destination location

### Stock Ledger
Real-time record of all inventory movements:
- Tracks quantity changes at each location
- Records handling unit movements
- Maintains batch and serial number tracking
- Updates location occupancy

### Allocation Policies
Rules for selecting source/destination locations:
- **FIFO** (First In, First Out)
- **LIFO** (Last In, First Out)
- **Location Preference**
- **Capacity Optimization**

### Capacity Management
System tracks and enforces:
- Volume capacity per location
- Weight capacity per location
- Handling unit capacity
- Prevents exceeding limits (configurable)

### Storage Type Restrictions
Items may be restricted to specific storage types:
- Temperature requirements
- Security requirements
- Compliance requirements
- System validates during allocation

---

## Workflow Summary

### Inbound Flow (Putaway)
```
Inbound Order
    ↓
Warehouse Job (Putaway)
    ↓
Allocate Handling Units (if needed)
    ↓
Allocate Putaway (assign storage locations)
    ↓
Post Receiving (items IN to staging)
    ↓
Post Putaway (items OUT from staging, IN to storage)
```

### Outbound Flow (Pick)
```
Release Order
    ↓
Warehouse Job (Pick)
    ↓
Allocate Pick (assign source locations)
    ↓
Post Pick (items OUT from storage, IN to staging)
    ↓
Post Release (items OUT from staging)
```

### Transfer Flow (Move)
```
Transfer Order
    ↓
Warehouse Job (Move)
    ↓
Allocate Move (assign source and destination)
    ↓
Post Move (items OUT from source, IN to destination)
```

### VAS Flow
```
VAS Order
    ↓
Warehouse Job (VAS)
    ↓
Allocate VAS (pick items, process, putaway)
    ↓
Post Pick → Perform VAS → Post Putaway
```

### Stocktake Flow
```
Stocktake Order
    ↓
Warehouse Job (Stocktake)
    ↓
Generate Count Sheet
    ↓
Perform Counts
    ↓
Review Variances → Adjust if needed
```

---

## Additional Features

### Dock Door Management
- Assign dock doors to orders
- Track vehicle arrivals (ETA, plate numbers)
- Link dock doors to warehouse jobs
- Support for inbound and outbound docks

### Charges and Billing
- Track charges for warehouse operations
- Link charges to warehouse jobs
- Support for periodic billing (storage charges)
- Volume-based billing options

### Operations Tracking
- Record warehouse operations (putaway, pick, move)
- Track operation start/end times
- Link operations to warehouse jobs
- Support for productivity analysis

### Sustainability Tracking
- Track energy consumption
- Monitor waste generation
- Calculate carbon footprint
- Support for green certifications

### SLA Management
- Set service level targets
- Track SLA status
- Monitor target dates
- Record SLA notes

---

## Best Practices

1. **Always set staging area** before posting operations
2. **Validate allocations** before posting to catch errors early
3. **Use handling units** for better tracking and organization
4. **Review capacity** before putaway to avoid over-allocation
5. **Complete operations in sequence**: Receiving → Putaway, Pick → Release
6. **Monitor stock ledger** for real-time inventory visibility
7. **Use appropriate allocation policies** based on business needs
8. **Regular stocktakes** to maintain inventory accuracy
9. **Track operations** for performance analysis
10. **Maintain dock schedules** for efficient receiving/shipping

---

## Troubleshooting

### Common Issues

**Issue**: Cannot post receiving/putaway
- **Solution**: Ensure staging area is set on warehouse job

**Issue**: Allocation fails with capacity errors
- **Solution**: Check location capacity limits, reduce quantities, or use additional locations

**Issue**: Handling unit validation errors
- **Solution**: Ensure one handling unit goes to one destination in putaway

**Issue**: Stock not available for pick
- **Solution**: Verify stock exists at source locations, check item availability

**Issue**: Storage type restriction violations
- **Solution**: Review item storage type requirements and location assignments

---

*This documentation covers the complete warehouse management process. For specific field-level details, refer to the individual DocType documentation.*
