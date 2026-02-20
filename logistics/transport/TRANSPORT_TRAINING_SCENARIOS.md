# Transport Module Training Scenarios

## Overview
This document contains 5 training scenarios for the Transport Module. All scenarios use **only existing master files** and do not require creating transport orders, jobs, or transactions. These exercises focus on setting up and managing master data.

---

## Scenario 1: Setting Up a New Transport Company and Vehicle Fleet

### Objective
Create a complete setup for a new transport company with vehicles, drivers, and supporting master data.

### Prerequisites
- Access to Transport Module
- Basic understanding of master files

### Steps

#### Step 1: Create Transport Company
1. Navigate to **Transport > Master Files > Transport Company**
2. Click **New**
3. Fill in the following details:
   - **Full Name**: "ABC Logistics Pte Ltd"
   - **Supplier**: Create or select an existing Supplier (e.g., "ABC-LOG-SUP")
   - **Customer**: Leave blank (if not applicable)
   - **Company Owned**: Check this box (if it's your company's fleet)
4. Click **Save**

#### Step 2: Create Terminal Type
1. Navigate to **Transport > Settings > Terminal Type**
2. Click **New**
3. Create the following terminal types:
   - **Code**: "WAREHOUSE", **Description**: "Warehouse Terminal"
   - **Code**: "DISTRIBUTION", **Description**: "Distribution Center"
   - **Code**: "CROSSDOCK", **Description**: "Cross-dock Facility"
4. Save each terminal type

#### Step 3: Create Terminals
1. Navigate to **Transport > Settings > Terminal**
2. Click **New**
3. Create terminals:
   - **Code**: "WH-SG-01"
     - **Description**: "Singapore Main Warehouse"
     - **Terminal Type**: "WAREHOUSE"
     - **Primary Address**: Create/select address in Singapore
   - **Code**: "DC-KL-01"
     - **Description**: "Kuala Lumpur Distribution Center"
     - **Terminal Type**: "DISTRIBUTION"
     - **Primary Address**: Create/select address in Kuala Lumpur
4. Save each terminal

#### Step 4: Create Transport Zones
1. Navigate to **Transport > Settings > Zone**
2. Click **New**
3. Create zones:
   - **Code**: "SG-CENTRAL"
     - **Zone Name**: "Singapore Central"
     - **Description**: "Central Singapore delivery zone"
     - **Country**: "Singapore"
     - **City**: "Singapore"
   - **Code**: "MY-SELANGOR"
     - **Zone Name**: "Selangor"
     - **Description**: "Selangor state coverage"
     - **Country**: "Malaysia"
     - **State**: "Selangor"
4. Save each zone

#### Step 5: Create Transport Vehicles
1. Navigate to **Transport > Master Files > Vehicle**
2. Click **New**
3. Create vehicles:
   - **Code**: "TRUCK-001"
     - **Vehicle Name**: "Delivery Truck 001"
     - **Vehicle Type**: Select/create appropriate vehicle type
     - **Company Owned**: Checked
     - **Make**: Select/create vehicle make (e.g., "Isuzu")
     - **Model**: "NPR 400"
     - **Base Facility**: "WH-SG-01"
     - **License Plate Number**: "SGB1234A"
     - **Capacity Tab**:
       - **Capacity Weight**: 3500 (kg)
       - **Capacity Volume**: 25 (CBM)
       - **Capacity Pallets**: 12
     - **Routing Tab**:
       - **Service Zones**: Add "SG-CENTRAL"
       - **Avg Speed**: 50 (km/h)
       - **Cost per km**: 1.50
       - **Cost per hour**: 25.00
   - **Code**: "VAN-002"
     - **Vehicle Name**: "Express Van 002"
     - **Vehicle Type**: Select/create appropriate vehicle type
     - **Company Owned**: Checked
     - **Make**: "Toyota"
     - **Model**: "Hiace"
     - **Base Facility**: "WH-SG-01"
     - **License Plate Number**: "SGB5678B"
     - **Capacity Tab**:
       - **Capacity Weight**: 1000 (kg)
       - **Capacity Volume**: 8 (CBM)
       - **Capacity Pallets**: 4
     - **Routing Tab**:
       - **Service Zones**: Add "SG-CENTRAL"
       - **Avg Speed**: 45 (km/h)
       - **Cost per km**: 0.80
       - **Cost per hour**: 20.00
