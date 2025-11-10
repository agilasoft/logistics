# Other Service

## Overview

Other Service is a master data document that defines additional services that can be offered with sea freight shipments. These services include documentation services, insurance, special handling, and other value-added services beyond basic sea freight transportation.

## Purpose

The Other Service master is used to:
- Define additional services available for sea freight shipments
- Create a service catalog for value-added services
- Track service types and descriptions
- Reference in Sea Freight Services child table
- Support service pricing and billing

## Document Structure

The Other Service document contains the following fields:

### Basic Information

- **Service Code**: Unique identifier for the service
- **Service Name**: Full name of the service
- **Service Type**: Category or type of service
- **Description**: Detailed description of the service
- **Is Active**: Checkbox to indicate if the service is currently available

## Creating an Other Service

### Step 1: Basic Information

1. Navigate to **Sea Freight > Master > Other Service**
2. Click **New**
3. Enter **Service Code** (unique identifier)
4. Enter **Service Name** (full name of the service)
5. Select **Service Type** if applicable
6. Enter **Description** with detailed information about the service
7. Check **Is Active** if the service is currently available

### Step 2: Save

1. Review all information
2. Click **Save**

## Key Fields Explained

### Service Code
Unique identifier for the service. This code is used throughout the system to reference the service. Must be unique across all services.

### Service Name
Full name of the service. This is the display name used in lists and service selection.

### Service Type
Category or classification of the service. This helps organize services into groups (e.g., Documentation, Insurance, Handling, etc.).

### Description
Detailed description of what the service includes, how it works, and any special requirements or conditions.

### Is Active
Checkbox indicating whether the service is currently available. Inactive services will not appear in selection lists for new documents, but will remain visible in historical records.

## Common Service Types

Typical services that can be created include:

### Documentation Services
- Bill of Lading preparation
- Commercial invoice preparation
- Certificate of origin
- Export documentation
- Import documentation

### Insurance Services
- Cargo insurance
- Liability insurance
- Special coverage options

### Handling Services
- Special handling requirements
- Temperature-controlled handling
- Dangerous goods handling
- Oversized cargo handling

### Value-Added Services
- Cargo consolidation
- Cargo deconsolidation
- Repacking services
- Labeling services
- Quality inspection

## Usage

Other Service is referenced in:

- **Sea Freight Services**: Child table in Sea Shipment documents
- **Service Selection**: Used when adding services to shipments
- **Service Pricing**: Referenced in service pricing and billing
- **Reports**: Used in service utilization reports

## Best Practices

1. **Comprehensive Catalog**: Create a comprehensive service catalog covering all available services
2. **Clear Descriptions**: Provide clear and detailed service descriptions
3. **Service Types**: Use service types to organize services into logical groups
4. **Active Status**: Keep service status updated (active/inactive)
5. **Regular Review**: Review and update service catalog regularly
6. **Unique Codes**: Use consistent naming conventions for service codes

## Service Catalog Management

To maintain an effective service catalog:

1. **Regular Updates**: Review services regularly and update as needed
2. **New Services**: Add new services as they become available
3. **Inactive Services**: Mark services as inactive when they are no longer offered
4. **Descriptions**: Keep descriptions current and accurate
5. **Pricing**: Coordinate with pricing team to ensure service pricing is up to date

## Inactive Services

When a service is marked as inactive:

- It will not appear in selection lists for new documents
- Historical records will still reference the service
- Existing documents with the service remain valid
- Reports will still include inactive services for historical data

## Related Documents

- **Sea Shipment**: Uses services in Sea Freight Services child table
- **Sea Freight Services**: Child table that references Other Service
- **Pricing**: Service pricing may be configured separately

## Next Steps

- Learn about [Sea Shipment](sea-shipment.md) management
- Understand how to add services to shipments
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

