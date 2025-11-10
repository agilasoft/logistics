# Sea Freight Consolidation

## Overview

Sea Freight Consolidation is a document used to manage consolidated cargo operations where multiple shipments are combined into a single consolidation for transportation. This document helps track consolidated cargo, calculate consolidation ratios, and manage costs across multiple shipments.

## Purpose

The Sea Freight Consolidation document is used to:
- Manage consolidation operations for multiple shipments
- Track consolidated cargo details (containers, packages, weight, volume)
- Calculate consolidation ratios and costs
- Link multiple Sea Shipments to a consolidation
- Manage consolidation routing and charges
- Track consolidation status and milestones

## Document Structure

The Sea Freight Consolidation document contains the following sections:

### Consolidation Information

- **Naming Series**: Document numbering series (required)
- **Consolidation Date**: Date of consolidation (required)
- **Consolidation Type**: Type of consolidation (required)
  - Direct Consolidation
  - Transit Consolidation
  - Break-Bulk Consolidation
  - Multi-Port Consolidation
- **Status**: Consolidation status (required)
  - Draft
  - Planning
  - In Progress
  - Ready for Departure
  - In Transit
  - Arrived
  - Delivered
  - Cancelled
- **Priority**: Priority level (Low, Normal, High, Urgent)
- **Consolidation Agent**: User responsible for the consolidation

### Route Information

- **Origin Port**: Origin port UNLOCO code (required)
- **Destination Port**: Destination port UNLOCO code (required)
- **ETD**: Estimated Time of Departure (required)
- **ETA**: Estimated Time of Arrival (required)
- **Shipping Line**: Shipping line for the consolidation (required)
- **Vessel Name**: Vessel name (required)
- **Voyage Number**: Voyage number (required)

### Cargo Summary

Auto-calculated fields based on attached shipments:

- **Total Containers**: Total number of containers
- **Total Packages**: Total number of packages
- **Total Weight**: Total weight in kilograms
- **Total Volume**: Total volume in cubic meters
- **Chargeable Weight**: Chargeable weight in kilograms
- **Consolidation Ratio**: Consolidation ratio percentage
- **Cost per kg**: Cost per kilogram

### Documents

- **Master Bill**: Link to Master Bill document
- **House Bill Prefix**: Prefix for house bill numbers
- **Customs Declaration**: Customs declaration number
- **Export License**: Export license number

### Notes & Instructions

- **Consolidation Notes**: General notes about the consolidation
- **Special Instructions**: Special handling instructions
- **Quality Control Notes**: Quality control requirements
- **Handling Requirements**: Handling and storage requirements

### Containers Tab

- **Consolidation Containers**: Table of containers in the consolidation
  - Container number
  - Container type
  - Seal numbers
  - Status

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
  - Origin port
  - Destination port
  - Transit ports
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

- **Attached Sea Shipments**: Table of Sea Shipments linked to this consolidation
  - Sea Shipment reference
  - Shipment details
  - Status

### Accounts Tab

Accounting dimensions (all required):

- **Company**: Company for accounting (required)
- **Branch**: Branch for accounting (required)
- **Cost Center**: Cost center for cost tracking (required)
- **Profit Center**: Profit center for profitability analysis (required)
- **Job Costing Number**: Job costing number for cost tracking

## Creating a Sea Freight Consolidation

### Step 1: Basic Information

1. Navigate to **Sea Freight > Transactions > Sea Freight Consolidation**
2. Click **New**
3. Select **Naming Series** (required)
4. Enter **Consolidation Date** (required)
5. Select **Consolidation Type** (required)
6. Select **Status** (default: Draft)
7. Select **Priority** if applicable
8. Select **Consolidation Agent** if applicable

### Step 2: Route Information

1. Select **Origin Port** (required) - use UNLOCO code
2. Select **Destination Port** (required) - use UNLOCO code
3. Enter **ETD** (required)
4. Enter **ETA** (required)
5. Select **Shipping Line** (required)
6. Enter **Vessel Name** (required)
7. Enter **Voyage Number** (required)

### Step 3: Link Master Bill

1. In **Documents** section, select **Master Bill** if applicable
2. Enter **House Bill Prefix** if using a prefix for house bills
3. Enter **Customs Declaration** number if applicable
4. Enter **Export License** number if applicable

### Step 4: Add Shipments

