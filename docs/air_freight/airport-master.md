## Overview

Airport Master is a master data document that stores comprehensive information about airports worldwide, including IATA and ICAO codes, location data, capabilities, and contact information. This master data is essential for air freight operations.

## Purpose

The Airport Master is used to:
- Store comprehensive airport information
- Track airport codes (IATA, ICAO)
- Manage airport location data
- Track airport capabilities (cargo hub, customs, dangerous goods, etc.)
- Reference in Air Shipments, Master Air Waybills, and Flight Schedules
- Support route planning and optimization

## Document Structure

The Airport Master document contains the following sections:

### Airport Information

- **Airport Name**: Full name of the airport (required)
- **IATA Code**: 3-letter IATA code (required, unique)
- **ICAO Code**: 4-letter ICAO code (unique)
- **Airport Type**: Type of airport
  - Airport
  - Heliport
  - Seaplane Base
  - Balloonport
  - Closed
- **City**: City where airport is located
- **Country**: Country where airport is located
- **Timezone**: Airport timezone

### Location

- **Latitude**: Airport latitude coordinates
- **Longitude**: Airport longitude coordinates
- **Altitude (Meters)**: Airport altitude in meters
- **GMT Offset**: GMT offset
- **DST**: Daylight Saving Time information

### Capabilities

- **Is Cargo Hub**: Checkbox indicating if airport is a cargo hub
- **Is International**: Checkbox indicating if airport handles international flights
- **Has Customs Facility**: Checkbox indicating customs facility availability
- **Supports Dangerous Goods**: Checkbox indicating DG handling capability
- **Supports Live Animals**: Checkbox indicating live animal handling capability
- **Supports Refrigerated**: Checkbox indicating refrigerated cargo capability

### Contact Information

- **Website**: Airport website
- **Phone**: Airport phone number
- **Email**: Airport email address
- **Address Line 1**: Physical address
- **Address Line 2**: Additional address information
- **Postal Code**: Postal code

### Metadata

- **Data Source**: Source of airport data (read-only)
- **Last Synced**: Last synchronization timestamp (read-only)
- **Is Active**: Checkbox indicating if airport is currently active
- **Disabled**: Checkbox indicating if airport is disabled

## Creating an Airport

### Step 1: Basic Information

1. Navigate to **Air Freight > Master > Airport Master**
2. Click **New**
3. Enter **Airport Name** (required)
4. Enter **IATA Code** (required, 3-letter code, unique)
5. Enter **ICAO Code** (4-letter code, unique) if applicable
6. Select **Airport Type** (default: Airport)
7. Enter **City**
8. Select **Country**
9. Enter **Timezone** if applicable

### Step 2: Location

1. Enter **Latitude** coordinates
2. Enter **Longitude** coordinates
3. Enter **Altitude (Meters)** if applicable
4. Enter **GMT Offset** if applicable
5. Enter **DST** information if applicable

### Step 3: Capabilities

1. Check **Is Cargo Hub** if airport is a cargo hub
2. Check **Is International** if airport handles international flights
3. Check **Has Customs Facility** if customs facility is available
4. Check **Supports Dangerous Goods** if DG handling is available
5. Check **Supports Live Animals** if live animal handling is available
6. Check **Supports Refrigerated** if refrigerated cargo handling is available

### Step 4: Contact Information

1. Enter **Website** if applicable
2. Enter **Phone** if applicable
3. Enter **Email** if applicable
4. Enter **Address Line 1**
5. Enter **Address Line 2** if applicable
6. Enter **Postal Code** if applicable

### Step 5: Status

1. Check **Is Active** if airport is currently active
2. Check **Disabled** if airport is disabled

### Step 6: Save

1. Review all information
2. Click **Save**

## Key Fields Explained

### Airport Name
Full name of the airport. This is the display name used in lists and reports.

### IATA Code
3-letter IATA (International Air Transport Association) code. This is the standard code used in air freight operations. Must be unique and is required.

### ICAO Code
4-letter ICAO (International Civil Aviation Organization) code. This is used for international aviation operations. Must be unique.

### Airport Type
Type of airport facility:
- **Airport**: Standard airport
- **Heliport**: Helicopter facility
- **Seaplane Base**: Seaplane facility
- **Balloonport**: Balloon facility
- **Closed**: Closed airport

### Location Data
Geographic location information:
- **Latitude/Longitude**: Precise location coordinates
- **Altitude**: Airport elevation
- **GMT Offset**: Time zone offset
- **DST**: Daylight Saving Time information

### Capabilities
Airport capabilities and facilities:
- **Is Cargo Hub**: Indicates if airport is a major cargo hub
- **Is International**: Indicates if airport handles international flights
- **Has Customs Facility**: Indicates customs facility availability
- **Supports Dangerous Goods**: Indicates DG handling capability
- **Supports Live Animals**: Indicates live animal handling capability
- **Supports Refrigerated**: Indicates refrigerated cargo capability

## Usage

Airport Master is referenced in:

- **Air Shipment**: Origin Port, Destination Port
- **Master Air Waybill**: Origin Airport, Destination Airport
- **Air Consolidation**: Origin Airport, Destination Airport
- **Flight Schedule**: Departure Airport, Arrival Airport
- **Flight Route**: Origin Airport, Destination Airport, Transit Airports
- **Air Freight Rate**: Origin Airport, Destination Airport
- **Reports**: Used in various air freight reports

## Best Practices

1. **Standard Codes**: Always use standard IATA codes (3-letter codes)
2. **Accurate ICAO Codes**: Maintain accurate ICAO codes (4-letter codes)
3. **Location Accuracy**: Keep location coordinates accurate
4. **Capabilities**: Update capabilities based on actual airport facilities
5. **Active Status**: Maintain active/inactive status based on operations
6. **Contact Information**: Keep contact information current
7. **Regular Updates**: Review and update airport information regularly

## IATA Code Standards

IATA codes are 3-letter codes assigned by the International Air Transport Association:

- Used in air freight documentation
- Standard for airline and airport identification
- Required for air freight operations
- Must be unique across all airports

## ICAO Code Standards

ICAO codes are 4-letter codes assigned by the International Civil Aviation Organization:

- Used for international aviation operations
- More specific than IATA codes
- Used in flight planning and air traffic control
- Must be unique across all airports

## Capability Management

Airport capabilities help:

- Filter airports by capabilities in selection lists
- Identify suitable airports for specific cargo types
- Plan routes based on airport capabilities
- Ensure compliance with cargo requirements

## Data Synchronization

Airport data can be synchronized from external sources:

- **Data Source**: Indicates source of airport data
- **Last Synced**: Timestamp of last synchronization
- System can auto-update airport information from external APIs

## Inactive Airports

When an airport is marked as inactive or disabled:

- It will not appear in selection lists for new documents
- Historical records will still reference the airport
- Existing documents linked to the airport remain valid
- Reports will still include inactive airports for historical data

## Related Documents

- **Air Shipment**: References airports for origin and destination
- **Master Air Waybill**: References airports for flight information
- **Air Consolidation**: References airports for consolidation routes
- **Flight Schedule**: References airports for flight routes
- **Flight Route**: References airports for route planning

## Next Steps

- Learn about [Air Shipment](air-shipment.md) management
- Understand [Master Air Waybill](master-air-waybill.md) operations
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