4. Save each vehicle

#### Step 6: Create Drivers
1. Navigate to **Transport > Master Files > Driver**
2. Click **New**
3. Create drivers:
   - **Full Name**: "John Tan"
     - **Status**: "Active"
     - **Cell Number**: "+65 9123 4567"
     - **License Number**: "D1234567X"
     - **Expiry Date**: Set to future date (e.g., 2 years from today)
     - **Transport Tab**:
       - **Is Internal**: Checked
       - **Default Vehicle**: "TRUCK-001"
   - **Full Name**: "Ahmad Bin Hassan"
     - **Status**: "Active"
     - **Cell Number**: "+65 9876 5432"
     - **License Number**: "D7654321Y"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Checked
       - **Default Vehicle**: "VAN-002"
4. Save each driver

#### Step 7: Create Dispatchers
1. Navigate to **Transport > Master Files > Dispatcher**
2. Click **New**
3. Create dispatchers:
   - **Employee**: Select/create employee "Sarah Lim"
     - **Terminal**: "WH-SG-01"
   - **Employee**: Select/create employee "David Wong"
     - **Terminal**: "DC-KL-01"
4. Save each dispatcher

### Expected Outcome
- 1 Transport Company created
- 3 Terminal Types created
- 2 Terminals created
- 2 Transport Zones created
- 2 Transport Vehicles created with capacity and routing information
- 2 Drivers created and linked to vehicles
- 2 Dispatchers created and assigned to terminals

### Verification Checklist
- [ ] All master records are saved successfully
- [ ] Vehicles are linked to correct base facilities
- [ ] Drivers are assigned default vehicles
- [ ] Dispatchers are assigned to terminals
- [ ] Service zones are assigned to vehicles

---

## Scenario 2: Setting Up Load Types and Pick & Drop Modes

### Objective
Configure load types and pick & drop modes to support different transport operations.

### Prerequisites
- Completed Scenario 1 (optional, but helpful)

### Steps

#### Step 1: Create Load Types
1. Navigate to **Transport > Master Files > Load Type** (if available) or check existing load types
2. Click **New**
3. Create the following load types:
   - **Load Type Name**: "STANDARD"
     - **Description**: "Standard cargo load"
     - **Transport**: Checked
     - **Can be Consolidated**: Checked
     - **Can handle Consolidation**: Checked
     - **Max Consolidation Jobs**: 10
     - **Max Weight (kg)**: 5000
     - **Max Volume (m³)**: 50
     - **Allowed Transport Job Types**:
       - **Non-Container**: Checked
   - **Load Type Name**: "REEFER"
     - **Description**: "Refrigerated cargo"
     - **Transport**: Checked
     - **Can be Consolidated**: Unchecked
     - **Can handle Consolidation**: Unchecked
     - **Allowed Transport Job Types**:
       - **Special**: Checked
   - **Load Type Name**: "HAZMAT"
     - **Description**: "Hazardous materials"
     - **Transport**: Checked
     - **Can be Consolidated**: Unchecked
     - **Can handle Consolidation**: Unchecked
     - **Allowed Transport Job Types**:
       - **Special**: Checked
   - **Load Type Name**: "OVERSIZED"
     - **Description**: "Oversized cargo"
     - **Transport**: Checked
     - **Can be Consolidated**: Unchecked
     - **Can handle Consolidation**: Unchecked
     - **Allowed Transport Job Types**:
       - **Oversized**: Checked
4. Save each load type

