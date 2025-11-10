## Overview

Air Consolidation is a document used to manage consolidated cargo operations where multiple air freight shipments are combined into a single consolidation for transportation. This document helps track consolidated cargo, calculate consolidation ratios, and manage costs across multiple shipments.

## Purpose

The Air Consolidation document is used to:
- Manage consolidation operations for multiple air freight shipments
- Track consolidated cargo details (packages, weight, volume)
- Calculate consolidation ratios and costs
- Link multiple Air Shipments to a consolidation
- Manage consolidation routing and charges
- Track consolidation status and milestones
- Validate dangerous goods segregation

## Document Structure

The Air Consolidation document contains the following sections:

### Consolidation Information

- **Naming Series**: Document numbering series (required)
- **Consolidation Date**: Date of consolidation (required)
- **Consolidation Type**: Type of consolidation (required)
  - Direct Consolidation
  - Transit Consolidation
  - Break-Bulk Consolidation
  - Multi-Country Consolidation
- **Status**: Consolidation status (required)
  - Draft
  - Planning
  - In Progress
  - Ready for Departure
  - In Transit
  - Delivered
  - Cancelled
- **Priority**: Priority level (Low, Normal, High, Urgent)
- **Consolidation Agent**: User responsible for the consolidation

### Route Information

- **Origin Airport**: Origin airport (required)
- **Destination Airport**: Destination airport (required)
- **Departure Date**: Departure date and time (required)
- **Arrival Date**: Arrival date and time (required)
- **Airline**: Airline for the consolidation (required)
- **Flight Number**: Flight number (required)

### Cargo Summary

Auto-calculated fields based on attached shipments:

- **Total Packages**: Total number of packages
- **Total Weight**: Total weight in kilograms
- **Total Volume**: Total volume in cubic meters
- **Chargeable Weight**: Chargeable weight in kilograms
- **Consolidation Ratio**: Consolidation ratio percentage
- **Cost per kg**: Cost per kilogram

### Documents

- **Master AWB**: Link to Master Air Waybill document
- **House AWB Prefix**: Prefix for house air waybill numbers
- **Customs Declaration**: Customs declaration number
- **Export License**: Export license number

### Notes & Instructions

- **Consolidation Notes**: General notes about the consolidation
- **Special Instructions**: Special handling instructions
- **Quality Control Notes**: Quality control requirements
- **Handling Requirements**: Handling and storage requirements

### Packages Tab

- **Consolidation Packages**: Table of packages in the consolidation
  - Commodity
  - HS Code
  - Number of packs
  - Weight
  - Volume
  - Goods description

### Routes Tab

- **Consolidation Routes**: Table of routing information
  - Origin airport
  - Destination airport
  - Transit airports
  - Routing details

### Charges Tab

- **Consolidation Charges**: Table of charges for the consolidation
  - Charge type
  - Description
  - Quantity
  - Rate
  - Amount
  - Currency

### Shipments Tab

- **Attached Air Freight Jobs**: Table of Air Shipments linked to this consolidation
  - Air Shipment reference
  - Shipment details
  - Status

### Accounts Tab

Accounting dimensions (all required):

- **Company**: Company for accounting (required)
- **Branch**: Branch for accounting (required)
- **Cost Center**: Cost center for cost tracking (required)
- **Profit Center**: Profit center for profitability analysis (required)
- **Job Costing Number**: Job costing number for cost tracking

## Creating an Air Consolidation

### Step 1: Basic Information

1. Navigate to **Air Freight > Transactions > Air Consolidation**
2. Click **New**
3. Select **Naming Series** (required)
4. Enter **Consolidation Date** (required)
5. Select **Consolidation Type** (required)
6. Select **Status** (default: Draft)
7. Select **Priority** if applicable
8. Select **Consolidation Agent** if applicable

### Step 2: Route Information

1. Select **Origin Airport** (required)
2. Select **Destination Airport** (required)
3. Enter **Departure Date** (required)
4. Enter **Arrival Date** (required)
5. Select **Airline** (required)
6. Enter **Flight Number** (required)

### Step 3: Link Master AWB

1. In **Documents** section, select **Master AWB** if applicable
2. Enter **House AWB Prefix** if using a prefix for house air waybills
3. Enter **Customs Declaration** number if applicable
4. Enter **Export License** number if applicable

### Step 4: Add Shipments

1. Go to **Shipments Tab**
2. In **Attached Air Freight Jobs** table, click **Add Row**
3. Select **Air Shipment** to link
4. Repeat for all shipments in the consolidation
5. System will auto-calculate cargo summary from attached shipments

