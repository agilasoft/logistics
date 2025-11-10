# Air Freight Master Data

## Overview

Master data forms the foundation of the Air Freight module. This document describes all master data records that need to be set up before creating air freight transactions.

## Airline

### Purpose

Airline master contains information about airlines that provide air cargo services for air freight shipments.

### Key Fields

- **Code**: Unique identifier for the airline (auto-generated or manual, unique)
- **Airline Name**: Full name of the airline
- **Airline Numeric Code**: IATA numeric code
- **Two Character Code**: IATA two-character code
- **Three Letter Numeric Code**: ICAO three-letter code
- **Logo**: Airline logo image (optional)
- **Short Name**: Short name or abbreviation
- **Address**: Link to Address master
- **Is Active**: Checkbox to indicate if the airline is currently active

### Performance & Operations

- **Airline Performance Score**: Overall performance score
- **On-Time Performance %**: On-time performance percentage
- **Damage Rate %**: Damage rate percentage
- **Capacity Utilization %**: Capacity utilization percentage
- **Preferred Carrier**: Checkbox indicating if this is a preferred carrier
- **Carrier Contract Terms**: Contract terms and conditions
- **Fuel Surcharge Rate**: Fuel surcharge rate
- **Security Surcharge**: Security surcharge amount

### Memberships Tab

In the Memberships tab, you can link airline memberships (e.g., IATA, alliances).

### Usage

Airline is referenced in:
- Air Shipment documents
- Master Air Waybill documents
- Air Consolidation documents
- Flight Schedule records
- Air Freight Rate configuration

### Best Practices

- Use standard IATA codes for airline identification
- Keep airline records active/inactive based on current business relationships
- Maintain performance metrics for carrier selection
- Update contract terms and surcharges regularly
- Keep airline information current

## Airport Master

### Purpose

Airport Master stores comprehensive information about airports worldwide, including IATA and ICAO codes, location data, and capabilities.

### Key Fields

#### Airport Information
- **Airport Name**: Full name of the airport (required)
- **IATA Code**: 3-letter IATA code (required, unique)
- **ICAO Code**: 4-letter ICAO code (unique)
- **Airport Type**: Type of airport (Airport, Heliport, Seaplane Base, etc.)
- **City**: City where airport is located
- **Country**: Country where airport is located
- **Timezone**: Airport timezone

#### Location
- **Latitude**: Airport latitude coordinates
- **Longitude**: Airport longitude coordinates
- **Altitude (Meters)**: Airport altitude in meters
- **GMT Offset**: GMT offset
- **DST**: Daylight Saving Time information

#### Capabilities
- **Is Cargo Hub**: Checkbox indicating if airport is a cargo hub
- **Is International**: Checkbox indicating if airport handles international flights
- **Has Customs Facility**: Checkbox indicating customs facility availability
- **Supports Dangerous Goods**: Checkbox indicating DG handling capability
- **Supports Live Animals**: Checkbox indicating live animal handling capability
- **Supports Refrigerated**: Checkbox indicating refrigerated cargo capability

#### Contact Information
- **Website**: Airport website
- **Phone**: Airport phone number
- **Email**: Airport email address
- **Address Line 1**: Physical address
- **Address Line 2**: Additional address information
- **Postal Code**: Postal code

#### Status
- **Is Active**: Checkbox indicating if airport is currently active
- **Disabled**: Checkbox indicating if airport is disabled

### Usage

Airport Master is referenced in:
- Air Shipment (Origin Port, Destination Port)
- Master Air Waybill documents
- Air Consolidation
- Flight Schedule records
- Flight Route records
- Air Freight Rate configuration

### Best Practices

- Always use standard IATA codes (3-letter codes)
- Maintain accurate ICAO codes (4-letter codes)
- Keep location coordinates accurate
- Update capabilities based on actual airport facilities
- Maintain active/inactive status based on operations
- Keep contact information current

## Flight Route

### Purpose

Flight Route master stores information about flight routes between airports, including transit points and route details.

