# Shipping Line

## Overview

Shipping Line is a master data document that stores information about ocean carriers that provide vessel services for sea freight shipments. This master data is referenced in Sea Shipments, Master Bills, and Consolidation documents.

## Purpose

The Shipping Line master is used to:
- Store information about ocean carriers
- Link shipping lines to Customer/Supplier masters for accounting
- Associate Cargo Terminal Operators (CTOs) with shipping lines
- Track shipping line codes and SCAC codes
- Manage active/inactive shipping line status

## Document Structure

The Shipping Line document contains the following sections:

### Basic Information

- **Code**: Unique identifier for the shipping line (auto-generated or manual, unique)
- **Shipping Line Name**: Full name of the shipping line
- **SCAC**: Standard Carrier Alpha Code (4-letter code used in North America)
- **Is Active**: Checkbox to indicate if the shipping line is currently active

### Organizations Tab

Contains accounting links:

- **Customer Link**: Link to Customer master if the shipping line is also a customer
- **Supplier Link**: Link to Supplier master if the shipping line is also a supplier

### Cargo Terminal Operators Tab

Contains linked Cargo Terminal Operators:

- **CTOs**: Table of Shipping Line CTO
  - Cargo Terminal Operator
  - Terminal details
  - Relationship information

## Creating a Shipping Line

### Step 1: Basic Information

1. Navigate to **Sea Freight > Master > Shipping Line**
2. Click **New**
3. Enter **Code** (unique identifier) - can be auto-generated or manual
4. Enter **Shipping Line Name**
5. Enter **SCAC** (Standard Carrier Alpha Code) if applicable
6. Check **Is Active** if the shipping line is currently active

### Step 2: Accounting Links

1. Go to **Organizations Tab**
2. If the shipping line is a customer, select **Customer Link**
3. If the shipping line is a supplier, select **Supplier Link**

### Step 3: Cargo Terminal Operators

1. Go to **Cargo Terminal Operators Tab**
2. In **CTOs** table, click **Add Row**
3. Select **Cargo Terminal Operator**
4. Enter any additional relationship details
5. Repeat for all associated CTOs

### Step 4: Save

1. Review all information
2. Click **Save**

## Key Fields Explained

### Code
Unique identifier for the shipping line. This code is used throughout the system to reference the shipping line. It can be:
- Auto-generated based on naming rules
- Manually entered
- Must be unique across all shipping lines

### Shipping Line Name
Full name of the shipping line. This is the display name used in lists and reports.

### SCAC (Standard Carrier Alpha Code)
A 4-letter code used in North America to identify carriers. This is required for certain operations and documentation in North American markets.

### Is Active
Checkbox indicating whether the shipping line is currently active. Inactive shipping lines will not appear in selection lists for new documents, but will remain visible in historical records.

### Customer Link
Link to Customer master if the shipping line is also a customer. This enables:
- Integrated accounting
- Customer-specific pricing
- Customer relationship management

### Supplier Link
Link to Supplier master if the shipping line is also a supplier. This enables:
- Integrated accounting
- Supplier management
- Purchase order processing

### Cargo Terminal Operators
Table of Cargo Terminal Operators associated with this shipping line. This helps manage terminal relationships and operations.

## Usage

Shipping Line is referenced in:

- **Sea Shipment**: Selected as the ocean carrier
- **Master Bill**: Linked to master bill of lading
- **Sea Freight Consolidation**: Selected for consolidation operations
- **Sea Freight Rate**: Used in rate configuration
- **Reports**: Used in various sea freight reports

## Best Practices

1. **Unique Codes**: Use consistent naming conventions for shipping line codes
2. **Complete Names**: Enter full shipping line names for clarity
3. **SCAC Codes**: Maintain SCAC codes for North American operations
4. **Active Status**: Keep shipping line status updated (active/inactive)
5. **Accounting Links**: Link to Customer/Supplier masters for integrated operations
6. **CTO Relationships**: Maintain accurate CTO relationships
7. **Regular Updates**: Review and update shipping line information regularly

## Naming Conventions

Recommended naming conventions for shipping line codes:

- Use shipping line abbreviations (e.g., "MAEU" for Maersk)
- Use standard industry codes when available
- Keep codes short and memorable
- Maintain consistency across the system

## Inactive Shipping Lines

When a shipping line is marked as inactive:

- It will not appear in selection lists for new documents
- Historical records will still reference the shipping line
- Existing documents linked to the shipping line remain valid
- Reports will still include inactive shipping lines for historical data

## Related Documents

- **Sea Shipment**: Uses shipping line for carrier information
- **Master Bill**: Links to shipping line
- **Sea Freight Consolidation**: References shipping line
- **Cargo Terminal Operator**: Linked in CTOs table
- **Customer**: Linked via Customer Link
- **Supplier**: Linked via Supplier Link

## Next Steps

- Learn about [Sea Shipment](sea-shipment.md) management
- Understand [Master Bill](master-bill.md) operations
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