#### Step 2: Create Pick and Drop Modes
1. Navigate to **Transport > Master Files > Pick and Drop Mode**
2. Click **New**
3. Create the following modes:
   - **Code**: "DOOR_DOOR"
     - **Description**: "Door to Door Service"
     - **Usage**: "Full pickup and delivery service"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Checked
     - **With Equipment**: Unchecked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 15
       - **Loading Time Calculation Method**: "Volume-Based"
       - **Loading Time per m³ (minutes)**: 5
       - **Base Unloading Time (minutes)**: 15
       - **Unloading Time Calculation Method**: "Volume-Based"
       - **Unloading Time per m³ (minutes)**: 5
   - **Code**: "TERMINAL_TERMINAL"
     - **Description**: "Terminal to Terminal"
     - **Usage**: "Terminal-based service"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Checked
     - **With Equipment**: Unchecked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 10
       - **Loading Time Calculation Method**: "Fixed Time"
       - **Base Unloading Time (minutes)**: 10
       - **Unloading Time Calculation Method**: "Fixed Time"
   - **Code**: "DOOR_TERMINAL"
     - **Description**: "Door to Terminal"
     - **Usage**: "Pickup from customer, deliver to terminal"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Checked
     - **With Equipment**: Unchecked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 20
       - **Loading Time Calculation Method**: "Volume and Weight Combined"
       - **Loading Time per m³ (minutes)**: 5
       - **Loading Time per 100kg (minutes)**: 2
       - **Base Unloading Time (minutes)**: 10
       - **Unloading Time Calculation Method**: "Fixed Time"
   - **Code**: "TERMINAL_DOOR"
     - **Description**: "Terminal to Door"
     - **Usage**: "Pickup from terminal, deliver to customer"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Checked
     - **With Equipment**: Unchecked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 10
       - **Loading Time Calculation Method**: "Fixed Time"
       - **Base Unloading Time (minutes)**: 20
       - **Unloading Time Calculation Method**: "Volume and Weight Combined"
       - **Unloading Time per m³ (minutes)**: 5
       - **Unloading Time per 100kg (minutes)**: 2
   - **Code**: "PICKUP_ONLY"
     - **Description**: "Pickup Only Service"
     - **Usage**: "Collection service only"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Unchecked
     - **With Equipment**: Unchecked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 15
       - **Loading Time Calculation Method**: "Volume-Based"
       - **Loading Time per m³ (minutes)**: 5
   - **Code**: "DELIVERY_ONLY"
     - **Description**: "Delivery Only Service"
     - **Usage**: "Delivery service only"
     - **Allow in Pick**: Unchecked
     - **Allow in Drop**: Checked
     - **With Equipment**: Unchecked
     - **Loading and Unloading Time Tab**:
       - **Base Unloading Time (minutes)**: 15
       - **Unloading Time Calculation Method**: "Volume-Based"
       - **Unloading Time per m³ (minutes)**: 5
4. Save each pick and drop mode

### Expected Outcome
- 4 Load Types created (STANDARD, REEFER, HAZMAT, OVERSIZED)
- 6 Pick and Drop Modes created with different loading/unloading time configurations

### Verification Checklist
- [ ] All load types have appropriate consolidation settings
- [ ] Load types have correct transport job type flags
- [ ] Pick and drop modes have correct allow_in_pick and allow_in_drop settings
- [ ] Loading and unloading time calculations are configured appropriately
- [ ] All records are saved successfully

---

## Scenario 3: Setting Up External Transport Company and Third-Party Vehicles

### Objective
Configure external transport companies and their vehicles for outsourcing transport operations.

### Prerequisites
- Basic understanding of transport companies

### Steps

#### Step 1: Create External Transport Companies
1. Navigate to **Transport > Master Files > Transport Company**
2. Click **New**
3. Create external transport companies:
   - **Full Name**: "XYZ Transport Services"
     - **Supplier**: Create/select supplier "XYZ-TRANS-SUP"
     - **Customer**: Leave blank
     - **Company Owned**: Unchecked
   - **Full Name**: "Fast Movers Logistics"
     - **Supplier**: Create/select supplier "FAST-MOVERS-SUP"
     - **Customer**: Leave blank
     - **Company Owned**: Unchecked
   - **Full Name**: "Cold Chain Specialists"
     - **Supplier**: Create/select supplier "COLD-CHAIN-SUP"
     - **Customer**: Leave blank
     - **Company Owned**: Unchecked
