## Overview

Air Shipment is the main transaction document in the Air Freight module. It represents a single air freight shipment from origin to destination, containing all relevant information about the cargo, parties involved, packages, services, charges, and IATA compliance tracking.

## Purpose

The Air Shipment document is used to:
- Track individual air freight shipments from booking to delivery
- Manage package details and ULD assignments
- Link to Master Air Waybills for consolidated shipments
- Track Dangerous Goods (DG) declarations and compliance
- Record services and charges
- Track milestones and shipment status
- Integrate with IATA systems for status updates
- Calculate sustainability metrics
- Generate shipping documents

## Document Structure

The Air Shipment document is organized into the following tabs:

### Milestones Tab

Contains visual milestone tracking:

- **Milestone HTML**: Visual dashboard showing shipment milestones and their status
- Displays estimated and actual dates
- Highlights delays and issues

### Details Tab

Contains the primary shipment information:

#### Basic Information
- **Naming Series**: Document numbering series
- **Booking Date**: Date when the shipment was booked (required)
- **House Type**: Type of house air waybill
- **Direction**: Import, Export, or Domestic (required)
- **Airline**: Airline carrier for the shipment
- **Local Customer**: Customer for this shipment (required)
- **Freight Agent**: Freight forwarding agent if applicable

#### Shipment Classification
- **Release Type**: Type of release
- **Entry Type**: Customs entry type (Customs Permit, Transshipment, ATA Carnet)
- **Service Level**: Service level agreement

#### Route Information
- **Shipper**: Party shipping the goods (required)
- **Origin Port**: Origin airport/port (required)
- **ETD**: Estimated Time of Departure
- **Consignee**: Party receiving the goods (required)
- **Destination Port**: Destination airport/port (required)
- **ETA**: Estimated Time of Arrival

#### Cargo Summary
- **Volume**: Total volume in cubic meters (cbm)
- **Weight**: Total weight in kilograms (kg)
- **Chargeable**: Chargeable weight in kilograms (kg)

### House Tab

Contains House Air Waybill information:

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

### Packing Tab

Contains package details:

- **Packages**: Table of Air Shipment Packages
  - Commodity
  - HS Code
  - Number of packs
  - UOM (Unit of Measure)
  - Weight
  - Volume
  - Goods description
  - Dangerous goods information (if applicable)
  - Temperature control requirements (if applicable)

### Master Tab

Contains Master Air Waybill information:

- **Master AWB**: Link to Master Air Waybill document if part of consolidation

#### IATA Integration
- **IATA Status**: Current IATA status
- **IATA Message ID**: IATA message identifier
- **Last Status Update**: Last IATA status update timestamp
- **House AWB Number**: House Air Waybill number
- **Booking Reference**: Booking reference number
- **Agent Reference**: Agent reference number

### Dangerous Goods Tab

Contains Dangerous Goods declaration information:

- **Contains Dangerous Goods**: Checkbox indicating if shipment contains DG
- **DG Declaration Complete**: Checkbox indicating if DG declaration is complete
- **DG Compliance Status**: Compliance status (Compliant, Non-Compliant, Under Review, Pending Documentation)
- **DG Emergency Contact**: Emergency contact person
- **DG Emergency Phone**: Emergency phone number
- **DG Emergency Email**: Emergency email address

### Services Tab

Contains additional services:

- **Services**: Table of Air Shipment Services
  - Service type
  - Service description
  - Service charges

### Charges Tab

Contains charge and billing information:

- **Charges**: Table of Air Shipment Charges
  - Charge type
  - Description
  - Quantity
  - Rate
  - Amount
  - Currency
  - Charge category (Revenue or Cost)

### Contacts & Addresses Tab

Contains address and contact information:

#### Addresses
- **Shipper Address**: Address of the shipper
- **Shipper Address Display**: Display of shipper address
- **Consignee Address**: Address of the consignee
- **Consignee Address Display**: Display of consignee address
- **Notify Party**: Party to be notified
- **Notify Party Address**: Address for notification

