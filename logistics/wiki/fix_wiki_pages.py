# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def fix_wiki_pages():
    """Fix wiki pages by creating them properly without space field"""
    
    print("🔧 Fixing wiki pages structure...")
    
    # Check Wiki Page doctype fields
    try:
        wiki_page_doctype = frappe.get_doc("DocType", "Wiki Page")
        print("📋 Wiki Page fields:")
        for field in wiki_page_doctype.fields:
            if field.fieldtype in ["Data", "Text", "Text Editor", "Select", "Link"]:
                print(f"   - {field.fieldname}: {field.fieldtype}")
    except Exception as e:
        print(f"ℹ️ Could not get Wiki Page doctype: {e}")
    
    # Create wiki pages without space field
    create_warehousing_wiki_pages()
    
    print("✅ Wiki pages fixed!")


def create_warehousing_wiki_pages():
    """Create warehousing wiki pages with correct structure"""
    
    # Main warehousing overview page
    create_wiki_page("warehousing-overview", "Warehousing Module - Complete User Guide", """
# 🏭 CargoNext Warehousing Module

## Overview
The CargoNext Warehousing Module provides comprehensive warehouse management capabilities including warehouse job management, storage location management, handling unit tracking, value-added services, periodic billing, capacity management, and sustainability tracking.

## Quick Navigation

### Setup & Configuration
- [Warehouse Settings](./warehouse-settings) - Global warehouse configuration
- [Storage Locations](./storage-locations) - Warehouse layout and location management
- [Handling Unit Types](./handling-unit-types) - Container and unit configuration
- [Storage Types](./storage-types) - Storage type definitions

### Operations
- [Warehouse Jobs](./warehouse-jobs) - Complete warehouse operations workflow
- [VAS Operations](./vas-operations) - Value-added services management
- [Inbound Operations](./inbound-operations) - Receiving and putaway processes
- [Outbound Operations](./outbound-operations) - Picking and shipping processes

### Business Management
- [Billing and Contracts](./billing-contracts) - Contract and billing management
- [Periodic Billing](./periodic-billing) - Automated billing processes
- [Charges Management](./charges-management) - Charge calculation and management

### Advanced Features
- [Capacity Management](./capacity-management) - Real-time capacity monitoring
- [Quality Management](./quality-management) - Quality control and assurance
- [Sustainability](./sustainability) - Environmental tracking and reporting
- [Security and Compliance](./security-compliance) - Security and regulatory compliance

### Support
- [Troubleshooting](./troubleshooting) - Common issues and solutions
- [Best Practices](./best-practices) - Operational best practices
- [Integration Guide](./integration-guide) - System integration and automation

## Getting Started

1. **Configure Warehouse Settings** - Set up global parameters
2. **Create Storage Locations** - Define your warehouse layout
3. **Setup Handling Units** - Configure containers and units
4. **Create Your First Job** - Start with warehouse operations

## Key Features

- **Warehouse Job Management** - Complete lifecycle management
- **Storage Location Management** - Organized storage with capacity tracking
- **Handling Unit Tracking** - Track items through various units
- **Value-Added Services** - Manage additional services
- **Periodic Billing** - Automated billing based on usage
- **Capacity Management** - Real-time capacity monitoring
- **Sustainability Tracking** - Environmental impact monitoring

## Need Help?

- 📧 Contact Support: support@cargonext.io
- 📚 Browse all documentation in this space
- 💬 Join our community forum
- 🎓 Attend our training sessions
""")

    # Individual component pages
    create_wiki_page("warehouse-settings", "Warehouse Settings Configuration", """
# Warehouse Settings Configuration

## Overview
Warehouse Settings is the central configuration point for your warehousing operations. It defines global parameters that affect all warehouse jobs, billing, and capacity management.

## Accessing Warehouse Settings
1. Go to **Warehousing** > **Setup** > **Warehouse Settings**
2. Select your company
3. Configure the settings as described below

## Configuration Sections

### Company Information
- **Company**: Select the company for which you're configuring warehouse settings
- **Planned Date Offset Days**: Number of days to offset planned dates for warehouse jobs
- **Allocation Level Limit**: Maximum number of allocation levels allowed
- **Replenishment Policy**: Policy for stock replenishment

### Default Locations
- **Default Site**: Default site for warehouse operations
- **Default Facility**: Default facility for warehouse operations

### Billing Configuration

#### Volume Billing
- **Enable Volume Billing**: Check to enable volume-based billing
- **Default Volume UOM**: Default unit of measure for volume calculations
- **Volume Calculation Precision**: Decimal precision for volume calculations
- **Default Weight UOM**: Default unit of measure for weight calculations

### Capacity Management

#### Capacity Settings
- **Enable Capacity Management**: Enable real-time capacity monitoring
- **Default Volume Alert Threshold**: Percentage threshold for volume alerts
- **Default Weight Alert Threshold**: Percentage threshold for weight alerts
- **Default Utilization Alert Threshold**: Percentage threshold for utilization alerts

### Sustainability Tracking

#### Sustainability Settings
- **Enable Sustainability Tracking**: Track environmental impact
- **Green Certification Requirements**: Requirements for green certifications
- **Default Carbon Emission Factors**: Standard carbon emission factors

## Best Practices

### Initial Setup
1. **Start with Company Settings**: Configure company-specific parameters first
2. **Set Realistic Thresholds**: Configure capacity and utilization thresholds based on your actual warehouse capacity
3. **Enable Sustainability**: If you track environmental impact, enable sustainability tracking
4. **Configure Billing**: Set up billing parameters that match your business model

## Common Issues

### Q: How do I change the default UOM for volume calculations?
A: Go to Warehouse Settings > Billing Configuration > Default Volume UOM and select the appropriate UOM from the list.

### Q: What happens if I disable capacity management?
A: You won't receive capacity alerts, and capacity utilization reports will not be available.
""")

    create_wiki_page("storage-locations", "Storage Locations Setup", """
# Storage Locations Setup

## Overview
Storage Locations define the physical layout of your warehouse. They represent specific areas where items can be stored, such as zones, aisles, racks, or bins.

## Creating Storage Locations

### Using Storage Location Configurator
1. Go to **Warehousing** > **Setup** > **Storage Location Configurator**
2. Click **New** to create a new location
3. Fill in the required fields:
   - **Location Code**: Unique identifier for the location
   - **Location Name**: Descriptive name
   - **Parent Location**: Parent location (for hierarchical structure)
   - **Location Type**: Type of storage location
   - **Capacity**: Maximum capacity of the location
   - **Dimensions**: Physical dimensions (length, width, height)

## Location Hierarchy

### Zone Structure
```
Warehouse
├── Zone A (Bulk Storage)
│   ├── Aisle 1
│   │   ├── Rack 1
│   │   │   ├── Level 1
│   │   │   └── Level 2
│   │   └── Rack 2
│   └── Aisle 2
└── Zone B (Picking Area)
    ├── Aisle 3
    └── Aisle 4
```

## Location Types

### Bulk Storage
- **Purpose**: Store large quantities of items
- **Characteristics**: High capacity, less frequent access
- **Examples**: Pallet racks, bulk storage areas

### Picking Areas
- **Purpose**: Store items for order fulfillment
- **Characteristics**: Easy access, organized for picking
- **Examples**: Bin locations, pick faces

## Best Practices

### Design Principles
1. **Efficiency**: Minimize travel time between locations
2. **Flexibility**: Allow for future expansion
3. **Safety**: Ensure safe access and operations
4. **Scalability**: Design for growth

## Common Issues

### Q: How do I change the capacity of a location?
A: Edit the Storage Location record and update the capacity fields. Changes take effect immediately.

### Q: Can I move items between locations?
A: Yes, use Transfer Orders to move items between storage locations.
""")

    create_wiki_page("warehouse-jobs", "Warehouse Jobs Operations", """
# Warehouse Jobs Operations

## Overview
Warehouse Jobs are the core operational documents that manage all warehouse activities. They track the complete lifecycle of warehouse operations from inbound to outbound processes.

## Types of Warehouse Jobs

### Inbound Jobs
- **Receiving**: Process incoming shipments
- **Putaway**: Store items in appropriate locations
- **Quality Control**: Inspect received items
- **Cross-dock**: Direct transfer without storage

### Outbound Jobs
- **Picking**: Gather items for orders
- **Packing**: Package items for shipment
- **Staging**: Prepare items for loading
- **Loading**: Load items onto vehicles

### Internal Jobs
- **Transfer**: Move items between locations
- **Replenishment**: Restock picking locations
- **Cycle Count**: Count inventory
- **Relocation**: Reorganize storage

## Creating Warehouse Jobs

### Basic Job Creation
1. Go to **Warehousing** > **Operations** > **Warehouse Job**
2. Click **New** to create a new job
3. Select the job type (Inbound, Outbound, Transfer, etc.)
4. Fill in the basic information:
   - **Customer**: Customer for the job
   - **Reference Order**: Related sales order or purchase order
   - **Job Open Date**: When the job becomes active
   - **Warehouse Contract**: Applicable contract

## Job Workflow

### Job Lifecycle
1. **Draft**: Job is created but not active
2. **Open**: Job is active and ready for operations
3. **In Progress**: Operations are being performed
4. **Completed**: All operations are finished
5. **Cancelled**: Job is cancelled

## Best Practices

### Job Planning
1. **Plan Ahead**: Plan jobs in advance
2. **Resource Allocation**: Allocate resources properly
3. **Capacity Planning**: Consider capacity constraints
4. **Scheduling**: Schedule jobs efficiently

## Common Issues

### Q: How do I change the status of a warehouse job?
A: Use the status field in the Warehouse Job record. Some status changes are automatic based on operations.

### Q: Can I modify a job after it's started?
A: Yes, but some modifications may require cancelling and recreating the job.
""")

    create_wiki_page("vas-operations", "Value-Added Services (VAS) Operations", """
# Value-Added Services (VAS) Operations

## Overview
Value-Added Services (VAS) are additional services provided to customers beyond basic storage and handling. These services add value to the customer's supply chain and generate additional revenue.

## Types of VAS Operations

### Packaging Services
- **Repackaging**: Change packaging format
- **Bulk to Retail**: Convert bulk items to retail packaging
- **Custom Packaging**: Create custom packaging solutions
- **Labeling**: Apply labels and tags

### Quality Services
- **Quality Inspection**: Inspect items for quality
- **Testing**: Perform quality tests
- **Certification**: Provide quality certifications
- **Documentation**: Create quality documentation

### Processing Services
- **Assembly**: Assemble products
- **Kitting**: Create product kits
- **Configuration**: Configure products
- **Customization**: Customize products

## Creating VAS Orders

### Basic VAS Order Creation
1. Go to **Warehousing** > **Operations** > **VAS Order**
2. Click **New** to create a new order
3. Fill in the order details:
   - **Customer**: Customer for the service
   - **VAS Order Type**: Type of value-added service
   - **Items**: Items to be processed
   - **Services**: Specific services required
   - **Charges**: Applicable charges

## VAS Workflow

### Order Processing
1. **Order Creation**: Create VAS order
2. **Order Approval**: Approve the order
3. **Resource Allocation**: Allocate resources
4. **Service Execution**: Execute the service
5. **Quality Control**: Perform quality control
6. **Delivery**: Deliver completed service

## Best Practices

### Service Design
1. **Customer Focus**: Focus on customer needs
2. **Quality Standards**: Maintain high quality
3. **Efficiency**: Optimize service delivery
4. **Innovation**: Continuously improve

## Common Issues

### Q: How do I create a new VAS order type?
A: Go to Warehousing > Setup > VAS Order Type and create a new record with the required configuration.

### Q: Can I modify a VAS order after it's started?
A: Yes, but some modifications may require approval or may not be possible depending on the service status.
""")

    create_wiki_page("billing-contracts", "Billing and Contracts Management", """
# Billing and Contracts Management

## Overview
The billing and contracts system manages customer agreements, pricing, and automated billing for warehouse services. It ensures accurate and timely billing based on storage, handling, and value-added services.

## Warehouse Contracts

### Creating Warehouse Contracts
1. Go to **Warehousing** > **Setup** > **Warehouse Contract**
2. Click **New** to create a new contract
3. Fill in the contract details:
   - **Customer**: Customer for the contract
   - **Contract Type**: Type of contract
   - **Start Date**: Contract start date
   - **End Date**: Contract end date
   - **Terms**: Contract terms and conditions

## Contract Types

### Storage Contracts
- **Basic Storage**: Basic storage services
- **Temperature Controlled**: Temperature-controlled storage
- **High Security**: High-security storage
- **Bonded Storage**: Bonded warehouse storage

### Handling Contracts
- **Inbound Handling**: Inbound processing services
- **Outbound Handling**: Outbound processing services
- **Cross-dock**: Cross-docking services
- **Transfer**: Transfer services

## Pricing Models

### Volume-based Pricing
- **Per Cubic Meter**: Charge per cubic meter
- **Per Pallet**: Charge per pallet
- **Per Container**: Charge per container
- **Tiered Pricing**: Different rates for different volumes

### Time-based Pricing
- **Per Day**: Charge per day
- **Per Week**: Charge per week
- **Per Month**: Charge per month
- **Overtime Rates**: Overtime charges

## Best Practices

### Contract Design
1. **Clear Terms**: Use clear and specific terms
2. **Fair Pricing**: Set fair and competitive pricing
3. **Flexibility**: Allow for modifications
4. **Risk Management**: Manage contract risks

## Common Issues

### Q: How do I modify a contract after it's active?
A: Create a contract amendment to modify active contracts. Some changes may require customer approval.

### Q: Can I change pricing during a contract period?
A: Yes, but changes typically require contract amendments and customer approval.
""")

    create_wiki_page("sustainability", "Sustainability and Reporting", """
# Sustainability and Reporting

## Overview
The sustainability module tracks environmental impact, carbon footprint, and green initiatives in warehouse operations. It provides comprehensive reporting and analytics for environmental compliance and optimization.

## Sustainability Tracking

### Carbon Footprint Tracking
- **Carbon Emissions**: Track carbon emissions from operations
- **Emission Factors**: Use industry-standard emission factors
- **Scope 1, 2, 3**: Track different emission scopes
- **Reduction Targets**: Set and track reduction targets

### Energy Consumption
- **Energy Usage**: Track energy consumption
- **Energy Sources**: Monitor energy sources
- **Efficiency Metrics**: Calculate energy efficiency
- **Optimization**: Identify optimization opportunities

## Sustainability Configuration

### Carbon Emission Factors
1. Go to **Warehousing** > **Sustainability** > **Carbon Emission Factor**
2. Configure emission factors:
   - **Activity Type**: Type of activity
   - **Emission Factor**: CO2 equivalent per unit
   - **Unit of Measure**: Unit for the factor
   - **Source**: Source of the factor

### Green Certifications
1. Go to **Warehousing** > **Sustainability** > **Green Certification**
2. Manage certifications:
   - **Certification Type**: Type of certification
   - **Certification Body**: Certifying organization
   - **Valid From**: Certification start date
   - **Valid To**: Certification end date

## Best Practices

### Environmental Management
1. **Set Targets**: Set clear environmental targets
2. **Monitor Performance**: Monitor environmental performance
3. **Continuous Improvement**: Continuously improve
4. **Stakeholder Engagement**: Engage stakeholders

## Common Issues

### Q: How do I set up carbon emission tracking?
A: Configure carbon emission factors and set up tracking for different activities in your warehouse operations.

### Q: Can I track energy consumption from different sources?
A: Yes, you can track energy consumption from electricity, gas, and other sources separately.
""")

    create_wiki_page("troubleshooting", "Troubleshooting Guide", """
# Troubleshooting Guide

## Common Issues and Solutions

### Warehouse Job Issues

#### Job Not Starting
**Problem**: Warehouse job is not starting or processing
**Solutions**:
1. Check job status and ensure it's in "Open" status
2. Verify all required fields are filled
3. Check for system errors in the job log
4. Ensure proper permissions are assigned

#### Items Not Allocating
**Problem**: Items are not being allocated to storage locations
**Solutions**:
1. Check storage location availability
2. Verify item specifications match location requirements
3. Check capacity constraints
4. Review allocation rules and settings

### Storage Location Issues

#### Location Not Available
**Problem**: Storage location is not available for allocation
**Solutions**:
1. Check location status (active/inactive)
2. Verify capacity availability
3. Check access permissions
4. Review location constraints

### Billing Issues

#### Charges Not Calculating
**Problem**: Billing charges are not calculating correctly
**Solutions**:
1. Check billing configuration
2. Verify contract terms
3. Review charge definitions
4. Check billing rules and formulas

## Support Resources

### Documentation
- **User Guides**: Comprehensive user guides
- **API Documentation**: API reference documentation
- **Best Practices**: Best practice guides
- **Troubleshooting**: Troubleshooting guides

### Support Channels
- **Help Desk**: Technical support help desk
- **Knowledge Base**: Self-service knowledge base
- **Community Forum**: User community forum
- **Training**: Training and certification programs
""")


def create_wiki_page(page_name, title, content):
    """Create a wiki page with the given content"""
    try:
        if frappe.db.exists("Wiki Page", page_name):
            print(f"ℹ️ Wiki page '{page_name}' already exists")
            return
            
        wiki_page = frappe.get_doc({
            "doctype": "Wiki Page",
            "name": page_name,
            "title": title,
            "content": content,
            "published": 1
        })
        wiki_page.insert(ignore_permissions=True)
        print(f"✅ Wiki page '{page_name}' created")
    except Exception as e:
        print(f"ℹ️ Could not create wiki page '{page_name}': {e}")


if __name__ == "__main__":
    fix_wiki_pages()

