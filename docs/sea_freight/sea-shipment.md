# Sea Shipment

## Overview

Sea Shipment is the main transaction document in the Sea Freight module. It represents a single sea freight shipment from origin to destination, containing all relevant information about the cargo, parties involved, containers, packages, services, and charges.

## Purpose

The Sea Shipment document is used to:
- Track individual sea freight shipments from booking to delivery
- Manage container and package details
- Link to Master Bills for consolidated shipments
- Record services and charges
- Track milestones and shipment status
- Calculate sustainability metrics
- Generate shipping documents

## Document Structure

The Sea Shipment document is organized into the following tabs:

### Details Tab

Contains the primary shipment information:

#### Basic Information
- **Naming Series**: Document numbering series
- **Booking Date**: Date when the shipment was booked (required)
- **Shipping Status**: Current status of the shipment
- **Transport Mode**: Always "Sea" for sea freight
- **Direction**: Import, Export, or Domestic (required)
- **Shipping Line**: Ocean carrier for the shipment
- **Local Customer**: Customer for this shipment (required)
- **Freight Agent**: Freight forwarding agent if applicable

#### Shipment Classification
- **House Type**: Type of house bill (Standard House, Co-load Master, etc.)
- **Release Type**: Type of release
- **Entry Type**: Customs entry type (Customs Permit, Transshipment, ATA Carnet)
- **Service Level**: Logistics service level

#### Route Information
- **Shipper**: Party shipping the goods (required)
- **Origin Port**: Origin port UNLOCO code (required)
- **ETD**: Estimated Time of Departure
- **Consignee**: Party receiving the goods (required)
- **Destination Port**: Destination port UNLOCO code (required)
- **ETA**: Estimated Time of Arrival

#### Cargo Summary
- **Volume**: Total volume in cubic meters (cbm)
- **Weight**: Total weight in kilograms (kg)
- **Chargeable**: Chargeable weight in kilograms (kg)

### House Tab

Contains House Bill of Lading information:

#### Shipping Details
- **House BL**: House Bill of Lading number
- **Incoterm**: International commercial terms
- **Additional Terms**: Any additional terms and conditions

#### Cargo Details
- **Packs**: Number of packages
- **Inner**: Inner package count
- **Good Value**: Value of goods
- **Insurance**: Insurance value

#### Description
- **Description**: Detailed description of goods
- **Marks and Nos**: Shipping marks and numbers

### Master Tab

Contains Master Bill information:

- **Master Bill**: Link to Master Bill document if part of consolidation
- **Container Type**: Default container type
- **Vessel**: Vessel name
- **Voyage No.**: Voyage number

### Addresses Tab

Contains address and contact information:

#### Bill of Lading Addresses
- **Shipper Address**: Address of the shipper
- **Shipper Address Display**: Display of shipper address
- **Consignee Address**: Address of the consignee
- **Consignee Address Display**: Display of consignee address

#### Shipping Contacts
- **Shipper Contact**: Contact person for shipper
- **Shipper Contact Display**: Display of shipper contact
- **Consignee Contact**: Contact person for consignee
- **Consignee Contact Display**: Display of consignee contact

#### Notify Party
- **Notify To Party**: Party to be notified
- **Notify To Address**: Address for notification

### Services Tab

Contains additional services:

- **Services**: Table of Sea Freight Services
  - Service type
  - Service description
  - Service charges

### Packing Tab

Contains container and package details:

#### Containers Section
- **Containers**: Table of Sea Freight Containers
  - Container number
  - Container type
  - Seal numbers
  - Container status
- **Total Containers**: Total number of containers (auto-calculated)
- **Total TEUs**: Total TEU capacity (auto-calculated)

#### Packages Section
- **Packages**: Table of Sea Freight Packages
  - Commodity
  - HS Code
  - Number of packs
  - UOM (Unit of Measure)
  - Weight
  - Volume
  - Goods description
  - Dangerous goods information (if applicable)
  - Temperature control requirements (if applicable)