#### Contacts
- **Shipper Contact**: Contact person for shipper
- **Shipper Contact Display**: Display of shipper contact
- **Consignee Contact**: Contact person for consignee
- **Consignee Contact Display**: Display of consignee contact

### ULD Tab

Contains Unit Load Device information:

- **ULD Type**: Type of ULD
- **ULD Number**: ULD number
- **ULD Capacity (KG)**: ULD capacity in kilograms
- **ULD Position**: ULD position on aircraft
- **ULD Tracking Status**: ULD tracking status

### Customs Tab

Contains customs information:

- **Customs Declaration Number**: Customs declaration number
- **Customs Status**: Customs clearance status
- **Customs Broker**: Customs broker information
- **Duty Amount**: Customs duty amount
- **Tax Amount**: Tax amount
- **Customs Clearance Date**: Date of customs clearance
- **Customs Notes**: Customs-related notes

### Insurance Tab

Contains insurance information:

- **Insurance Provider**: Insurance provider
- **Insurance Policy Number**: Insurance policy number
- **Insurance Value**: Insurance value
- **Insurance Claim Number**: Claim number if applicable
- **Insurance Claim Status**: Claim status
- **Insurance Claim Date**: Claim date

### Temperature Tab

Contains temperature control information:

- **Requires Temperature Control**: Checkbox indicating if temperature control is required
- **Min Temperature**: Minimum temperature requirement
- **Max Temperature**: Maximum temperature requirement
- **Temperature Monitoring**: Temperature monitoring method
- **Cold Chain Compliance**: Cold chain compliance status
- **Temperature Log**: Temperature log information

### Documents Tab

Contains document information:

- **Commercial Invoice Number**: Commercial invoice number
- **Packing List Number**: Packing list number
- **Certificate of Origin**: Certificate of origin
- **Export License**: Export license number
- **Import Permit**: Import permit number
- **Other Documents**: Other document references

### Sustainability Tab

Contains sustainability metrics:

- **Estimated Carbon Footprint**: Estimated carbon emissions
- **Estimated Fuel Consumption**: Estimated fuel consumption
- **Sustainability Notes**: Notes on sustainability measures

### Accounts Tab

Contains accounting dimensions:

- **Company**: Company for accounting (required)
- **Branch**: Branch for accounting
- **Cost Center**: Cost center for cost tracking
- **Profit Center**: Profit center for profitability analysis
- **Job Costing Number**: Job costing number for cost tracking

## Creating an Air Shipment

### Step 1: Basic Information

1. Navigate to **Air Freight > Transactions > Air Shipment**
2. Click **New**
3. Select the **Naming Series**
4. Enter the **Booking Date** (required)
5. Select **Direction** (Import/Export/Domestic) (required)
6. Select **Local Customer** (required)
7. Select **Airline**

### Step 2: Route Information

1. Select **Shipper** (required)
2. Select **Origin Port** (required) - use airport/port code
3. Enter **ETD** (Estimated Time of Departure)
4. Select **Consignee** (required)
5. Select **Destination Port** (required) - use airport/port code
6. Enter **ETA** (Estimated Time of Arrival)

### Step 3: House Air Waybill Information

1. Go to **House Tab**
2. Enter **House BL** number if available
3. Select **Incoterm** if applicable
4. Enter cargo details (packs, weight, volume, value)
5. Enter **Description** of goods
6. Enter **Marks and Nos** if applicable

### Step 4: Master AWB Linking

1. Go to **Master Tab**
2. If part of consolidation, select **Master AWB**
3. Enter **House AWB Number** if available
4. Enter **Booking Reference** if applicable
5. Enter **Agent Reference** if applicable

### Step 5: IATA Integration

1. In **Master Tab**, go to **IATA Integration** section
2. System will automatically update IATA status if IATA integration is configured
3. Monitor **IATA Status** and **Last Status Update**

