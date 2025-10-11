# CargoNext

A comprehensive logistics management system built on Frappe framework.

## Introduction

CargoNext is a modern, integrated logistics management platform designed to streamline and optimize logistics operations across warehousing, transportation, and freight management. Built on the robust Frappe framework, CargoNext provides a complete solution for logistics companies, freight forwarders, and supply chain managers.

### What is CargoNext?

CargoNext is a comprehensive logistics management system that combines:

- **Warehouse Management**: Complete warehouse operations including job management, storage tracking, and inventory control
- **Transportation Management**: End-to-end transport job lifecycle with route optimization and vehicle tracking
- **Freight Management**: Air and sea freight operations with IATA compliance and customs integration
- **Pricing Center**: Advanced rate calculation engine with flexible tariff management
- **Customer Portal**: Self-service portal for customers to track shipments and manage orders

### Key Benefits

- **Integrated Operations**: Seamless integration between warehousing, transport, and freight operations
- **Real-time Tracking**: Live tracking of shipments, vehicles, and warehouse operations
- **Automated Billing**: Comprehensive billing system with multiple charge types and automated invoice generation
- **Scalable Architecture**: Built on Frappe framework for enterprise-grade scalability
- **Customizable**: Flexible configuration to adapt to various logistics business models

### Who Should Use CargoNext?

- **Logistics Companies**: Freight forwarders, 3PL providers, and logistics service providers
- **Warehouse Operators**: Companies managing multiple warehouses and distribution centers
- **Transport Companies**: Fleet operators and transport service providers
- **Supply Chain Managers**: Companies looking to optimize their logistics operations
- **Freight Forwarders**: Companies handling air and sea freight operations

## Installation

### Using Bench (Recommended)

1. Install CargoNext
```bash
bench get-app https://github.com/agilasoft/cargonext
bench install-app cargonext
```

2. Migrate the database
```bash
bench migrate
```

### Manual Installation

1. Clone the repository
```bash
git clone https://github.com/agilasoft/cargonext.git
```

2. Install the app
```bash
bench get-app --link cargonext
bench install-app cargonext
```

## Features

### Warehousing
- Warehouse Job Management
- Storage Location Management
- Handling Unit Tracking
- Periodic Billing
- Capacity Management
- Sustainability Dashboard

### Transportation
- Transport Job Management
- Vehicle Tracking
- Route Optimization
- Customer Portal
- Carbon Footprint Calculation

### Freight Management
- Air Freight Operations
- Sea Freight Management
- Customs Integration
- Flight Schedule Integration

### Pricing Center
- Rate Calculation Engine
- Tariff Management
- Quote Generation
- Cost Analysis

## Setup

### Prerequisites
- Frappe Framework v15.0+
- ERPNext v15.0+

### Configuration

1. **Warehouse Setup**
   - Configure warehouse locations
   - Set up storage types
   - Define handling unit types

2. **Transport Setup**
   - Configure transport settings
   - Set up vehicle types
   - Define route optimization

3. **Billing Setup**
   - Create warehouse contracts
   - Configure billing methods
   - Set up charge types

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/agilasoft/cargonext.git

# Setup development environment
bench setup requirements
bench setup config
bench setup supervisor
bench start
```

### Running Tests

```bash
# Run all tests
bench run-tests cargonext

# Run specific module tests
bench run-tests cargonext --module logistics.warehousing
```

### Building Assets

```bash
# Build assets
bench build --app cargonext

# Watch for changes
bench watch
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the AGPL-3.0-or-later License.

## Support

- **Documentation**: [CargoNext Docs](https://docs.cargonext.com)
- **Issues**: [GitHub Issues](https://github.com/agilasoft/cargonext/issues)
- **Community**: [Frappe Community](https://discuss.frappe.io)
- **Email**: info@agilasoft.com

## About

**CargoNext** is developed by **Agilasoft Cloud Technologies Inc.**

- **Publisher**: Agilasoft Cloud Technologies Inc.
- **Email**: info@agilasoft.com
- **Website**: [www.agilasoft.com](https://www.agilasoft.com)