- **Total Packages**: Total number of packages (auto-calculated)
- **Total Volume**: Total volume (auto-calculated)
- **Total Weight**: Total weight (auto-calculated)

### Charges Tab

Contains charge and billing information:

#### Job Information
- **Handling Branch**: Branch handling the shipment
- **Handling Department**: Department handling the shipment
- **Recognition Date**: Date for revenue recognition
- **Job Description**: Description of the job
- **Quote No**: Link to quotation if applicable

#### Charges
- **Charges**: Table of Sea Freight Charges
  - Charge type
  - Description
  - Quantity
  - Rate
  - Amount
  - Currency
  - Charge category (Revenue or Cost)

### Accounts Tab

Contains accounting dimensions:

- **Company**: Company for accounting (required)
- **Branch**: Branch for accounting (required)
- **Cost Center**: Cost center for cost tracking (required)
- **Profit Center**: Profit center for profitability analysis (required)
- **Job Costing Number**: Job costing number for cost tracking

### Milestones Tab

Contains milestone tracking:

- **Milestone HTML**: Visual display of shipment milestones and status

### Connections Tab

Contains linked documents and relationships:

- Shows connections to related documents like Master Bill, Consolidation, etc.

### Notes Tab

Contains internal and external notes:

- **External Notes**: Notes visible to customers
- **Internal Notes**: Internal notes for operations team

### Sustainability Tab

Contains sustainability metrics:

- **Estimated Carbon Footprint**: Estimated carbon emissions
- **Estimated Fuel Consumption**: Estimated fuel consumption
- **Sustainability Notes**: Notes on sustainability measures

### Alerts Tab

Contains delay and penalty alerts:

#### Delay Alerts
- **Has Delays**: Checkbox indicating if there are delays
- **Delay Count**: Number of delays
- **Last Delay Check**: Date of last delay check
- **Delay Alert Sent**: Whether delay alert has been sent

#### Penalty Alerts
- **Has Penalties**: Checkbox indicating if there are penalties
- **Detention Days**: Number of detention days
- **Demurrage Days**: Number of demurrage days
- **Free Time Days**: Free time allowed
- **Penalty Alert Sent**: Whether penalty alert has been sent
- **Last Penalty Check**: Date of last penalty check
- **Estimated Penalty Amount**: Estimated penalty amount

## Creating a Sea Shipment

### Step 1: Basic Information

1. Navigate to **Sea Freight > Transactions > Sea Shipment**
2. Click **New**
3. Select the **Naming Series**
4. Enter the **Booking Date**
5. Select **Direction** (Import/Export/Domestic)
6. Select **Local Customer** (required)
7. Select **Shipping Line**

### Step 2: Route Information

1. Select **Shipper** (required)
2. Select **Origin Port** (required) - use UNLOCO code
3. Enter **ETD** (Estimated Time of Departure)
4. Select **Consignee** (required)
5. Select **Destination Port** (required) - use UNLOCO code
6. Enter **ETA** (Estimated Time of Arrival)

### Step 3: House Bill Information

1. Go to **House Tab**
2. Enter **House BL** number if available
3. Select **Incoterm** if applicable
4. Enter cargo details (packs, weight, volume, value)
5. Enter **Description** of goods
6. Enter **Marks and Nos** if applicable

### Step 4: Master Bill Linking

1. Go to **Master Tab**
2. If part of consolidation, select **Master Bill**
3. Enter **Vessel** name
4. Enter **Voyage No.**
5. Select **Container Type** if applicable

### Step 5: Containers

1. Go to **Packing Tab**
2. In **Containers Section**, click **Add Row**
3. Enter container details:
   - Container number
   - Container type
   - Seal numbers
   - Status
4. System will auto-calculate **Total Containers** and **Total TEUs**

### Step 6: Packages

1. In **Packing Tab**, go to **Packages Section**
2. Click **Add Row**
3. Enter package details:
   - Commodity
   - HS Code
   - Number of packs
   - UOM
   - Weight
   - Volume
   - Goods description