1. Go to **Shipments Tab**
2. In **Attached Sea Shipments** table, click **Add Row**
3. Select **Sea Shipment** to link
4. Repeat for all shipments in the consolidation
5. System will auto-calculate cargo summary from attached shipments

### Step 5: Containers

1. Go to **Containers Tab**
2. In **Consolidation Containers** table, click **Add Row**
3. Enter container details:
   - Container number
   - Container type
   - Seal numbers
   - Status
4. System will update **Total Containers** automatically

### Step 6: Packages

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

### Step 7: Routes

1. Go to **Routes Tab** (if using multi-port routing)
2. In **Consolidation Routes** table, click **Add Row**
3. Enter routing information:
   - Origin port
   - Destination port
   - Transit ports
   - Routing details

### Step 8: Charges

1. Go to **Charges Tab**
2. In **Consolidation Charges** table, click **Add Row**
3. Enter charge details:
   - Charge type
   - Description
   - Quantity
   - Rate
   - Amount
   - Currency

### Step 9: Accounting

1. Go to **Accounts Tab**
2. Select **Company** (required)
3. Select **Branch** (required)
4. Select **Cost Center** (required)
5. Select **Profit Center** (required)
6. Select **Job Costing Number** if using job costing

### Step 10: Notes

1. Enter **Consolidation Notes** if applicable
2. Enter **Special Instructions** if applicable
3. Enter **Quality Control Notes** if applicable
4. Enter **Handling Requirements** if applicable

### Step 11: Save and Submit

1. Review all information
2. Verify cargo summary calculations
3. Click **Save**
4. Click **Submit** to finalize the consolidation

## Status Management

The consolidation document supports status tracking:

- **Draft**: Initial creation
- **Planning**: Consolidation being planned
- **In Progress**: Consolidation in progress
- **Ready for Departure**: Ready to depart
- **In Transit**: In transit
- **Arrived**: Arrived at destination
- **Delivered**: Delivered
- **Cancelled**: Cancelled

## Consolidation Types

### Direct Consolidation
Multiple shipments consolidated directly at origin for direct transport to destination.

### Transit Consolidation
Consolidation that transits through intermediate ports.

### Break-Bulk Consolidation
Consolidation that is broken down at intermediate points.

### Multi-Port Consolidation
Consolidation involving multiple ports in the routing.

## Auto-Calculations

The system automatically calculates:

- **Total Containers**: Sum of containers from attached shipments
- **Total Packages**: Sum of packages from attached shipments
- **Total Weight**: Sum of weights from attached shipments
- **Total Volume**: Sum of volumes from attached shipments
- **Chargeable Weight**: Calculated chargeable weight
- **Consolidation Ratio**: Ratio of consolidation efficiency
- **Cost per kg**: Cost per kilogram based on charges

## Linking Shipments

To link Sea Shipments to a consolidation:

1. Create or open the **Sea Freight Consolidation**
2. Go to **Shipments Tab**
3. In **Attached Sea Shipments** table, add rows
4. Select **Sea Shipment** documents to link
5. System will aggregate cargo details from linked shipments

Alternatively, link from Sea Shipment:

1. Open the **Sea Shipment** document
2. Go to **Master Tab**
3. Select the **Master Bill** linked to the consolidation
4. The shipment will be associated with the consolidation

## Best Practices

1. **Complete Route Information**: Ensure all route details are accurate
2. **Accurate Dates**: Enter correct ETD and ETA dates
3. **Link All Shipments**: Link all related shipments to the consolidation
4. **Verify Calculations**: Review auto-calculated cargo summary
5. **Accounting Dimensions**: Always set accounting dimensions
6. **Status Updates**: Update status as consolidation progresses
7. **Document Linking**: Link Master Bill for proper document management
8. **Charge Management**: Properly categorize and track consolidation charges

## Related Documents

- **Sea Shipment**: House Bills linked to this consolidation
- **Master Bill**: Master Bill of Lading for the consolidation
- **Shipping Line**: Shipping line information
- **Job Costing Number**: For cost tracking

## Reports

Consolidation data is included in:
- Sea Freight Performance Dashboard
- Sea Freight Revenue Analysis
- Sea Freight Cost Analysis
- Container Utilization Report

## Next Steps

- Learn about [Sea Shipment](sea-shipment.md) management
- Understand [Master Bill](master-bill.md) operations
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

