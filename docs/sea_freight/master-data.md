# Sea Freight Master Data

## Overview

Master data forms the foundation of the Sea Freight module. This document describes all master data records that need to be set up before creating sea freight transactions.

## Shipping Line

### Purpose

Shipping Line master contains information about ocean carriers that provide vessel services for sea freight shipments.

### Key Fields

- **Code**: Unique identifier for the shipping line (auto-generated or manual)
- **Shipping Line Name**: Full name of the shipping line
- **SCAC**: Standard Carrier Alpha Code (4-letter code used in North America)
- **Is Active**: Checkbox to indicate if the shipping line is currently active
- **Customer Link**: Link to Customer master if the shipping line is also a customer
- **Supplier Link**: Link to Supplier master if the shipping line is also a supplier

### Cargo Terminal Operators Tab

In the Cargo Terminal Operators tab, you can link Cargo Terminal Operators (CTOs) associated with this shipping line. This helps in managing terminal relationships.

### Usage

Shipping Line is referenced in:
- Sea Shipment documents
- Master Bill documents
- Sea Freight Consolidation documents
- Sea Freight Rate configuration

### Best Practices

- Use consistent naming conventions for shipping line codes
- Keep shipping line records active/inactive based on current business relationships
- Link to Customer/Supplier masters for integrated accounting
- Maintain SCAC codes for North American operations

## Container Yard

### Purpose

Container Yard master stores information about container storage facilities, also known as container depots or CY locations.

### Key Fields

- **Code**: Unique identifier for the container yard
- **Yard Name**: Full name of the container yard
- **Address**: Physical address of the yard
- **Port**: Associated port (UNLOCO code)
- **Is Active**: Checkbox to indicate if the yard is currently active

### Usage

Container Yard is referenced in:
- Master Bill documents (Origin CY, Destination CY)
- Sea Freight operations for container pickup and drop-off

### Best Practices

- Link container yards to their respective ports
- Keep yard records updated with current addresses
- Mark inactive yards to prevent selection in new shipments

## Cargo Terminal Operator

### Purpose

Cargo Terminal Operator (CTO) master contains information about terminal operators that handle cargo at ports and terminals.

### Key Fields

- **Code**: Unique identifier for the terminal operator
- **Terminal Operator Name**: Full name of the terminal operator
- **Address**: Physical address of the terminal
- **Port**: Associated port (UNLOCO code)
- **Is Active**: Checkbox to indicate if the operator is currently active

### Usage

Cargo Terminal Operator is referenced in:
- Master Bill documents (Origin CTO, Destination CTO)
- Shipping Line records (linked CTOs)

### Best Practices

- Maintain accurate port associations
- Keep terminal operator information current
- Link to ports for proper routing

## Other Service

### Purpose

Other Service master defines additional services that can be offered with sea freight shipments, such as documentation, insurance, or special handling.

### Key Fields

- **Service Code**: Unique identifier for the service
- **Service Name**: Full name of the service
- **Service Type**: Category of service
- **Description**: Detailed description of the service
- **Is Active**: Checkbox to indicate if the service is currently available

### Usage

Other Service is referenced in:
- Sea Freight Services child table in Sea Shipment
- Service pricing and billing

### Best Practices

- Create comprehensive service catalog
- Use clear service names and descriptions
- Maintain active/inactive status based on service availability

## Ports (UNLOCO)

### Purpose

Ports are typically managed through UNLOCO (United Nations Code for Trade and Transport Locations) master data. These codes are standard identifiers for ports worldwide.

### Key Fields

- **UNLOCO Code**: Standard 5-character UNLOCO code
- **Port Name**: Full name of the port
- **Country**: Country where the port is located
- **Port Type**: Type of port (sea port, river port, etc.)

### Usage

Ports are referenced in:
- Sea Shipment (Origin Port, Destination Port)
- Master Bill documents
- Sea Freight Consolidation
- Sea Freight Rate configuration

### Best Practices

- Always use standard UNLOCO codes
- Verify port codes for accuracy
- Maintain port names in local and English languages if needed

## Shipper and Consignee

### Purpose

Shipper and Consignee are parties involved in sea freight shipments. These are typically managed as separate master data or linked to Customer/Supplier records.

### Key Fields

- **Code**: Unique identifier
- **Name**: Full name of the party
- **Address**: Physical address
- **Contact**: Contact person and details
- **Country**: Country of origin/destination

### Usage

Shipper and Consignee are referenced in:
- Sea Shipment documents
- Master Bill documents
- Shipping documents and bills of lading

### Best Practices

- Maintain accurate address and contact information
- Link to Customer/Supplier masters for integrated operations
- Keep party information updated

## Freight Agent

### Purpose

Freight Agent master contains information about freight forwarding agents that may be involved in shipments.

### Key Fields

- **Code**: Unique identifier for the agent
- **Agent Name**: Full name of the agent
- **Agent Type**: Type of agent (customer agent, supplier agent)
- **Address**: Physical address
- **Is Active**: Checkbox to indicate if the agent is currently active

### Usage

Freight Agent is referenced in:
- Sea Shipment documents
- Master Bill documents
- Agency network management

### Best Practices

- Maintain agent relationships and commission structures
- Keep agent information current
- Track active/inactive agent status

## Master Data Relationships

The following diagram shows how master data records relate to each other:

```
Shipping Line
    ├── Cargo Terminal Operators (linked)
    └── Referenced in: Sea Shipment, Master Bill, Consolidation

Container Yard
    ├── Port (UNLOCO)
    └── Referenced in: Master Bill

Cargo Terminal Operator
    ├── Port (UNLOCO)
    └── Referenced in: Master Bill, Shipping Line

Port (UNLOCO)
    └── Referenced in: Sea Shipment, Master Bill, Rates

Shipper/Consignee
    └── Referenced in: Sea Shipment, Master Bill

Freight Agent
    └── Referenced in: Sea Shipment, Master Bill
```

## Setup Sequence

Recommended sequence for setting up master data:

1. **Ports (UNLOCO)**: Set up ports first as they are referenced by other masters
2. **Shipping Lines**: Create shipping line records
3. **Container Yards**: Set up container yards linked to ports
4. **Cargo Terminal Operators**: Create CTO records linked to ports
5. **Shippers and Consignees**: Set up party masters
6. **Freight Agents**: Configure agent network if applicable
7. **Other Services**: Create service catalog

## Maintenance

### Regular Updates

- Review and update shipping line status (active/inactive)
- Verify port codes and names
- Update container yard and CTO addresses
- Maintain shipper and consignee contact information

### Data Quality

- Ensure unique codes for all master records
- Maintain consistent naming conventions
- Keep address and contact information current
- Verify UNLOCO codes for accuracy

## Next Steps

After setting up master data:

1. Review [Setup Guide](setup.md) for configuration
2. Learn how to create a [Sea Shipment](sea-shipment.md)
3. Understand [Master Bill Management](master-bill.md)

---

*For information on creating and managing transactions, refer to the respective doctype documentation.*