4. If dangerous goods, enter DG information
5. If temperature controlled, enter temperature requirements
6. System will auto-calculate totals

### Step 7: Services

1. Go to **Services Tab**
2. Click **Add Row** to add services
3. Select service type and enter details
4. Enter service charges if applicable

### Step 8: Charges

1. Go to **Charges Tab**
2. Enter **Handling Branch** and **Department** if applicable
3. Enter **Recognition Date** for revenue recognition
4. In **Charges** table, click **Add Row**
5. Enter charge details:
   - Charge type
   - Description
   - Quantity
   - Rate
   - Amount
   - Currency
   - Category (Revenue or Cost)
6. Alternatively, link to Pricing Center for automated rate calculation

### Step 9: Accounting

1. Go to **Accounts Tab**
2. Select **Company** (required)
3. Select **Branch** (required)
4. Select **Cost Center** (required)
5. Select **Profit Center** (required)
6. Select **Job Costing Number** if using job costing

### Step 10: Addresses and Contacts

1. Go to **Addresses Tab**
2. Select **Shipper Address** and **Shipper Contact**
3. Select **Consignee Address** and **Consignee Contact**
4. Enter **Notify To Party** and **Notify To Address** if applicable

### Step 11: Save and Submit

1. Review all information
2. Add any **Internal Notes** or **External Notes** in Notes Tab
3. Click **Save**
4. Click **Submit** to finalize the shipment

## Status Management

The Sea Shipment document supports status tracking through the **Shipping Status** field. Common statuses include:

- **Draft**: Initial creation
- **Booked**: Booking confirmed
- **In Transit**: Shipment in transit
- **Arrived**: Arrived at destination
- **Delivered**: Delivered to consignee
- **Cancelled**: Cancelled shipment

## Linking to Master Bill

If the shipment is part of a consolidation:

1. Create or identify the **Master Bill**
2. In Sea Shipment, go to **Master Tab**
3. Select the **Master Bill**
4. The shipment will be linked to the consolidation

## Charge Calculation

Charges can be entered manually or calculated automatically:

### Manual Entry
1. Go to **Charges Tab**
2. Add rows in **Charges** table
3. Enter charge details manually

### Automated Calculation
1. Ensure **Sea Freight Rates** are configured in Pricing Center
2. System will calculate charges based on:
   - Origin and destination ports
   - Container type
   - Weight and volume
   - Service level
3. Charges will be populated automatically

## Milestone Tracking

The **Milestones Tab** provides visual tracking of shipment progress:

- Shows key milestones and their status
- Displays estimated and actual dates
- Highlights delays and issues

## Alerts and Notifications

The **Alerts Tab** tracks:

- **Delay Alerts**: Automatically detects delays in milestones
- **Penalty Alerts**: Tracks detention, demurrage, and free time
- Alerts can be configured to send notifications

## Best Practices

1. **Complete Information**: Fill in all required fields before submitting
2. **Accurate Ports**: Use correct UNLOCO codes for ports
3. **Container Details**: Enter accurate container numbers and types
4. **Package Information**: Ensure weight and volume are accurate
5. **Charge Categories**: Properly categorize charges as Revenue or Cost
6. **Accounting Dimensions**: Always set accounting dimensions for proper financial tracking
7. **Status Updates**: Update shipping status as shipment progresses
8. **Document Linking**: Link to Master Bill if part of consolidation

## Related Documents

- **Master Bill**: For consolidated shipments
- **Sea Freight Consolidation**: For consolidation operations
- **Quotation**: Can be linked via Quote No field
- **Job Costing Number**: For cost tracking

## Reports

The following reports are available for Sea Shipment:

- Sea Freight Performance Dashboard
- Sea Freight Revenue Analysis
- Sea Freight Cost Analysis
- On-Time Performance Report
- Container Utilization Report

## Next Steps

- Learn about [Master Bill Management](master-bill.md)
- Understand [Sea Freight Consolidation](sea-freight-consolidation.md)
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