4. Save each transport company

#### Step 2: Create Additional Terminals for External Companies
1. Navigate to **Transport > Settings > Terminal**
2. Click **New**
3. Create terminals:
   - **Code**: "EXT-WH-01"
     - **Description**: "XYZ Transport Warehouse"
     - **Terminal Type**: "WAREHOUSE"
     - **Primary Address**: Create/select appropriate address
   - **Code**: "EXT-DC-01"
     - **Description**: "Fast Movers Distribution Center"
     - **Terminal Type**: "DISTRIBUTION"
     - **Primary Address**: Create/select appropriate address
4. Save each terminal

#### Step 3: Create External Transport Vehicles
1. Navigate to **Transport > Master Files > Vehicle**
2. Click **New**
3. Create vehicles for external companies:
   - **Code**: "EXT-TRUCK-001"
     - **Vehicle Name**: "XYZ Transport Truck 001"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Unchecked
     - **Transport Company**: "XYZ Transport Services"
     - **Make**: "Mercedes"
     - **Model**: "Actros"
     - **Base Facility**: "EXT-WH-01"
     - **License Plate Number**: "SGC9999X"
     - **Capacity Tab**:
       - **Capacity Weight**: 5000 (kg)
       - **Capacity Volume**: 35 (CBM)
       - **Capacity Pallets**: 15
     - **Routing Tab**:
       - **Service Zones**: Add multiple zones as needed
       - **Avg Speed**: 55 (km/h)
       - **Cost per km**: 2.00
       - **Cost per hour**: 30.00
   - **Code**: "EXT-REEFER-001"
     - **Vehicle Name**: "Cold Chain Reefer 001"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Unchecked
     - **Transport Company**: "Cold Chain Specialists"
     - **Make**: "Isuzu"
     - **Model**: "FRR 600"
     - **Base Facility**: Create/select appropriate terminal
     - **License Plate Number**: "SGC8888Y"
     - **Capacity Tab**:
       - **Capacity Weight**: 3000 (kg)
       - **Capacity Volume**: 20 (CBM)
       - **Capacity Pallets**: 10
     - **Reefer Settings**:
       - **Reefer**: Checked
       - **Minimum Temp**: -20 (°C)
       - **Maximum Temp**: 5 (°C)
     - **Routing Tab**:
       - **Service Zones**: Add zones as needed
       - **Avg Speed**: 50 (km/h)
       - **Cost per km**: 2.50
       - **Cost per hour**: 35.00
   - **Code**: "EXT-VAN-001"
     - **Vehicle Name**: "Fast Movers Express Van"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Unchecked
     - **Transport Company**: "Fast Movers Logistics"
     - **Make**: "Ford"
     - **Model**: "Transit"
     - **Base Facility**: "EXT-DC-01"
     - **License Plate Number**: "SGC7777Z"
     - **Capacity Tab**:
       - **Capacity Weight**: 1200 (kg)
       - **Capacity Volume**: 9 (CBM)
       - **Capacity Pallets**: 5
     - **Routing Tab**:
       - **Service Zones**: Add zones as needed
       - **Avg Speed**: 50 (km/h)
       - **Cost per km**: 1.00
       - **Cost per hour**: 22.00
4. Save each vehicle

#### Step 4: Create External Drivers
1. Navigate to **Transport > Master Files > Driver**
2. Click **New**
3. Create drivers for external companies:
   - **Full Name**: "Raj Kumar"
     - **Status**: "Active"
     - **Cell Number**: "+65 9111 2222"
     - **License Number**: "D1111111A"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Unchecked
       - **Transport Company**: "XYZ Transport Services"
       - **Default Vehicle**: "EXT-TRUCK-001"
   - **Full Name**: "Lee Wei Ming"
     - **Status**: "Active"
     - **Cell Number**: "+65 9333 4444"
     - **License Number**: "D2222222B"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Unchecked
       - **Transport Company**: "Fast Movers Logistics"
       - **Default Vehicle**: "EXT-VAN-001"
   - **Full Name**: "Mohammed Ali"
     - **Status**: "Active"
     - **Cell Number**: "+65 9555 6666"
     - **License Number**: "D3333333C"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Unchecked
       - **Transport Company**: "Cold Chain Specialists"
       - **Default Vehicle**: "EXT-REEFER-001"
       - **HazMat Endorsement**: Checked (if applicable)
