# Sea Freight Setup

## Overview

This guide will help you set up the Sea Freight module in CargoNext. Proper setup ensures that all sea freight operations run smoothly and efficiently.

## Prerequisites

Before setting up the Sea Freight module, ensure that:

1. CargoNext is installed and configured
2. You have System Manager or Administrator access
3. Basic master data (Company, Customer, Supplier) is set up
4. UNLOCO codes for ports are configured (if using port management)

## Configuration Steps

### 1. Sea Freight Settings

Navigate to **Sea Freight > Setup > Sea Freight Settings** to configure module-level settings.

#### Key Settings

- **Default Shipping Status**: Set the default status for new sea shipments
- **Default Service Level**: Configure default service level for shipments
- **Default Container Type**: Set default container type if applicable

#### Configuration Steps

1. Go to **Sea Freight > Setup > Sea Freight Settings**
2. Configure the default values as per your business requirements
3. Save the settings

### 2. Naming Series Setup

Configure naming series for Sea Freight documents to ensure proper document numbering.

#### Documents Requiring Naming Series

- **Sea Shipment**: Main shipment document
- **Master Bill**: Master Bill of Lading
- **Sea Freight Consolidation**: Consolidation documents

#### Setup Steps

1. Go to **Sea Freight > Setup > Naming Series**
2. Create naming series for each document type
3. Set prefixes and numbering formats (e.g., SF-SHIP-.YYYY.-.#####)
4. Set as default for the respective document types

### 3. Master Data Setup

Before creating sea freight shipments, set up the following master data:

#### Shipping Lines

1. Navigate to **Sea Freight > Master > Shipping Line**
2. Create shipping line records with:
   - **Code**: Unique shipping line code
   - **Shipping Line Name**: Full name of the shipping line
   - **SCAC**: Standard Carrier Alpha Code (if applicable)
   - **Customer Link**: Link to Customer master if shipping line is a customer
   - **Supplier Link**: Link to Supplier master if shipping line is a supplier
   - **Is Active**: Check if the shipping line is currently active

#### Container Yards

1. Navigate to **Sea Freight > Master > Container Yard**
2. Create container yard records with:
   - **Code**: Unique yard code
   - **Yard Name**: Full name of the container yard
   - **Address**: Physical location
   - **Port**: Associated port (UNLOCO code)
   - **Is Active**: Check if the yard is currently active

#### Cargo Terminal Operators

1. Navigate to **Sea Freight > Master > Cargo Terminal Operator**
2. Create terminal operator records with:
   - **Code**: Unique operator code
   - **Terminal Operator Name**: Full name
   - **Address**: Physical location
   - **Port**: Associated port
   - **Is Active**: Check if the operator is currently active

#### Other Services

1. Navigate to **Sea Freight > Master > Other Service**
2. Create service records for additional services like:
   - Documentation services
   - Customs clearance assistance
   - Cargo insurance
   - Other value-added services

### 4. Port Configuration

Ensure that ports are configured using UNLOCO codes:

1. Navigate to **Setup > Master Data > UNLOCO** (or your port master)
2. Create or verify port records with UNLOCO codes
3. Ensure ports used in sea freight operations are properly configured

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

1. Navigate to **Pricing Center > Sea Freight Rate**
2. Configure sea freight rates with:
   - Origin and destination ports
   - Container types
   - Weight and volume ranges
   - Calculation methods
   - Valid date ranges

### 7. Accounting Dimensions

Configure accounting dimensions for proper financial tracking:

1. **Company**: Ensure company is set up
2. **Branch**: Configure branches if using multi-branch operations
3. **Cost Center**: Set up cost centers for cost tracking
4. **Profit Center**: Configure profit centers for profitability analysis
5. **Job Costing**: Set up job costing if tracking costs by shipment

### 8. Custom Fields (Optional)

If you need additional fields:

1. Go to **Customize Form** for any Sea Freight doctype
2. Add custom fields as per your business requirements
3. Configure field properties and validations

## Verification Checklist

After setup, verify the following:

- [ ] Sea Freight Settings configured
- [ ] Naming series set up for all documents
- [ ] At least one Shipping Line created
- [ ] At least one Container Yard created (if using)
- [ ] At least one Cargo Terminal Operator created (if using)
- [ ] Ports configured with UNLOCO codes
- [ ] Shipper and Consignee masters set up
- [ ] Accounting dimensions configured
- [ ] Pricing Center rates configured (if using automated pricing)

## Common Setup Issues

### Issue: Cannot create Sea Shipment
**Solution**: Ensure naming series is configured for Sea Shipment document type.

### Issue: Port not found
**Solution**: Verify that ports are created with proper UNLOCO codes in the port master.

### Issue: Shipping Line not appearing
**Solution**: Check if the shipping line is marked as "Is Active" in the Shipping Line master.

### Issue: Charges not calculating
**Solution**: Verify that Sea Freight Rates are configured in Pricing Center with valid date ranges.

## Next Steps

After completing the setup:

1. Review [Master Data](master-data.md) documentation
2. Learn how to create your first [Sea Shipment](sea-shipment.md)
3. Understand [Master Bill Management](master-bill.md)

---

*For detailed information on each master data type, refer to the Master Data documentation.*

