# Transport Module Process Flow

## Overview
This document describes the complete process flow for the Transport Module in the Logistics application. The flow covers the entire lifecycle from customer order to final delivery and billing.

## Main Process Flow

```
┌─────────────────┐
│ Transport Order │
│   (Customer     │
│    Booking)     │
└────────┬────────┘
         │
         │ Create Transport Job
         ▼
┌─────────────────┐
│ Transport Job   │
│  Status: Draft  │
└────────┬────────┘
         │
         │ Submit
         ▼
┌─────────────────┐
│ Transport Job   │
│ Status: Submitted│
│                 │
│ Creates:        │
│ - Transport Legs│
└────────┬────────┘
         │
         │ Plan & Assign
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Transport Plan  │────▶│   Run Sheet     │
│  (Optional)     │     │ Status: Draft   │
└─────────────────┘     │                 │
                        │ Assigns:        │
                        │ - Vehicle       │
                        │ - Driver        │
                        │ - Transport Legs │
                        └────────┬────────┘
                                 │
                                 │ Submit & Dispatch
                                 ▼
                        ┌─────────────────┐
                        │   Run Sheet     │
                        │Status: Dispatched│
                        └────────┬────────┘
                                 │
                                 │ Start Execution
                                 ▼
                        ┌─────────────────┐
                        │   Run Sheet     │
                        │Status: In-Progress│
                        │                 │
                        │ Transport Legs: │
                        │ - Started      │
                        │ - In Progress  │
                        └────────┬────────┘
                                 │
                                 │ Complete All Legs
                                 ▼
                        ┌─────────────────┐
                        │   Run Sheet     │
                        │Status: Completed│
                        │                 │
                        │ Transport Legs: │
                        │ - Completed    │
                        └────────┬────────┘
                                 │
                                 │ Auto/Manual Billing
                                 ▼
                        ┌─────────────────┐
                        │ Transport Leg   │
                        │Status: Billed   │
                        │                 │
                        │ Sales Invoice   │
                        │   Created       │
                        └─────────────────┘
```

## Detailed Process Steps

### 1. Transport Order (Customer Booking)
**Purpose**: Initial customer request/booking for transport services

**Key Fields**:
- Customer, Booking Date, Scheduled Date
- Transport Job Type (Container/Non-Container/Special/etc.)
- Vehicle Type, Load Type
- Pickup and Delivery Locations
- Packages, Charges

**Status**: Not applicable (submittable document)

**Next Step**: Create Transport Job from Transport Order

---

### 2. Transport Job
**Purpose**: Operational document that manages the execution of transport services

**Status Flow**:
```
Draft → Submitted → In Progress → Completed
```

**Status Details**:
- **Draft**: Job created but not yet submitted
- **Submitted**: Job submitted, ready for planning and assignment
- **In Progress**: At least one Transport Leg is started or in progress
- **Completed**: All Transport Legs are completed

**Key Features**:
- Contains one or more Transport Legs
- Can be created from Transport Order or manually
- Status automatically updates based on leg statuses
- Supports auto-billing when all legs are completed (if enabled)

**Next Step**: Create Transport Legs for each pickup/delivery segment

---

### 3. Transport Leg
**Purpose**: Individual segment of a transport job (from pickup location to delivery location)

**Status Flow**:
```
Open → Assigned → Started → Completed → Billed
```

**Status Details**:
- **Open**: Leg created but not assigned to any Run Sheet
- **Assigned**: Leg assigned to a Run Sheet (vehicle/driver assigned)
- **Started**: Leg execution started (start_date set)
- **Completed**: Leg execution completed (end_date set)
- **Billed**: Sales Invoice created for this leg

**Key Features**:
- Links to Transport Job
- Contains pickup and delivery addresses
- Has time windows (pick_window_start, pick_window_end, drop_window_start, drop_window_end)
- Routing information (distance, duration, route map)
- Telematics integration (ETA, remaining distance/time)
- Carbon footprint calculation
- Auto-updates status based on dates and Run Sheet assignment

**Next Step**: Assign to Run Sheet for execution

---

### 4. Transport Plan (Optional)
**Purpose**: Planning document that groups multiple Run Sheets for a specific date

**Key Features**:
- Groups Run Sheets by plan date
- Assigned to Transport Planner
- Helps in organizing daily/weekly transport operations

**Next Step**: Create Run Sheets within the plan

---

### 5. Run Sheet
**Purpose**: Assignment of vehicle, driver, and multiple Transport Legs for execution

**Status Flow**:
```
Draft → Dispatched → In-Progress → Completed
         (or Hold)              (or Cancelled)
```

**Status Details**:
- **Draft**: Run Sheet created, not yet dispatched
- **Dispatched**: Vehicle dispatched from terminal
- **In-Progress**: Execution started, at least one leg started
- **Hold**: Execution temporarily paused
- **Completed**: All legs completed
- **Cancelled**: Run Sheet cancelled

**Key Features**:
- Assigns Vehicle and Driver
- Contains multiple Transport Legs (optimized route)
- Dispatch and Return terminal information
- Route optimization and mapping
- Estimated and actual completion times
- Links to Transport Consolidation (if applicable)

**Next Step**: Execute the Run Sheet (start Transport Legs)

---