### Step 5: Packages

1. Go to **Packages Tab**
2. In **Consolidation Packages** table, click **Add Row**
3. Enter package details:
   - Commodity
   - HS Code
   - Number of packs
   - Weight
   - Volume
   - Goods description
4. System will update package totals automatically

### Step 6: Routes

1. Go to **Routes Tab** (if using multi-airport routing)
2. In **Consolidation Routes** table, click **Add Row**
3. Enter routing information:
   - Origin airport
   - Destination airport
   - Transit airports
   - Routing details

### Step 7: Charges

1. Go to **Charges Tab**
2. In **Consolidation Charges** table, click **Add Row**
3. Enter charge details:
   - Charge type
   - Description
   - Quantity
   - Rate
   - Amount
   - Currency

### Step 8: Accounting

1. Go to **Accounts Tab**
2. Select **Company** (required)
3. Select **Branch** (required)
4. Select **Cost Center** (required)
5. Select **Profit Center** (required)
6. Select **Job Costing Number** if using job costing

### Step 9: Notes

1. Enter **Consolidation Notes** if applicable
2. Enter **Special Instructions** if applicable
3. Enter **Quality Control Notes** if applicable
4. Enter **Handling Requirements** if applicable

### Step 10: Save and Submit

1. Review all information
2. Verify cargo summary calculations
3. Verify dangerous goods segregation if applicable
4. Click **Save**
5. Click **Submit** to finalize the consolidation

## Status Management

The consolidation document supports status tracking:

- **Draft**: Initial creation
- **Planning**: Consolidation being planned
- **In Progress**: Consolidation in progress
- **Ready for Departure**: Ready to depart
- **In Transit**: In transit
- **Delivered**: Delivered
- **Cancelled**: Cancelled

## Consolidation Types

### Direct Consolidation
Multiple shipments consolidated directly at origin for direct transport to destination.

### Transit Consolidation
Consolidation that transits through intermediate airports.

### Break-Bulk Consolidation
Consolidation that is broken down at intermediate points.

### Multi-Country Consolidation
Consolidation involving multiple countries in the routing.

## Auto-Calculations

The system automatically calculates:

- **Total Packages**: Sum of packages from attached shipments
- **Total Weight**: Sum of weights from attached shipments
- **Total Volume**: Sum of volumes from attached shipments
- **Chargeable Weight**: Calculated chargeable weight
- **Consolidation Ratio**: Ratio of consolidation efficiency
- **Cost per kg**: Cost per kilogram based on charges

## Linking Shipments

To link Air Shipments to a consolidation:

1. Create or open the **Air Consolidation**
2. Go to **Shipments Tab**
3. In **Attached Air Freight Jobs** table, add rows
4. Select **Air Shipment** documents to link
5. System will aggregate cargo details from linked shipments

Alternatively, link from Air Shipment:

1. Open the **Air Shipment** document
2. Go to **Master Tab**
3. Select the **Master AWB** linked to the consolidation
4. The shipment will be associated with the consolidation

## Dangerous Goods Segregation

The system validates dangerous goods segregation in consolidations:

- Ensures incompatible DG classes are not consolidated together
- Validates DG compliance before consolidation
- Tracks DG segregation requirements

## Best Practices

1. **Complete Route Information**: Ensure all route details are accurate
2. **Accurate Dates**: Enter correct departure and arrival dates
3. **Link All Shipments**: Link all related shipments to the consolidation
4. **Verify Calculations**: Review auto-calculated cargo summary
5. **Accounting Dimensions**: Always set accounting dimensions
6. **Status Updates**: Update status as consolidation progresses
7. **Document Linking**: Link Master AWB for proper document management
8. **Charge Management**: Properly categorize and track consolidation charges
9. **DG Segregation**: Verify dangerous goods segregation compliance

## Related Documents

- **Air Shipment**: House Air Waybills linked to this consolidation
- **Master Air Waybill**: Master Air Waybill for the consolidation
- **Airline**: Airline information
- **Job Costing Number**: For cost tracking

## Reports

Consolidation data is included in:
- Air Freight Performance Dashboard
- Air Freight Revenue Analysis
- Air Freight Cost Analysis
- Air Consolidation Report
- Route Analysis Report

## Next Steps

- Learn about [Air Shipment](air-shipment.md) management
- Understand [Master Air Waybill](master-air-waybill.md) operations
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

