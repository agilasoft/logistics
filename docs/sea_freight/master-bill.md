# Master Bill

## Overview

Master Bill (Master Bill of Lading) is a document that represents the main bill of lading issued by the shipping line or carrier for consolidated cargo. It contains information about the vessel, voyage, and consolidated shipment, and can be linked to multiple House Bills (Sea Shipments).

## Purpose

The Master Bill document is used to:
- Track Master Bills of Lading issued by shipping lines
- Manage vessel and voyage information
- Link multiple House Bills to a single Master Bill
- Track container yard and terminal operations
- Manage consolidation operations

## Document Structure

The Master Bill document contains the following sections:

### Basic Information

- **Master BL**: Master Bill of Lading number (unique, required)
- **Master Type**: Type of master bill
  - Direct
  - Co-Load
  - Agent Consolidation
  - Charter
  - Courier
  - Other
- **Charted Vessel**: Checkbox indicating if vessel is chartered

### Shipping Line Information

- **Shipping Line**: Link to Shipping Line master
- **Vessel**: Vessel name
- **Voyage No.**: Voyage number

### Consolidation Information

- **Consolidator**: Link to Freight Consolidator
- **Sending Agent**: Freight agent at origin
- **Receiving Agent**: Freight agent at destination

### Departure Tab

Contains origin port information:

- **Origin CTO**: Cargo Terminal Operator at origin
- **Origin CFS**: Container Freight Station at origin
- **Container Yard**: Container yard at origin
- **Receipt Requested**: Date when cargo receipt is requested
- **Dispatch Requested**: Date when dispatch is requested
- **Departure**: Departure date

### Arrival Tab

Contains destination port information:

- **Destination CTO**: Cargo Terminal Operator at destination
- **Destination CFS**: Container Freight Station at destination
- **Container Yard**: Container yard at destination
- **Receipt Requested**: Date when cargo receipt is requested
- **Dispatch Requested**: Date when dispatch is requested
- **Arrival**: Arrival date

### Connections Tab

Shows linked documents and relationships:
- Linked Sea Shipments (House Bills)
- Related consolidations
- Related documents

## Creating a Master Bill

### Step 1: Basic Information

1. Navigate to **Sea Freight > Master > Master Bill**
2. Click **New**
3. Enter **Master BL** number (unique identifier)
4. Select **Master Type**
5. Check **Charted Vessel** if applicable

### Step 2: Shipping Line Information

1. Select **Shipping Line**
2. Enter **Vessel** name
3. Enter **Voyage No.**

### Step 3: Consolidation Information

1. Select **Consolidator** if applicable
2. Select **Sending Agent** (origin agent)
3. Select **Receiving Agent** (destination agent)

### Step 4: Departure Information

1. Go to **Departure Tab**
2. Select **Origin CTO** (Cargo Terminal Operator)
3. Select **Origin CFS** (Container Freight Station) if applicable
4. Select **Container Yard** at origin
5. Enter **Receipt Requested** date
6. Enter **Dispatch Requested** date
7. Enter **Departure** date

### Step 5: Arrival Information

1. Go to **Arrival Tab**
2. Select **Destination CTO**
3. Select **Destination CFS** if applicable
4. Select **Container Yard** at destination
5. Enter **Receipt Requested** date
6. Enter **Dispatch Requested** date
7. Enter **Arrival** date

### Step 6: Save

1. Review all information
2. Click **Save**

## Linking House Bills to Master Bill

To link Sea Shipments (House Bills) to a Master Bill:

1. Open the **Sea Shipment** document
2. Go to **Master Tab**
3. Select the **Master Bill**
4. Save the Sea Shipment

The linked Sea Shipments will appear in the Master Bill's **Connections Tab**.

## Master Bill Types

### Direct
Used for direct shipments without consolidation.

### Co-Load
Used when multiple shipments are co-loaded on the same vessel.

### Agent Consolidation
Used when consolidating shipments from multiple agents.

### Charter
Used for chartered vessel operations.

### Courier
Used for courier/express sea freight services.

### Other
Used for other types of master bill arrangements.

## Best Practices

1. **Unique Master BL Numbers**: Ensure Master BL numbers are unique
2. **Accurate Vessel Information**: Enter correct vessel name and voyage number
3. **Complete Terminal Information**: Fill in CTO, CFS, and Container Yard details
4. **Date Accuracy**: Ensure departure and arrival dates are accurate
5. **Agent Information**: Maintain accurate sending and receiving agent information
6. **Link House Bills**: Link all related House Bills to the Master Bill

## Related Documents

- **Sea Shipment**: House Bills linked to this Master Bill
- **Sea Freight Consolidation**: Consolidation operations
- **Shipping Line**: Shipping line information
- **Container Yard**: Container yard locations
- **Cargo Terminal Operator**: Terminal operator information

## Usage in Consolidation

Master Bills are commonly used in consolidation operations:

1. Create a **Sea Freight Consolidation** document
2. Create or link a **Master Bill**
3. Link multiple **Sea Shipments** (House Bills) to the Master Bill
4. Track the consolidated shipment through the Master Bill

## Next Steps

- Learn about [Sea Freight Consolidation](sea-freight-consolidation.md)
- Understand [Sea Shipment](sea-shipment.md) management
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

