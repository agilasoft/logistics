## Overview

Airline is a master data document that stores information about airlines that provide air cargo services for air freight shipments. This master data is referenced in Air Shipments, Master Air Waybills, and Consolidation documents.

## Purpose

The Airline master is used to:
- Store information about airlines
- Track airline codes (IATA, ICAO, numeric codes)
- Manage airline performance metrics
- Track airline memberships and alliances
- Configure carrier contract terms and surcharges
- Link airlines to Customer/Supplier masters for accounting

## Document Structure

The Airline document contains the following sections:

### Codes Section

- **Code**: Unique identifier for the airline (auto-generated or manual, unique)
- **Airline Name**: Full name of the airline
- **Logo**: Airline logo image (optional)
- **Airline Numeric Code**: IATA numeric code
- **Three Letter Numeric Code**: ICAO three-letter code
- **Two Character Code**: IATA two-character code

### Memberships Section

- **Memberships**: Table of Airline Membership
  - Membership type (e.g., IATA, alliance)
  - Membership details
  - Membership status

### Other Details Section

- **Short Name**: Short name or abbreviation
- **Address**: Link to Address master

### Performance & Operations Section

- **Airline Performance Score**: Overall performance score
- **On-Time Performance %**: On-time performance percentage
- **Damage Rate %**: Damage rate percentage
- **Capacity Utilization %**: Capacity utilization percentage
- **Preferred Carrier**: Checkbox indicating if this is a preferred carrier
- **Carrier Contract Terms**: Contract terms and conditions
- **Fuel Surcharge Rate**: Fuel surcharge rate
- **Security Surcharge**: Security surcharge amount

### eFreight Tab

Contains eFreight configuration and settings.

### Airline Codes Tab

Contains additional airline code information.

### Notes Tab

Contains notes and additional information.

## Creating an Airline

### Step 1: Basic Information

1. Navigate to **Air Freight > Master > Airline**
2. Click **New**
3. Enter **Code** (unique identifier) - can be auto-generated or manual
4. Enter **Airline Name**
5. Upload **Logo** if applicable

### Step 2: Airline Codes

1. Enter **Airline Numeric Code** (IATA numeric code)
2. Enter **Two Character Code** (IATA two-character code)
3. Enter **Three Letter Numeric Code** (ICAO three-letter code)

### Step 3: Memberships

1. Go to **Memberships** section
2. In **Memberships** table, click **Add Row**
3. Enter membership details:
   - Membership type
   - Membership details
   - Status
4. Repeat for all memberships

### Step 4: Other Details

1. Enter **Short Name** if applicable
2. Select **Address** if applicable

### Step 5: Performance & Operations

1. Enter **Airline Performance Score** if available
2. Enter **On-Time Performance %** if available
3. Enter **Damage Rate %** if available
4. Enter **Capacity Utilization %** if available
5. Check **Preferred Carrier** if this is a preferred carrier
6. Enter **Carrier Contract Terms** if applicable
7. Enter **Fuel Surcharge Rate** if applicable
8. Enter **Security Surcharge** if applicable

### Step 6: Save

1. Review all information
2. Click **Save**

## Key Fields Explained

### Code
Unique identifier for the airline. This code is used throughout the system to reference the airline. It can be:
- Auto-generated based on naming rules
- Manually entered
- Must be unique across all airlines

### Airline Name
Full name of the airline. This is the display name used in lists and reports.

### Airline Codes
Standard airline identification codes:
- **Airline Numeric Code**: IATA numeric code (3-digit)
- **Two Character Code**: IATA two-character code (2-letter)
- **Three Letter Numeric Code**: ICAO three-letter code (3-letter)

### Logo
Airline logo image. This is displayed in lists and reports for visual identification.

### Performance Metrics
Key performance indicators:
- **Airline Performance Score**: Overall performance rating
- **On-Time Performance %**: Percentage of on-time flights
- **Damage Rate %**: Percentage of damaged shipments
- **Capacity Utilization %**: Percentage of capacity utilized

### Preferred Carrier
Checkbox indicating whether this airline is a preferred carrier. Preferred carriers may be prioritized in carrier selection.

### Contract Terms
Carrier contract terms and conditions. This can include:
- Rate agreements
- Service level agreements
- Special terms and conditions

### Surcharges
Additional charges:
- **Fuel Surcharge Rate**: Fuel surcharge amount
- **Security Surcharge**: Security surcharge amount

## Usage

Airline is referenced in:

- **Air Shipment**: Selected as the airline carrier
- **Master Air Waybill**: Linked to master air waybill
- **Air Consolidation**: Selected for consolidation operations
- **Flight Schedule**: Linked to flight schedules
- **Air Freight Rate**: Used in rate configuration
- **Reports**: Used in various air freight reports

## Best Practices

1. **Standard Codes**: Use standard IATA and ICAO codes for airline identification
2. **Complete Information**: Enter all available airline codes
3. **Performance Metrics**: Maintain accurate performance metrics for carrier selection
4. **Active Status**: Keep airline status updated (active/inactive)
5. **Contract Terms**: Maintain current contract terms and surcharges
6. **Memberships**: Track airline memberships and alliances
7. **Regular Updates**: Review and update airline information regularly

## Naming Conventions

Recommended naming conventions for airline codes:

- Use IATA two-character codes (e.g., "AA" for American Airlines)
- Use standard IATA numeric codes
- Use ICAO three-letter codes when available
- Maintain consistency across the system

## Performance Tracking

The airline master supports performance tracking:

- Track on-time performance
- Monitor damage rates
- Track capacity utilization
- Calculate overall performance scores

These metrics help in:
- Carrier selection
- Performance evaluation
- Contract negotiations
- Service level monitoring

## Inactive Airlines

When an airline is marked as inactive:

- It will not appear in selection lists for new documents
- Historical records will still reference the airline
- Existing documents linked to the airline remain valid
- Reports will still include inactive airlines for historical data

## Related Documents

- **Air Shipment**: Uses airline for carrier information
- **Master Air Waybill**: Links to airline
- **Air Consolidation**: References airline
- **Flight Schedule**: Links to airline
- **Airline Membership**: Linked in Memberships table

## Next Steps

- Learn about [Air Shipment](air-shipment.md) management
- Understand [Master Air Waybill](master-air-waybill.md) operations
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

