# Sea Freight Module

## Overview

The Sea Freight module in CargoNext provides comprehensive ocean freight forwarding capabilities, enabling you to manage the complete lifecycle of sea freight shipments from booking to delivery. This module is designed for freight forwarders, shipping agents, and logistics companies that handle ocean cargo operations.

## Key Features

### Complete Shipment Management
- Manage the entire sea freight lifecycle from booking to delivery
- Track shipments through multiple stages with status management
- Support for both import and export operations
- Handle direct shipments and consolidated cargo

### Container Management
- Track containers and manage container types
- Monitor container movements and assignments
- Calculate TEU (Twenty-foot Equivalent Unit) capacity
- Support for various container types (20ft, 40ft, 45ft, etc.)

### Master Bill and House Bill Management
- Create and manage Master Bills of Lading (MBL)
- Link multiple House Bills to a Master Bill
- Track consolidation operations
- Manage vessel and voyage information

### Port and Route Management
- Manage origin and destination ports using UNLOCO codes
- Track vessel schedules and ETD/ETA dates
- Handle port-to-port movements
- Support for multi-port routing

### Document Management
- Handle bills of lading, shipping instructions, and all sea freight documentation
- Manage commercial invoices, packing lists, and certificates
- Track document status and requirements

### Rate and Charge Management
- Configure and manage sea freight rates
- Handle surcharges and additional charges
- Link to Pricing Center for automated rate calculation
- Support for multiple charge types and billing methods

### Integration Capabilities
- Seamless integration with customs declarations
- Connect sea freight with inland transport operations
- Link to warehousing for container yard operations
- Integration with sustainability tracking for carbon footprint calculation

### Consolidation Management
- Manage consolidation operations
- Track multiple shipments in a single consolidation
- Calculate consolidation ratios and costs
- Handle consolidation routing and charges

## Module Structure

The Sea Freight module consists of the following main components:

### Transaction Documents
- **Sea Shipment**: Main document for managing individual sea freight shipments
- **Sea Freight Consolidation**: Document for managing consolidated cargo operations
- **Master Bill**: Master Bill of Lading management

### Master Data
- **Shipping Line**: Shipping line information and configurations
- **Container Yard**: Container yard locations and details
- **Cargo Terminal Operator**: Terminal operator information
- **Other Service**: Additional services offered in sea freight operations

### Settings
- **Sea Freight Settings**: Module-level configuration and defaults

### Child Tables
- **Sea Freight Containers**: Container details for shipments
- **Sea Freight Packages**: Package and cargo details
- **Sea Freight Services**: Additional services for shipments
- **Sea Freight Charges**: Charges and fees for shipments

## Workflow

A typical sea freight shipment workflow in CargoNext follows these steps:

1. **Setup**: Configure master data including shipping lines, ports, and container yards
2. **Booking**: Create a Sea Shipment document with shipper, consignee, and route details
3. **Container Assignment**: Assign containers and enter container details
4. **Package Details**: Enter package information, weights, and volumes
5. **Master Bill Linking**: Link to Master Bill if part of consolidation
6. **Services**: Add additional services if required
7. **Charges**: Configure charges and link to Pricing Center for rate calculation
8. **Documentation**: Generate and manage shipping documents
9. **Tracking**: Monitor shipment status and milestones
10. **Delivery**: Complete delivery and update final status

## Benefits

- **Centralized Management**: All sea freight operations in one platform
- **Real-Time Tracking**: Monitor shipments and containers in real-time
- **Automated Calculations**: Automatic calculation of charges, TEUs, and consolidation ratios
- **Document Management**: Comprehensive document handling and tracking
- **Integration**: Seamless integration with other CargoNext modules
- **Compliance**: Support for industry standards and regulations
- **Sustainability**: Track carbon footprint and environmental impact

## Related Modules

The Sea Freight module integrates with:
- **Air Freight**: For multi-modal shipments
- **Transport**: For inland transportation connections
- **Customs**: For customs declaration and clearance
- **Warehousing**: For container yard and CFS operations
- **Pricing Center**: For rate calculation and tariff management
- **Sustainability**: For carbon footprint tracking

## Next Steps

To get started with the Sea Freight module:

1. Review the [Setup Guide](setup.md) to configure the module
2. Set up [Master Data](master-data.md) including shipping lines and ports
3. Learn how to create a [Sea Shipment](sea-shipment.md)
4. Understand [Master Bill Management](master-bill.md)
5. Explore [Consolidation Operations](sea-freight-consolidation.md)

---

*For detailed information on each component, refer to the specific documentation pages.*

