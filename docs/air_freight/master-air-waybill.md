## Overview

Master Air Waybill (MAWB) is a document that represents the main air waybill issued by the airline for consolidated cargo. It contains information about the flight, aircraft, and consolidated shipment, and can be linked to multiple House Air Waybills (Air Shipments).

## Purpose

The Master Air Waybill document is used to:
- Track Master Air Waybills issued by airlines
- Manage flight and aircraft information
- Link multiple House Air Waybills to a single Master AWB
- Track flight schedules and real-time flight status
- Manage ground handling operations
- Integrate with flight schedule systems

## Document Structure

The Master Air Waybill document contains the following sections:

### Basic Information

- **Master AWB No**: Master Air Waybill number (unique, required)
- **Airline**: Link to Airline master
- **Aircraft Type**: Type of aircraft
- **Flight No**: Flight number
- **Aircraft Registration No**: Aircraft registration number

### Flight Type Indicators

- **Chartered Flight**: Checkbox indicating if flight is chartered
- **Connected Flight**: Checkbox indicating if flight is connected
- **Cargo Flight**: Checkbox indicating if flight is cargo-only

### IATA Integration Section

- **Flight Date**: Flight date
- **Manifest Sent**: Checkbox indicating if manifest has been sent
- **Manifest Sent Date**: Date when manifest was sent

### Flight Schedule Integration

- **Flight Schedule**: Link to Flight Schedule document
- **Auto-Update from Flight Schedule**: Checkbox to enable automatic updates
- **Flight Status**: Current flight status (read-only)
  - Scheduled
  - Active
  - EnRoute
  - Landed
  - Cancelled
  - Delayed
  - Diverted
- **Delay (Minutes)**: Flight delay in minutes (read-only)

### Flight Information

#### Origin Airport
- **Origin Airport**: Origin airport (read-only, from flight schedule)
- **Origin IATA**: Origin IATA code (read-only)
- **Departure Terminal**: Departure terminal (read-only)
- **Departure Gate**: Departure gate (read-only)

#### Destination Airport
- **Destination Airport**: Destination airport (read-only, from flight schedule)
- **Destination IATA**: Destination IATA code (read-only)
- **Arrival Terminal**: Arrival terminal (read-only)
- **Arrival Gate**: Arrival gate (read-only)

### Flight Times

- **Scheduled Departure (UTC)**: Scheduled departure time in UTC
- **Actual Departure (UTC)**: Actual departure time in UTC (read-only)
- **ETD (Local Time)**: Estimated time of departure in local time (read-only)
- **Scheduled Arrival (UTC)**: Scheduled arrival time in UTC
- **Actual Arrival (UTC)**: Actual arrival time in UTC (read-only)
- **ETA (Local Time)**: Estimated time of arrival in local time (read-only)

### Flight Details

- **Flight Duration (Minutes)**: Flight duration in minutes (read-only)
- **Distance (KM)**: Flight distance in kilometers (read-only)
- **Total Cargo Capacity (KG)**: Total cargo capacity in kilograms (read-only)
- **Available Capacity (KG)**: Available capacity in kilograms (read-only)
- **Booked on This AWB (KG)**: Booked weight on this Master AWB

### Real-time Tracking

(Visible when flight status is Active or EnRoute)

- **Last Known Position**: Last known position
- **Latitude**: Current latitude (read-only)
- **Longitude**: Current longitude (read-only)
- **Altitude (Meters)**: Current altitude in meters (read-only)
- **Speed (KM/H)**: Current speed in kilometers per hour (read-only)
- **Is On Ground**: Checkbox indicating if aircraft is on ground (read-only)
- **Last Position Update**: Timestamp of last position update (read-only)

### Handling Parties

- **Sending Agent**: Freight agent at origin
- **Receiving Agent**: Freight agent at destination
- **Booking Reference No**: Booking reference number
- **Agent Reference**: Agent reference number

### Departure Tab

Contains origin terminal information:

- **Origin CTO**: Cargo Terminal Operator at origin
- **Origin CFS**: Container Freight Station at origin
- **Receipt Requested**: Date when cargo receipt is requested
- **Dispatch Requested**: Date when dispatch is requested

### Arrival Tab

Contains destination terminal information:

- **Destination CTO**: Cargo Terminal Operator at destination
- **Destination CFS**: Container Freight Station at destination
- **Receipt Requested**: Date when cargo receipt is requested
- **Dispatch Requested**: Date when dispatch is requested

### Ground Handling Tab

Contains ground handling information:

- **Ground Works Agreement**: Text editor for ground handling agreement details

### Connections Tab