4. Save each driver

### Expected Outcome
- 3 External Transport Companies created (Company Owned = No)
- 2 Additional Terminals created
- 3 External Transport Vehicles created (linked to external companies)
- 3 External Drivers created (linked to external companies and vehicles)
- 1 Reefer vehicle configured with temperature settings

### Verification Checklist
- [ ] All external transport companies have Company Owned = No
- [ ] Vehicles are correctly linked to external transport companies
- [ ] Drivers are correctly linked to external transport companies
- [ ] Reefer vehicle has temperature settings configured
- [ ] All capacity and routing information is properly set

---

## Scenario 4: Expanding Transport Network with Multiple Zones and Terminals

### Objective
Set up a comprehensive transport network covering multiple geographic areas with appropriate zones and terminals.

### Prerequisites
- Understanding of zones and terminals

### Steps

#### Step 1: Create Additional Terminal Types
1. Navigate to **Transport > Settings > Terminal Type**
2. Click **New**
3. Create additional terminal types:
   - **Code**: "HUB", **Description**: "Transport Hub"
   - **Code**: "DEPOT", **Description**: "Vehicle Depot"
   - **Code**: "TRANSIT", **Description**: "Transit Point"
4. Save each terminal type

#### Step 2: Create Comprehensive Terminal Network
1. Navigate to **Transport > Settings > Terminal**
2. Click **New**
3. Create terminals for different locations:
   - **Code**: "HUB-SG-01"
     - **Description**: "Singapore Central Hub"
     - **Terminal Type**: "HUB"
     - **Primary Address**: Create/select address in central Singapore
   - **Code**: "WH-JB-01"
     - **Description**: "Johor Bahru Warehouse"
     - **Terminal Type**: "WAREHOUSE"
     - **Primary Address**: Create/select address in Johor Bahru, Malaysia
   - **Code**: "DC-PG-01"
     - **Description**: "Penang Distribution Center"
     - **Terminal Type**: "DISTRIBUTION"
     - **Primary Address**: Create/select address in Penang, Malaysia
   - **Code**: "DEPOT-KL-01"
     - **Description**: "Kuala Lumpur Vehicle Depot"
     - **Terminal Type**: "DEPOT"
     - **Primary Address**: Create/select address in Kuala Lumpur
   - **Code**: "TRANSIT-IPOH-01"
     - **Description**: "Ipoh Transit Point"
     - **Terminal Type**: "TRANSIT"
     - **Primary Address**: Create/select address in Ipoh, Malaysia
4. Save each terminal

#### Step 3: Create Comprehensive Zone Network
1. Navigate to **Transport > Settings > Zone**
2. Click **New**
3. Create zones for different areas:
   - **Code**: "SG-NORTH"
     - **Zone Name**: "Singapore North"
     - **Description**: "Northern Singapore delivery zone"
     - **Country**: "Singapore"
     - **City**: "Singapore"
   - **Code**: "SG-SOUTH"
     - **Zone Name**: "Singapore South"
     - **Description**: "Southern Singapore delivery zone"
     - **Country**: "Singapore"
     - **City**: "Singapore"
   - **Code**: "SG-EAST"
     - **Zone Name**: "Singapore East"
     - **Description**: "Eastern Singapore delivery zone"
     - **Country**: "Singapore"
     - **City**: "Singapore"
   - **Code**: "SG-WEST"
     - **Zone Name**: "Singapore West"
     - **Description**: "Western Singapore delivery zone"
     - **Country**: "Singapore"
     - **City**: "Singapore"
   - **Code**: "MY-JOHOR"
     - **Zone Name**: "Johor"
     - **Description**: "Johor state coverage"
     - **Country**: "Malaysia"
     - **State**: "Johor"
   - **Code**: "MY-PENANG"
     - **Zone Name**: "Penang"
     - **Description**: "Penang state coverage"
     - **Country**: "Malaysia"
     - **State**: "Penang"
   - **Code**: "MY-PERAK"
     - **Zone Name**: "Perak"
     - **Description**: "Perak state coverage"
     - **Country**: "Malaysia"
     - **State**: "Perak"