### Step 6: Packages

1. Go to **Packing Tab**
2. In **Packages** table, click **Add Row**
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

### Step 7: Dangerous Goods

1. Go to **Dangerous Goods Tab**
2. Check **Contains Dangerous Goods** if applicable
3. Complete DG declaration:
   - Enter DG emergency contact information
   - Complete DG declaration in packages
   - Update **DG Compliance Status**
4. Check **DG Declaration Complete** when done

### Step 8: ULD Assignment

1. Go to **ULD Tab**
2. Enter ULD details:
   - ULD Type
   - ULD Number
   - ULD Capacity
   - ULD Position
   - ULD Tracking Status

### Step 9: Services

1. Go to **Services Tab**
2. Click **Add Row** to add services
3. Select service type and enter details
4. Enter service charges if applicable

### Step 10: Charges

1. Go to **Charges Tab**
2. In **Charges** table, click **Add Row**
3. Enter charge details:
   - Charge type
   - Description
   - Quantity
   - Rate
   - Amount
   - Currency
   - Category (Revenue or Cost)
4. Alternatively, link to Pricing Center for automated rate calculation

### Step 11: Accounting

1. Go to **Accounts Tab**
2. Select **Company** (required)
3. Select **Branch** if applicable
4. Select **Cost Center** if applicable
5. Select **Profit Center** if applicable
6. Select **Job Costing Number** if using job costing

### Step 12: Addresses and Contacts

1. Go to **Contacts & Addresses Tab**
2. Select **Shipper Address** and **Shipper Contact**
3. Select **Consignee Address** and **Consignee Contact**
4. Enter **Notify Party** and **Notify Party Address** if applicable

### Step 13: Save and Submit

1. Review all information
2. Check milestone status in **Milestones Tab**
3. Verify DG compliance if applicable
4. Click **Save**
5. Click **Submit** to finalize the shipment

## Milestone Tracking

The **Milestones Tab** provides visual tracking of shipment progress:

- Shows key milestones and their status
- Displays estimated and actual dates
- Highlights delays and issues
- Provides real-time status updates

## IATA Integration

The Air Shipment document supports IATA integration:

- **IATA Status**: Automatically updated from IATA messages
- **IATA Message ID**: Tracks IATA message processing
- **Last Status Update**: Timestamp of last IATA status update
- **Auto-Update**: System can automatically update status from IATA messages

## Dangerous Goods Management

For shipments containing dangerous goods:

1. Check **Contains Dangerous Goods** in Dangerous Goods Tab
2. Enter DG information in package details
3. Complete DG declaration
4. Enter emergency contact information
5. Update **DG Compliance Status**
6. Check **DG Declaration Complete** when declaration is complete

## Best Practices

1. **Complete Information**: Fill in all required fields before submitting
2. **Accurate Airports**: Use correct airport codes for origin and destination
3. **Package Information**: Ensure weight and volume are accurate
4. **DG Compliance**: Complete DG declarations accurately and completely
5. **IATA Integration**: Monitor IATA status updates regularly
6. **Charge Categories**: Properly categorize charges as Revenue or Cost
7. **Accounting Dimensions**: Always set accounting dimensions for proper financial tracking
8. **Milestone Monitoring**: Monitor milestones for on-time performance
9. **Document Linking**: Link to Master AWB if part of consolidation

## Related Documents

- **Master Air Waybill**: For consolidated shipments
- **Air Consolidation**: For consolidation operations
- **Quotation**: Can be linked via Quote No field
- **Job Costing Number**: For cost tracking

## Reports

The following reports are available for Air Shipment:

- Air Freight Performance Dashboard
- Air Freight Revenue Analysis
- Air Freight Cost Analysis
- On-Time Performance Report
- Dangerous Goods Compliance Report
- Airline Performance Report

## Next Steps

- Learn about [Master Air Waybill Management](master-air-waybill.md)
- Understand [Air Consolidation](air-consolidation.md)
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

