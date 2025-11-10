# Air Freight Setup

## Overview

This guide will help you set up the Air Freight module in CargoNext. Proper setup ensures that all air freight operations run smoothly and efficiently with full IATA compliance support.

## Prerequisites

Before setting up the Air Freight module, ensure that:

1. CargoNext is installed and configured
2. You have System Manager or Administrator access
3. Basic master data (Company, Customer, Supplier) is set up
4. Airport master data is configured (if using airport management)

## Configuration Steps

### 1. IATA Settings

Navigate to **Air Freight > Setup > IATA Settings** to configure IATA integration.

#### Key Settings

- **IATA API Configuration**: Configure IATA API credentials and endpoints
- **Message Queue Settings**: Configure IATA message queue processing
- **Status Update Frequency**: Set frequency for automatic status updates
- **eAWB Settings**: Configure electronic Air Waybill settings

#### Configuration Steps

1. Go to **Air Freight > Setup > IATA Settings**
2. Configure IATA API credentials if using IATA integration
3. Set up message queue processing settings
4. Configure eAWB settings if applicable
5. Save the settings

### 2. Flight Schedule Settings

Navigate to **Air Freight > Setup > Flight Schedule Settings** to configure flight schedule integration.

#### Key Settings

- **Flight Schedule API**: Configure flight schedule API credentials
- **Auto-Sync Settings**: Configure automatic flight schedule synchronization
- **Update Frequency**: Set frequency for flight schedule updates
- **Data Source Priority**: Configure data source priority for flight information

#### Configuration Steps

1. Go to **Air Freight > Setup > Flight Schedule Settings**
2. Configure flight schedule API credentials if using external APIs
3. Set up auto-sync settings
4. Configure update frequency
5. Save the settings

### 3. Naming Series Setup

Configure naming series for Air Freight documents to ensure proper document numbering.

#### Documents Requiring Naming Series

- **Air Shipment**: Main shipment document
- **Master Air Waybill**: Master Air Waybill document
- **Air Consolidation**: Consolidation documents

#### Setup Steps

1. Go to **Air Freight > Setup > Naming Series**
2. Create naming series for each document type
3. Set prefixes and numbering formats (e.g., AF-SHIP-.YYYY.-.#####)
4. Set as default for the respective document types

### 4. Master Data Setup

Before creating air freight shipments, set up the following master data:

#### Airlines

1. Navigate to **Air Freight > Master > Airline**
2. Create airline records with:
   - **Code**: Unique airline code
   - **Airline Name**: Full name of the airline
   - **Airline Numeric Code**: IATA numeric code
   - **Two Character Code**: IATA two-character code
   - **Three Letter Numeric Code**: ICAO three-letter code
   - **Logo**: Airline logo (optional)
   - **Is Active**: Check if the airline is currently active

#### Airports

1. Navigate to **Air Freight > Master > Airport Master**
2. Create airport records with:
   - **Airport Name**: Full name of the airport
   - **IATA Code**: 3-letter IATA code (required, unique)
   - **ICAO Code**: 4-letter ICAO code
   - **City**: City where airport is located
   - **Country**: Country where airport is located
   - **Timezone**: Airport timezone
   - **Capabilities**: Cargo hub, customs facility, dangerous goods support, etc.
   - **Is Active**: Check if the airport is currently active

#### Flight Routes

1. Navigate to **Air Freight > Master > Flight Route**
2. Create flight route records for common routes
3. Configure route details including origin, destination, and transit points

#### Flight Schedules

1. Navigate to **Air Freight > Master > Flight Schedule**
2. Create or import flight schedule records
3. Configure flight details including:
   - Flight number
   - Airline
   - Origin and destination airports
   - Scheduled times
   - Aircraft type
   - Cargo capacity

#### Unit Load Devices (ULD)

1. Navigate to **Air Freight > Master > Unit Load Device**
2. Create ULD type records if applicable
3. Configure ULD capacity and specifications

### 5. Customer and Supplier Setup

#### Shipper and Consignee

1. Ensure **Shipper** and **Consignee** master data is set up
2. These can be linked to Customer or Supplier records as needed
3. Configure addresses and contacts for shippers and consignees

#### Freight Agents

1. Set up **Freight Agent** records if using agent networks
2. Configure agent relationships and commission structures

### 6. Pricing Center Integration

If using automated rate calculation:

1. Navigate to **Pricing Center > Air Freight Rate**
2. Configure air freight rates with:
   - Origin and destination airports
   - Weight and volume ranges
   - Calculation methods
   - Valid date ranges
   - IATA rate references if applicable

### 7. Accounting Dimensions

Configure accounting dimensions for proper financial tracking:

1. **Company**: Ensure company is set up
2. **Branch**: Configure branches if using multi-branch operations
3. **Cost Center**: Set up cost centers for cost tracking
4. **Profit Center**: Configure profit centers for profitability analysis
5. **Job Costing**: Set up job costing if tracking costs by shipment

### 8. Dangerous Goods Setup

If handling dangerous goods:

1. Ensure **Dangerous Goods** master data is set up
2. Configure DG classes and substances
3. Set up emergency contact procedures
4. Configure DG compliance requirements

### 9. Custom Fields (Optional)

If you need additional fields:

1. Go to **Customize Form** for any Air Freight doctype
2. Add custom fields as per your business requirements
3. Configure field properties and validations

## Verification Checklist

After setup, verify the following:

- [ ] IATA Settings configured (if using IATA integration)
- [ ] Flight Schedule Settings configured (if using flight schedule integration)
- [ ] Naming series set up for all documents
- [ ] At least one Airline created
- [ ] At least one Airport created
- [ ] Flight Routes configured (if applicable)
- [ ] Flight Schedules configured (if applicable)
- [ ] Shipper and Consignee masters set up
- [ ] Accounting dimensions configured
- [ ] Pricing Center rates configured (if using automated pricing)
- [ ] Dangerous Goods setup completed (if handling DG)

## Common Setup Issues

### Issue: Cannot create Air Shipment
**Solution**: Ensure naming series is configured for Air Shipment document type.

### Issue: Airport not found
**Solution**: Verify that airports are created with proper IATA codes in Airport Master.

### Issue: Airline not appearing
**Solution**: Check if the airline is marked as "Is Active" in the Airline master.

### Issue: IATA messages not processing
**Solution**: Verify that IATA Settings are configured correctly with valid API credentials.

### Issue: Flight schedule not updating
**Solution**: Check Flight Schedule Settings and verify API credentials and sync settings.

### Issue: Charges not calculating
**Solution**: Verify that Air Freight Rates are configured in Pricing Center with valid date ranges.

## Next Steps

After completing the setup:

1. Review [Master Data](master-data.md) documentation
2. Learn how to create your first [Air Shipment](air-shipment.md)
3. Understand [Master Air Waybill Management](master-air-waybill.md)

---

*For detailed information on each master data type, refer to the Master Data documentation.*