4. Save each zone

#### Step 4: Create Vehicles for Different Zones
1. Navigate to **Transport > Master Files > Vehicle**
2. Click **New**
3. Create vehicles assigned to different zones:
   - **Code**: "TRUCK-NORTH-01"
     - **Vehicle Name**: "North Zone Truck 01"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Checked
     - **Make**: "Isuzu"
     - **Model**: "NPR 400"
     - **Base Facility**: "HUB-SG-01"
     - **License Plate Number**: "SGN1111A"
     - **Capacity Tab**: Configure as needed
     - **Routing Tab**:
       - **Service Zones**: Add "SG-NORTH"
       - **Avg Speed**: 50 (km/h)
   - **Code**: "TRUCK-SOUTH-01"
     - **Vehicle Name**: "South Zone Truck 01"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Checked
     - **Make**: "Isuzu"
     - **Model**: "NPR 400"
     - **Base Facility**: "HUB-SG-01"
     - **License Plate Number**: "SGS2222B"
     - **Capacity Tab**: Configure as needed
     - **Routing Tab**:
       - **Service Zones**: Add "SG-SOUTH"
       - **Avg Speed**: 50 (km/h)
   - **Code**: "TRUCK-JB-01"
     - **Vehicle Name**: "Johor Bahru Truck 01"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Checked
     - **Make**: "Isuzu"
     - **Model**: "NPR 400"
     - **Base Facility**: "WH-JB-01"
     - **License Plate Number**: "JHM3333C"
     - **Capacity Tab**: Configure as needed
     - **Routing Tab**:
       - **Service Zones**: Add "MY-JOHOR"
       - **Avg Speed**: 60 (km/h)
4. Save each vehicle

#### Step 5: Assign Dispatchers to New Terminals
1. Navigate to **Transport > Master Files > Dispatcher**
2. Click **New**
3. Create dispatchers for new terminals:
   - **Employee**: Select/create employee for "HUB-SG-01"
     - **Terminal**: "HUB-SG-01"
   - **Employee**: Select/create employee for "WH-JB-01"
     - **Terminal**: "WH-JB-01"
   - **Employee**: Select/create employee for "DC-PG-01"
     - **Terminal**: "DC-PG-01"
4. Save each dispatcher

### Expected Outcome
- 3 Additional Terminal Types created (HUB, DEPOT, TRANSIT)
- 5 New Terminals created across different locations
- 7 Transport Zones created (4 Singapore zones + 3 Malaysia zones)
- 3 Vehicles created and assigned to specific zones
- 3 Dispatchers assigned to new terminals

### Verification Checklist
- [ ] Terminal types are appropriate for their use cases
- [ ] Terminals are created in different geographic locations
- [ ] Zones cover all required service areas
- [ ] Vehicles are assigned to correct base facilities
- [ ] Vehicles have appropriate service zones assigned
- [ ] Dispatchers are assigned to terminals

---

## Scenario 5: Specialized Vehicle and Driver Setup

### Objective
Set up specialized vehicles (reefer, container carriers, oversized) and drivers with special qualifications.

### Prerequisites
- Understanding of vehicle types and driver qualifications

### Steps