### 6. Trip (Legacy/Optional)
**Purpose**: Execution record for a transport job (older implementation)

**Key Features**:
- Links to Transport Job
- Contains Vehicle, Driver, Transport Company
- Scheduled and Actual start/completion times
- Links to Run Sheet
- Expense tracking

**Note**: May be replaced by Run Sheet in newer implementations

---

### 7. Dispatch
**Purpose**: Dispatch record for trips

**Key Features**:
- Dispatch Date
- Links to Trip
- Terminal and Dispatcher information

---

### 8. Proof of Delivery (POD)
**Purpose**: Delivery confirmation and signature capture

**Key Features**:
- Digital signature capture
- Delivery confirmation
- Links to Transport Leg or Transport Job

---

## Automation Features

### Auto Vehicle Assignment
**Trigger**: When Transport Leg is created or updated
**Condition**: If `enable_auto_vehicle_assignment` is enabled in Transport Settings
**Action**: Automatically assigns suitable vehicle based on:
- Vehicle type compatibility
- Capacity constraints
- Time window constraints
- Address day availability
- Plate coding constraints
- Truck ban constraints
- Ad-hoc transport factors

### Auto Billing
**Trigger**: When Transport Job status changes to "Completed"
**Condition**: If `enable_auto_billing` is enabled in Transport Settings
**Action**: Automatically creates Sales Invoice for completed Transport Legs

---

## Constraint System

The Transport Module includes a comprehensive constraint checking system:

### Constraint Types:
1. **Time Window Constraints**: Checks pickup/delivery time windows
2. **Address Day Availability**: Validates day-of-week restrictions
3. **Plate Coding Constraints**: Validates license plate restrictions (odd/even days)
4. **Truck Ban Constraints**: Checks area and time-based truck ban restrictions
5. **Ad-Hoc Factors**: Considers road closures, port congestion, etc.

### Constraint Checking Modes:
- **Strict**: Blocks vehicle assignment if constraints fail
- **Warning**: Allows assignment but shows warnings
- **Disabled**: Skips constraint checking

---

## Routing and Telematics

### Routing
- Supports multiple providers: OSRM, Mapbox, Google Maps
- Auto-computes routes and distances
- Route optimization for Run Sheets
- Distance and duration caching for performance

### Telematics
- Real-time vehicle tracking
- ETA calculations
- Auto arrival/departure detection
- Temperature monitoring (for refrigerated transport)
- Position tracking and event logging

---

## Carbon Footprint

### Features:
- Auto-compute carbon emissions
- Multiple calculation methods:
  - Factor table (default)
  - ClimaTQ API
  - Carbon Interface API
  - Custom webhook
- Tracks CO2e (Carbon Dioxide Equivalent) per leg
- Emission factors based on vehicle type and cargo

---

## Key Relationships

```
Transport Order
    │
    ├─▶ Transport Job
    │       │
    │       ├─▶ Transport Leg (1 to many)
    │       │       │
    │       │       └─▶ Run Sheet (many to many)
    │       │               │
    │       │               ├─▶ Transport Vehicle
    │       │               ├─▶ Driver
    │       │               └─▶ Transport Company
    │       │
    │       └─▶ Sales Invoice (after completion)
    │
    └─▶ Transport Plan (optional)
            │
            └─▶ Run Sheet (1 to many)
```

---

## Status Summary

### Transport Job Statuses:
- **Draft**: Initial state
- **Submitted**: Ready for planning
- **In Progress**: Execution started
- **Completed**: All legs completed

### Transport Leg Statuses:
- **Open**: Not assigned
- **Assigned**: Assigned to Run Sheet
- **Started**: Execution started
- **Completed**: Execution completed
- **Billed**: Invoiced

### Run Sheet Statuses:
- **Draft**: Created, not dispatched
- **Dispatched**: Vehicle dispatched
- **In-Progress**: Execution in progress
- **Hold**: Temporarily paused
- **Completed**: All legs completed
- **Cancelled**: Cancelled

---

## Best Practices

1. **Order Creation**: Always create Transport Order first for customer bookings
2. **Job Creation**: Create Transport Job from Transport Order to maintain traceability
3. **Leg Planning**: Plan all legs before creating Run Sheets
4. **Route Optimization**: Use Transport Plan to optimize routes and consolidate shipments
5. **Constraint Checking**: Enable constraint system for compliance and efficiency
6. **Telematics**: Integrate telematics for real-time tracking and ETA updates
7. **Auto Features**: Enable auto-vehicle assignment and auto-billing for efficiency
8. **Documentation**: Capture Proof of Delivery for all completed legs

---

## Integration Points

- **Sales Quote**: Transport Orders can link to Sales Quotes
- **Sales Invoice**: Auto-generated from completed Transport Jobs
- **Customer Portal**: Customers can track their transport jobs
- **Telematics Providers**: Real-time vehicle tracking integration
- **Routing Services**: OSRM, Mapbox, Google Maps integration
- **Carbon Providers**: Carbon footprint calculation services

---

## Reports and Analytics

- **Run Sheet Report**: View and print Run Sheets
- **Outsource Job Report**: Track outsourced transport jobs
- **Transport Dashboard**: Real-time monitoring of transport operations
- **Carbon Reports**: Environmental impact tracking

---

*Last Updated: Based on Transport Module v1.0*
