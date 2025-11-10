# Air Freight Module

## Overview

The Air Freight module in CargoNext provides comprehensive air cargo management capabilities, enabling you to manage the complete lifecycle of air freight shipments from booking to delivery. This module is designed for freight forwarders, air cargo agents, and logistics companies that handle air cargo operations with full IATA compliance support.

## Key Features

### Complete Shipment Management
- Manage the entire air freight lifecycle from booking to delivery
- Track shipments through multiple stages with status management
- Support for both import and export operations
- Handle direct shipments and consolidated cargo
- Visual milestone tracking dashboard

### IATA Compliance
- Full IATA (International Air Transport Association) compliance support
- IATA message integration for status updates
- IATA status tracking and message queue management
- Electronic Air Waybill (eAWB) support
- CASS (Cargo Accounts Settlement System) integration

### Dangerous Goods Management
- Comprehensive Dangerous Goods (DG) declaration support
- DG compliance status tracking
- Emergency contact information management
- DG segregation validation in consolidations
- IATA DG regulations compliance

### Flight Schedule Integration
- Real-time flight schedule integration
- Automatic flight status updates
- Flight tracking and monitoring
- Capacity management and booking
- Delay tracking and notifications

### Master Air Waybill (MAWB) Management
- Create and manage Master Air Waybills
- Link multiple House Air Waybills to Master AWB
- Track flight information and schedules
- Real-time flight tracking integration
- Ground handling agreement management

### Package and ULD Management
- Comprehensive package management
- Unit Load Device (ULD) tracking
- ULD capacity and position management
- Temperature-controlled cargo tracking
- Cold chain compliance monitoring

### Consolidation Management
- Manage consolidation operations for multiple shipments
- Track consolidated cargo details (packages, weight, volume)
- Calculate consolidation ratios and costs
- Route optimization for consolidations
- Dangerous goods segregation validation

### Milestone Tracking
- Visual milestone dashboard
- Track key shipment milestones
- Monitor on-time performance
- Delay detection and alerts
- Status updates and notifications

### Sustainability Tracking
- Carbon footprint calculation for air freight operations
- Fuel consumption tracking
- Environmental impact reporting
- Sustainability goals and compliance

## Module Structure

The Air Freight module consists of the following main components:

### Transaction Documents
- **Air Shipment**: Main document for managing individual air freight shipments
- **Air Consolidation**: Document for managing consolidated cargo operations
- **Master Air Waybill**: Master Air Waybill management

### Master Data
- **Airline**: Airline information and configurations
- **Airport Master**: Airport information with IATA/ICAO codes
- **Flight Route**: Flight route information
- **Flight Schedule**: Flight schedule management
- **Unit Load Device (ULD)**: ULD type and tracking information

### Settings
- **IATA Settings**: IATA integration configuration
- **Flight Schedule Settings**: Flight schedule sync configuration

### Child Tables
- **Air Shipment Packages**: Package details for shipments
- **Air Shipment Services**: Additional services for shipments
- **Air Shipment Charges**: Charges and fees for shipments
- **Dangerous Goods Declaration Packages**: DG package details

## Workflow

A typical air freight shipment workflow in CargoNext follows these steps:

1. **Setup**: Configure master data including airlines, airports, and flight schedules
2. **Booking**: Create an Air Shipment document with shipper, consignee, and route details
3. **Package Details**: Enter package information, weights, and volumes
4. **Dangerous Goods**: Complete DG declaration if applicable
5. **Master AWB Linking**: Link to Master Air Waybill if part of consolidation
6. **ULD Assignment**: Assign ULDs if applicable
7. **Services**: Add additional services if required
8. **Charges**: Configure charges and link to Pricing Center for rate calculation
9. **IATA Integration**: Process IATA messages and status updates
10. **Milestone Tracking**: Monitor shipment milestones and status
11. **Documentation**: Generate and manage shipping documents
12. **Delivery**: Complete delivery and update final status

## Benefits

- **IATA Compliance**: Full compliance with IATA regulations and standards
- **Real-Time Tracking**: Monitor shipments and flights in real-time
- **Automated Calculations**: Automatic calculation of charges, chargeable weight, and consolidation ratios
- **Dangerous Goods Support**: Comprehensive DG management and compliance
- **Flight Integration**: Real-time flight schedule and status integration
- **Milestone Visibility**: Visual milestone tracking for better operations management
- **Document Management**: Comprehensive document handling and tracking
- **Integration**: Seamless integration with other CargoNext modules
- **Sustainability**: Track carbon footprint and environmental impact

## Related Modules

The Air Freight module integrates with:
- **Sea Freight**: For multi-modal shipments
- **Transport**: For inland transportation connections
- **Customs**: For customs declaration and clearance
- **Warehousing**: For cargo terminal operations
- **Pricing Center**: For rate calculation and tariff management
- **Sustainability**: For carbon footprint tracking

## Next Steps

To get started with the Air Freight module:

1. Review the [Setup Guide](setup.md) to configure the module
2. Set up [Master Data](master-data.md) including airlines and airports
3. Learn how to create an [Air Shipment](air-shipment.md)
4. Understand [Master Air Waybill Management](master-air-waybill.md)
5. Explore [Consolidation Operations](air-consolidation.md)

---

*For detailed information on each component, refer to the specific documentation pages.*