#### Step 1: Create Specialized Transport Vehicles
1. Navigate to **Transport > Master Files > Vehicle**
2. Click **New**
3. Create specialized vehicles:
   - **Code**: "REEFER-001"
     - **Vehicle Name**: "Reefer Unit 001"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Checked
     - **Make**: "Isuzu"
     - **Model**: "FRR 600"
     - **Base Facility**: Select appropriate terminal
     - **License Plate Number**: "SGR1111A"
     - **Capacity Tab**:
       - **Capacity Weight**: 3000 (kg)
       - **Capacity Volume**: 20 (CBM)
       - **Capacity Pallets**: 10
     - **Reefer Settings**:
       - **Reefer**: Checked
       - **Minimum Temp**: -25 (°C)
       - **Maximum Temp**: 10 (°C)
     - **Routing Tab**:
       - **Service Zones**: Add zones as needed
       - **Avg Speed**: 50 (km/h)
       - **Cost per km**: 2.50
       - **Cost per hour**: 35.00
   - **Code**: "CONTAINER-001"
     - **Vehicle Name**: "Container Carrier 001"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Checked
     - **Make**: "Volvo"
     - **Model**: "FH16"
     - **Base Facility**: Select appropriate terminal
     - **License Plate Number**: "SGC2222B"
     - **Capacity Tab**:
       - **Capacity Weight**: 20000 (kg)
       - **Can Carry Container**: Checked
       - **Max Container Count**: 1
       - **Container Types**: Add appropriate container types
     - **Routing Tab**:
       - **Service Zones**: Add zones as needed
       - **Avg Speed**: 55 (km/h)
       - **Cost per km**: 3.00
       - **Cost per hour**: 40.00
   - **Code**: "OVERSIZED-001"
     - **Vehicle Name**: "Oversized Cargo Truck 001"
     - **Vehicle Type**: Select/create appropriate type
     - **Company Owned**: Checked
     - **Make**: "Scania"
     - **Model**: "R730"
     - **Base Facility**: Select appropriate terminal
     - **License Plate Number**: "SGO3333C"
     - **Capacity Tab**:
       - **Capacity Weight**: 30000 (kg)
       - **Capacity Volume**: 60 (CBM)
       - **Capacity Pallets**: 20
     - **Routing Tab**:
       - **Service Zones**: Add zones as needed
       - **Avg Speed**: 40 (km/h)
       - **Cost per km**: 4.00
       - **Cost per hour**: 50.00
4. Save each vehicle

#### Step 2: Create Specialized Drivers
1. Navigate to **Transport > Master Files > Driver**
2. Click **New**
3. Create drivers with special qualifications:
   - **Full Name**: "Robert Chen"
     - **Status**: "Active"
     - **Cell Number**: "+65 9123 1111"
     - **License Number**: "D1111111R"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Checked
       - **Default Vehicle**: "REEFER-001"
   - **Full Name**: "Michael Tan"
     - **Status**: "Active"
     - **Cell Number**: "+65 9123 2222"
     - **License Number**: "D2222222C"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Checked
       - **Default Vehicle**: "CONTAINER-001"
   - **Full Name**: "James Lee"
     - **Status**: "Active"
     - **Cell Number**: "+65 9123 3333"
     - **License Number**: "D3333333O"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Checked
       - **Default Vehicle**: "OVERSIZED-001"
   - **Full Name**: "Peter Wong"
     - **Status**: "Active"
     - **Cell Number**: "+65 9123 4444"
     - **License Number**: "D4444444H"
     - **Expiry Date**: Set to future date
     - **Transport Tab**:
       - **Is Internal**: Checked
       - **HazMat Endorsement**: Checked
       - **Medical Clearance Expiry**: Set to future date
       - **Default Vehicle**: Select appropriate vehicle
4. Save each driver

#### Step 3: Create Additional Load Types for Specialized Cargo
1. Navigate to **Transport > Master Files > Load Type**
2. Click **New**
3. Create specialized load types:
   - **Load Type Name**: "CONTAINER"
     - **Description**: "Containerized cargo"
     - **Transport**: Checked
     - **Can be Consolidated**: Unchecked
     - **Can handle Consolidation**: Unchecked
     - **Allowed Transport Job Types**:
       - **Container**: Checked
   - **Load Type Name**: "FROZEN"
     - **Description**: "Frozen cargo requiring reefer"
     - **Transport**: Checked
     - **Can be Consolidated**: Unchecked
     - **Can handle Consolidation**: Unchecked
     - **Allowed Transport Job Types**:
       - **Special**: Checked
   - **Load Type Name**: "CHILLED"
     - **Description**: "Chilled cargo requiring temperature control"
     - **Transport**: Checked
     - **Can be Consolidated**: Checked (with restrictions)
     - **Can handle Consolidation**: Checked
     - **Max Consolidation Jobs**: 5
     - **Allowed Transport Job Types**:
       - **Special**: Checked