### Key Fields

- **Route Code**: Unique identifier for the route
- **Origin Airport**: Origin airport (IATA code)
- **Destination Airport**: Destination airport (IATA code)
- **Transit Points**: Intermediate airports if applicable
- **Route Distance**: Distance in kilometers
- **Estimated Flight Time**: Estimated flight duration
- **Is Active**: Checkbox indicating if route is currently active

### Usage

Flight Route is referenced in:
- Flight Schedule records
- Route planning and optimization
- Consolidation routing

### Best Practices

- Create routes for commonly used paths
- Maintain accurate distance and time information
- Update routes as airline routes change
- Keep route status current

## Flight Schedule

### Purpose

Flight Schedule master stores detailed flight schedule information including departure/arrival times, aircraft details, and cargo capacity.

### Key Fields

#### Flight Information
- **Flight Number**: Flight number
- **Airline**: Link to Airline master
- **Aircraft Type**: Type of aircraft
- **Registration**: Aircraft registration number
- **Flight Status**: Current flight status

#### Departure Information
- **Departure Airport**: Origin airport
- **Departure Terminal**: Departure terminal
- **Departure Gate**: Departure gate
- **Scheduled Departure**: Scheduled departure time (UTC)
- **Estimated Departure**: Estimated departure time
- **Actual Departure**: Actual departure time
- **Departure Timezone**: Departure timezone

#### Arrival Information
- **Arrival Airport**: Destination airport
- **Arrival Terminal**: Arrival terminal
- **Arrival Gate**: Arrival gate
- **Scheduled Arrival**: Scheduled arrival time (UTC)
- **Estimated Arrival**: Estimated arrival time
- **Actual Arrival**: Actual arrival time
- **Arrival Timezone**: Arrival timezone

#### Flight Details
- **Delay Minutes**: Flight delay in minutes
- **Flight Duration Minutes**: Flight duration in minutes
- **Distance (KM)**: Flight distance in kilometers
- **Cargo Capacity (KG)**: Total cargo capacity in kilograms
- **Available Cargo Capacity (KG)**: Available capacity in kilograms
- **Cargo Booked (KG)**: Booked cargo weight in kilograms

#### Tracking Information
- **Latitude**: Current latitude
- **Longitude**: Current longitude
- **Altitude (Meters)**: Current altitude
- **Speed (KM/H)**: Current speed
- **Heading**: Current heading
- **Last Position Update**: Last position update timestamp
- **Is On Ground**: Checkbox indicating if aircraft is on ground

### Usage

Flight Schedule is referenced in:
- Master Air Waybill documents
- Air Shipment documents (for flight selection)
- Capacity management
- Real-time flight tracking

### Best Practices

- Keep flight schedules updated regularly
- Enable auto-sync if using external flight schedule APIs
- Monitor flight status and update delays
- Track cargo capacity for booking management
- Maintain accurate tracking information

## Unit Load Device (ULD)

### Purpose

Unit Load Device (ULD) master stores information about ULD types used in air cargo operations, including capacity and specifications.

### Key Fields

- **ULD Code**: Unique identifier for the ULD type
- **ULD Name**: Name of the ULD type
- **ULD Type**: Type of ULD (e.g., AKE, ALF, PMC)
- **Capacity (KG)**: Weight capacity in kilograms
- **Volume (CBM)**: Volume capacity in cubic meters
- **Dimensions**: Physical dimensions
- **Is Active**: Checkbox indicating if ULD type is currently active

### Usage

ULD is referenced in:
- Air Shipment documents (ULD assignment)
- Capacity planning
- ULD tracking

### Best Practices

- Use standard ULD type codes
- Maintain accurate capacity information
- Keep ULD specifications current
- Update active/inactive status as needed

## Shipper and Consignee

### Purpose

Shipper and Consignee are parties involved in air freight shipments. These are typically managed as separate master data or linked to Customer/Supplier records.

### Key Fields