Shows linked documents and relationships:
- Linked Air Shipments (House Air Waybills)
- Related consolidations
- Related documents

## Creating a Master Air Waybill

### Step 1: Basic Information

1. Navigate to **Air Freight > Master > Master Air Waybill**
2. Click **New**
3. Enter **Master AWB No** (unique identifier, required)
4. Select **Airline**
5. Enter **Flight No**
6. Enter **Aircraft Type** if applicable
7. Enter **Aircraft Registration No** if applicable

### Step 2: Flight Type

1. Check **Chartered Flight** if applicable
2. Check **Connected Flight** if applicable
3. Check **Cargo Flight** if applicable

### Step 3: Flight Schedule Integration

1. Select **Flight Schedule** if using flight schedule integration
2. Check **Auto-Update from Flight Schedule** to enable automatic updates
3. System will automatically populate flight information from flight schedule

### Step 4: Flight Information

1. Enter **Scheduled Departure (UTC)** and **Scheduled Arrival (UTC)**
2. System will auto-populate airport information if flight schedule is linked
3. Enter **Booked on This AWB (KG)** if applicable

### Step 5: IATA Integration

1. Enter **Flight Date**
2. Check **Manifest Sent** when manifest is sent
3. System will record **Manifest Sent Date** automatically

### Step 6: Handling Parties

1. Select **Sending Agent** (origin agent)
2. Select **Receiving Agent** (destination agent)
3. Enter **Booking Reference No** if applicable
4. Enter **Agent Reference** if applicable

### Step 7: Departure Information

1. Go to **Departure Tab**
2. Select **Origin CTO** (Cargo Terminal Operator)
3. Select **Origin CFS** (Container Freight Station) if applicable
4. Enter **Receipt Requested** date
5. Enter **Dispatch Requested** date

### Step 8: Arrival Information

1. Go to **Arrival Tab**
2. Select **Destination CTO**
3. Select **Destination CFS** if applicable
4. Enter **Receipt Requested** date
5. Enter **Dispatch Requested** date

### Step 9: Ground Handling

1. Go to **Ground Handling Tab**
2. Enter ground handling agreement details in **Ground Works Agreement** text editor

### Step 10: Save and Submit

1. Review all information
2. Verify flight schedule integration if applicable
3. Click **Save**
4. Click **Submit** to finalize the Master AWB

## Linking House Air Waybills to Master AWB

To link Air Shipments (House Air Waybills) to a Master AWB:

1. Open the **Air Shipment** document
2. Go to **Master Tab**
3. Select the **Master AWB**
4. Save the Air Shipment

The linked Air Shipments will appear in the Master AWB's **Connections Tab**.

## Flight Schedule Integration

When a Flight Schedule is linked:

1. System automatically populates:
   - Origin and destination airports
   - Scheduled departure and arrival times
   - Flight status
   - Real-time tracking information (if available)

2. If **Auto-Update from Flight Schedule** is enabled:
   - Flight status updates automatically
   - Delay information updates automatically
   - Real-time tracking updates automatically

## Real-time Flight Tracking

When flight status is Active or EnRoute:

- System displays real-time tracking information
- Shows current position (latitude, longitude, altitude)
- Displays current speed
- Indicates if aircraft is on ground
- Updates position automatically if flight schedule integration is enabled

## Best Practices

1. **Unique Master AWB Numbers**: Ensure Master AWB numbers are unique
2. **Accurate Flight Information**: Enter correct flight number and aircraft details
3. **Flight Schedule Integration**: Link to Flight Schedule for automatic updates
4. **Complete Terminal Information**: Fill in CTO and CFS details
5. **Date Accuracy**: Ensure departure and arrival dates are accurate
6. **Agent Information**: Maintain accurate sending and receiving agent information
7. **Link House AWBs**: Link all related House Air Waybills to the Master AWB
8. **Monitor Flight Status**: Monitor flight status and delays regularly

## Related Documents

- **Air Shipment**: House Air Waybills linked to this Master AWB
- **Air Consolidation**: Consolidation operations
- **Flight Schedule**: Flight schedule information
- **Airline**: Airline information
- **Cargo Terminal Operator**: Terminal operator information

## Usage in Consolidation

Master Air Waybills are commonly used in consolidation operations:

1. Create an **Air Consolidation** document
2. Create or link a **Master Air Waybill**
3. Link multiple **Air Shipments** (House Air Waybills) to the Master AWB
4. Track the consolidated shipment through the Master AWB

## Next Steps

- Learn about [Air Consolidation](air-consolidation.md)
- Understand [Air Shipment](air-shipment.md) management
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