4. Save each load type

#### Step 4: Create Specialized Pick and Drop Modes
1. Navigate to **Transport > Master Files > Pick and Drop Mode**
2. Click **New**
3. Create specialized modes:
   - **Code**: "REEFER_DOOR_DOOR"
     - **Description**: "Reefer Door to Door"
     - **Usage**: "Temperature-controlled door to door service"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Checked
     - **With Equipment**: Checked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 30
       - **Loading Time Calculation Method**: "Volume-Based"
       - **Loading Time per m³ (minutes)**: 8
       - **Base Unloading Time (minutes)**: 30
       - **Unloading Time Calculation Method**: "Volume-Based"
       - **Unloading Time per m³ (minutes)**: 8
   - **Code**: "CONTAINER_TERMINAL"
     - **Description**: "Container Terminal Service"
     - **Usage**: "Container handling at terminals"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Checked
     - **With Equipment**: Checked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 45
       - **Loading Time Calculation Method**: "Fixed Time"
       - **Base Unloading Time (minutes)**: 45
       - **Unloading Time Calculation Method**: "Fixed Time"
   - **Code**: "HAZMAT_DOOR_DOOR"
     - **Description**: "HazMat Door to Door"
     - **Usage**: "Hazardous materials door to door service"
     - **Allow in Pick**: Checked
     - **Allow in Drop**: Checked
     - **With Equipment**: Checked
     - **Loading and Unloading Time Tab**:
       - **Base Loading Time (minutes)**: 40
       - **Loading Time Calculation Method**: "Volume and Weight Combined"
       - **Loading Time per m³ (minutes)**: 10
       - **Loading Time per 100kg (minutes)**: 5
       - **Base Unloading Time (minutes)**: 40
       - **Unloading Time Calculation Method**: "Volume and Weight Combined"
       - **Unloading Time per m³ (minutes)**: 10
       - **Unloading Time per 100kg (minutes)**: 5
4. Save each pick and drop mode

### Expected Outcome
- 3 Specialized Vehicles created (Reefer, Container Carrier, Oversized)
- 4 Specialized Drivers created with appropriate qualifications
- 3 Additional Load Types created (CONTAINER, FROZEN, CHILLED)
- 3 Specialized Pick and Drop Modes created

### Verification Checklist
- [ ] Reefer vehicle has temperature settings configured
- [ ] Container carrier has container capacity settings
- [ ] Oversized vehicle has appropriate capacity settings
- [ ] Drivers are assigned to appropriate specialized vehicles
- [ ] HazMat driver has endorsement and medical clearance
- [ ] Load types have appropriate consolidation and job type settings
- [ ] Pick and drop modes have appropriate loading/unloading time settings
- [ ] Specialized modes have "With Equipment" checked where applicable

---

## Summary

These 5 scenarios cover:
1. **Basic Setup**: Transport company, terminals, zones, vehicles, drivers, dispatchers
2. **Load Types & Modes**: Configuration of load types and pick & drop modes
3. **External Companies**: Setting up third-party transport providers
4. **Network Expansion**: Multi-location terminal and zone setup
5. **Specialized Operations**: Reefer, container, oversized, and HazMat configurations

All scenarios use **only existing master files** and do not require creating transactions or orders. These exercises provide hands-on experience with the transport module's master data setup.

---

## Notes for Trainers

- Ensure trainees have appropriate permissions to create master data
- Verify that prerequisite master data (e.g., Vehicle Types, Vehicle Makes, Employees, Suppliers) exist or can be created
- Encourage trainees to explore field dependencies and relationships
- Review the created master data together to ensure accuracy
- Discuss how these master files are used in actual transport operations

---

## Additional Resources

- Transport Module Documentation
- Master Data Installation Guide
- Vehicle Type and Capacity Settings
- Zone and Terminal Configuration Best Practices
