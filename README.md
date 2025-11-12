# Logistics - CargoNext

Comprehensive Logistics Management System for Frappe/ERPNext.

## Overview

Logistics is a Frappe application that provides comprehensive logistics and supply chain management capabilities across multiple domains.

## Modules

The Logistics app includes the following modules:

1. **Logistics** - Core logistics management functionality
2. **Transport** - Transportation management, vehicle tracking, routing, and telematics
3. **Warehousing** - Warehouse operations including job management, storage location management, handling units, pick/putaway/move/VAS operations, stock ledger tracking, and transfer orders
4. **Customs** - Customs documentation, compliance management, and international trade compliance
5. **Sea Freight** - Ocean freight management and shipping operations
6. **Air Freight** - Air cargo management, flight schedules, and IATA cargo XML integration
7. **Job Management** - Job tracking and workflow management
8. **Pricing Center** - Centralized pricing management, rate configuration, and sales management for logistics services
9. **Sustainability** - Environmental impact tracking and sustainability reporting
10. **Netting** - Financial netting and reconciliation

## Installation

Install using bench:

```bash
bench get-app logistics
bench --site [your-site] install-app logistics
```

## Features

### Warehousing
- **Warehouse Operations**: Complete warehouse job management with support for Pick, Putaway, Move, and VAS operations
- **Storage Management**: Advanced storage location management with hierarchical structure
- **Handling Units**: Support for handling units and consolidation
- **Allocation Policies**: Configurable pick and putaway policies (FIFO, LIFO, FEFO, etc.)
- **Stock Tracking**: Real-time stock ledger tracking with location and handling unit details

### Transport
- Vehicle tracking and telematics integration
- Route optimization and planning
- Transportation job management
- Customer portal for transport services

### Freight Management
- **Sea Freight**: Ocean freight operations and shipping management
- **Air Freight**: Air cargo management with flight schedules and IATA cargo XML support

### Customs & Compliance
- Customs documentation management
- International customs and trade compliance
- Trade regulations support

### Business Operations
- **Pricing Center**: Centralized pricing, rate management, and sales management for logistics services
- **Job Management**: Workflow and job tracking
- **Sustainability**: Environmental impact tracking and reporting
- **Netting**: Financial netting and reconciliation

## License

MIT License

## Author

Agilasoft Cloud Technologies Inc.