- **Code**: Unique identifier
- **Name**: Full name of the party
- **Address**: Physical address
- **Contact**: Contact person and details
- **Country**: Country of origin/destination

### Usage

Shipper and Consignee are referenced in:
- Air Shipment documents
- Master Air Waybill documents
- Shipping documents and air waybills

### Best Practices

- Maintain accurate address and contact information
- Link to Customer/Supplier masters for integrated operations
- Keep party information updated

## Freight Agent

### Purpose

Freight Agent master contains information about freight forwarding agents that may be involved in shipments.

### Key Fields

- **Code**: Unique identifier for the agent
- **Agent Name**: Full name of the agent
- **Agent Type**: Type of agent (customer agent, supplier agent)
- **Address**: Physical address
- **Is Active**: Checkbox to indicate if the agent is currently active

### Usage

Freight Agent is referenced in:
- Air Shipment documents
- Master Air Waybill documents
- Agency network management

### Best Practices

- Maintain agent relationships and commission structures
- Keep agent information current
- Track active/inactive agent status

## Dangerous Goods

### Purpose

Dangerous Goods master contains information about dangerous goods substances, classes, and compliance requirements.

### Key Fields

- **DG Code**: Unique identifier for the dangerous goods substance
- **DG Name**: Name of the dangerous goods substance
- **DG Class**: Dangerous goods class
- **UN Number**: UN number for the substance
- **Packing Group**: Packing group classification
- **Is Active**: Checkbox indicating if DG is currently active

### Usage

Dangerous Goods is referenced in:
- Air Shipment Packages (DG information)
- Dangerous Goods Declaration
- DG compliance validation

### Best Practices

- Maintain comprehensive DG database
- Keep DG classifications current with IATA regulations
- Update UN numbers and packing groups accurately
- Maintain active/inactive status

## Master Data Relationships

The following diagram shows how master data records relate to each other:

```
Airline
    ├── Referenced in: Air Shipment, Master AWB, Consolidation, Flight Schedule
    └── Memberships (IATA, Alliances)

Airport Master
    ├── Referenced in: Air Shipment, Master AWB, Consolidation, Flight Schedule, Flight Route
    └── Capabilities (Cargo Hub, Customs, DG Support)

Flight Schedule
    ├── Airline (linked)
    ├── Origin/Destination Airports (linked)
    └── Referenced in: Master AWB, Air Shipment

Flight Route
    ├── Origin/Destination Airports (linked)
    └── Referenced in: Flight Schedule, Consolidation

ULD
    └── Referenced in: Air Shipment (ULD assignment)

Shipper/Consignee
    └── Referenced in: Air Shipment, Master AWB

Freight Agent
    └── Referenced in: Air Shipment, Master AWB

Dangerous Goods
    └── Referenced in: Air Shipment Packages, DG Declaration
```

## Setup Sequence

Recommended sequence for setting up master data:

1. **Airports**: Set up airports first as they are referenced by other masters
2. **Airlines**: Create airline records
3. **Flight Routes**: Set up flight routes linked to airports
4. **Flight Schedules**: Create or import flight schedules
5. **ULDs**: Set up ULD types if applicable
6. **Shippers and Consignees**: Set up party masters
7. **Freight Agents**: Configure agent network if applicable
8. **Dangerous Goods**: Create DG database if handling dangerous goods

## Maintenance

### Regular Updates

- Review and update airline status (active/inactive)
- Verify airport codes and capabilities
- Update flight schedules regularly
- Maintain shipper and consignee contact information
- Keep DG database current with regulations

### Data Quality

- Ensure unique codes for all master records
- Maintain consistent naming conventions
- Keep address and contact information current
- Verify IATA/ICAO codes for accuracy
- Update performance metrics regularly

## Next Steps

After setting up master data:

1. Review [Setup Guide](setup.md) for configuration
2. Learn how to create an [Air Shipment](air-shipment.md)
3. Understand [Master Air Waybill Management](master-air-waybill.md)

---

*For information on creating and managing transactions, refer to the respective doctype documentation.*

