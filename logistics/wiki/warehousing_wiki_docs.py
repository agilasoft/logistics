# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def create_warehousing_wiki_documentation():
    """Create comprehensive wiki documentation for the warehousing module"""
    
    print("📚 Creating comprehensive warehousing wiki documentation...")
    
    # Create main warehousing wiki space if it doesn't exist
    create_warehousing_wiki_space()
    
    # Create individual wiki pages for each major component
    create_warehouse_settings_guide()
    create_storage_locations_guide()
    create_handling_unit_types_guide()
    create_warehouse_jobs_guide()
    create_vas_operations_guide()
    create_billing_contracts_guide()
    create_sustainability_guide()
    
    print("✅ Warehousing wiki documentation created successfully!")


def create_warehousing_wiki_space():
    """Create the main warehousing wiki space"""
    try:
        if frappe.db.exists("Wiki Space", "warehousing"):
            print("ℹ️ Warehousing wiki space already exists")
            return
            
        wiki_space = frappe.get_doc({
            "doctype": "Wiki Space",
            "name": "warehousing",
            "title": "Warehousing Module Documentation",
            "description": "Complete user guide for CargoNext Warehousing Module including setup, operations, and best practices",
            "published": 1
        })
        wiki_space.insert(ignore_permissions=True)
        print("✅ Warehousing wiki space created")
    except Exception as e:
        print(f"ℹ️ Could not create wiki space: {e}")


def create_warehouse_settings_guide():
    """Create warehouse settings configuration guide"""
    
    content = """# Warehouse Settings Configuration

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

#### Billing Settings
Configure how charges are calculated and applied to warehouse operations.

### Capacity Management

#### Capacity Settings
- **Enable Capacity Management**: Enable real-time capacity monitoring
- **Default Volume Alert Threshold**: Percentage threshold for volume alerts
- **Default Weight Alert Threshold**: Percentage threshold for weight alerts
- **Default Utilization Alert Threshold**: Percentage threshold for utilization alerts

#### Default Capacities
- **Default Pallet Volume**: Standard volume for pallets
- **Default Pallet Weight**: Standard weight for pallets
- **Default Box Volume**: Standard volume for boxes
- **Default Box Weight**: Standard weight for boxes

### Sustainability Tracking

#### Sustainability Settings
- **Enable Sustainability Tracking**: Track environmental impact
- **Green Certification Requirements**: Requirements for green certifications
- **Default Carbon Emission Factors**: Standard carbon emission factors

### Standard Costing

#### Costing Settings
- **Enable Standard Costing**: Enable standard costing for warehouse operations
- **Post GL Entry for Standard Costing**: Automatically post GL entries for standard costing

## Best Practices

### Initial Setup
1. **Start with Company Settings**: Configure company-specific parameters first
2. **Set Realistic Thresholds**: Configure capacity and utilization thresholds based on your actual warehouse capacity
3. **Enable Sustainability**: If you track environmental impact, enable sustainability tracking
4. **Configure Billing**: Set up billing parameters that match your business model

### Regular Maintenance
- Review and update capacity thresholds quarterly
- Monitor sustainability metrics monthly
- Update billing parameters as needed
- Review standard costing settings annually

## Common Issues

### Q: How do I change the default UOM for volume calculations?
A: Go to Warehouse Settings > Billing Configuration > Default Volume UOM and select the appropriate UOM from the list.

### Q: What happens if I disable capacity management?
A: You won't receive capacity alerts, and capacity utilization reports will not be available.

### Q: How do I configure sustainability tracking?
A: Enable "Enable Sustainability Tracking" in the Sustainability section and configure the carbon emission factors.

## Related Documentation
- [Storage Locations Setup](./storage-locations)
- [Handling Unit Types](./handling-unit-types)
- [Warehouse Jobs](./warehouse-jobs)
- [Periodic Billing](./periodic-billing)
"""

    create_wiki_page("warehouse-settings", "Warehouse Settings Configuration", content, "warehousing")


def create_storage_locations_guide():
    """Create storage locations setup guide"""
    
    content = """# Storage Locations Setup

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

### Manual Creation
1. Go to **Warehousing** > **Setup** > **Storage Location**
2. Create individual locations with detailed specifications

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

### Best Practices for Hierarchy
1. **Logical Grouping**: Group related items in the same zone
2. **Accessibility**: Place frequently accessed items in easily reachable locations
3. **Capacity Planning**: Ensure adequate capacity for each location
4. **Naming Convention**: Use consistent naming conventions for easy identification

## Location Types

### Bulk Storage
- **Purpose**: Store large quantities of items
- **Characteristics**: High capacity, less frequent access
- **Examples**: Pallet racks, bulk storage areas

### Picking Areas
- **Purpose**: Store items for order fulfillment
- **Characteristics**: Easy access, organized for picking
- **Examples**: Bin locations, pick faces

### Staging Areas
- **Purpose**: Temporary storage during operations
- **Characteristics**: Flexible, temporary use
- **Examples**: Inbound staging, outbound staging

## Capacity Management

### Setting Capacity Limits
1. **Volume Capacity**: Maximum volume the location can hold
2. **Weight Capacity**: Maximum weight the location can support
3. **Item Count**: Maximum number of different items
4. **Handling Units**: Maximum number of handling units

### Capacity Monitoring
- Real-time capacity utilization
- Alert thresholds for capacity limits
- Capacity reports and analytics

## Location Attributes

### Physical Attributes
- **Dimensions**: Length, width, height
- **Weight Capacity**: Maximum supported weight
- **Accessibility**: Forklift access, manual access
- **Environmental**: Temperature, humidity requirements

### Operational Attributes
- **Storage Type**: Type of storage (bulk, picking, staging)
- **Picking Rank**: Priority for picking operations
- **Security Level**: Security requirements
- **Compliance**: Regulatory compliance requirements

## Configuration Steps

### Step 1: Define Zones
1. Create main zones (e.g., Bulk Storage, Picking, Staging)
2. Set capacity limits for each zone
3. Define access requirements

### Step 2: Create Aisles
1. Create aisles within each zone
2. Set aisle-specific attributes
3. Define movement patterns

### Step 3: Setup Racks and Bins
1. Create rack structures
2. Define bin locations
3. Set individual location capacities

### Step 4: Configure Access
1. Set up access controls
2. Define movement restrictions
3. Configure security requirements

## Best Practices

### Design Principles
1. **Efficiency**: Minimize travel time between locations
2. **Flexibility**: Allow for future expansion
3. **Safety**: Ensure safe access and operations
4. **Scalability**: Design for growth

### Implementation Tips
1. **Start Simple**: Begin with basic structure and expand
2. **Use Templates**: Create location templates for consistency
3. **Document Everything**: Maintain detailed documentation
4. **Regular Review**: Review and optimize regularly

## Common Issues

### Q: How do I change the capacity of a location?
A: Edit the Storage Location record and update the capacity fields. Changes take effect immediately.

### Q: Can I move items between locations?
A: Yes, use Transfer Orders to move items between storage locations.

### Q: How do I handle location maintenance?
A: Use the location status field to mark locations as under maintenance and prevent new allocations.

## Related Documentation
- [Warehouse Settings](./warehouse-settings)
- [Handling Unit Types](./handling-unit-types)
- [Warehouse Jobs](./warehouse-jobs)
- [Capacity Management](./capacity-management)
"""

    create_wiki_page("storage-locations", "Storage Locations Setup", content, "warehousing")


def create_handling_unit_types_guide():
    """Create handling unit types guide"""
    
    content = """# Handling Unit Types Configuration

## Overview
Handling Unit Types define the different types of containers, pallets, and other units used to move and store items in your warehouse. They are essential for tracking items through warehouse operations.

## Creating Handling Unit Types

### Basic Setup
1. Go to **Warehousing** > **Setup** > **Handling Unit Type**
2. Click **New** to create a new type
3. Fill in the required fields:
   - **Code**: Unique identifier (e.g., PAL, CONT, BOX)
   - **Description**: Descriptive name
   - **Type**: Category of handling unit
   - **Dimensions**: Physical specifications
   - **Capacity**: Storage and weight capacity

### Detailed Configuration

#### Physical Specifications
- **Length**: Maximum length in standard units
- **Width**: Maximum width in standard units
- **Height**: Maximum height in standard units
- **Weight**: Maximum weight capacity
- **Volume**: Maximum volume capacity

#### Operational Settings
- **Stackable**: Whether units can be stacked
- **Reusable**: Whether units can be reused
- **Trackable**: Whether units need tracking
- **Security Level**: Security requirements

## Common Handling Unit Types

### Pallets
- **Standard Pallet**: 48" x 40" x 6" (1200 x 1000 x 150 mm)
- **Euro Pallet**: 1200 x 800 x 144 mm
- **Half Pallet**: 24" x 40" x 6"
- **Quarter Pallet**: 24" x 20" x 6"

### Containers
- **20ft Container**: 20' x 8' x 8'6"
- **40ft Container**: 40' x 8' x 8'6"
- **High Cube Container**: 40' x 8' x 9'6"
- **Reefer Container**: Temperature-controlled container

### Boxes and Cartons
- **Standard Box**: Various sizes
- **Mailer Box**: For small items
- **Corrugated Box**: Heavy-duty packaging
- **Custom Box**: Specialized dimensions

### Specialized Units
- **Cage**: For loose items
- **Tote**: For small parts
- **Drum**: For liquids or bulk materials
- **Crate**: For fragile items

## Configuration Best Practices

### Naming Conventions
- Use clear, descriptive codes
- Include size information in the code
- Use consistent formatting
- Avoid special characters

### Capacity Planning
- Set realistic capacity limits
- Consider weight distribution
- Plan for stacking requirements
- Account for handling equipment

### Tracking Requirements
- Determine tracking needs
- Set up barcode/QR code systems
- Configure RFID if needed
- Plan for serial number tracking

## Handling Unit Storage Types

### Storage Type Assignment
1. **Bulk Storage**: For large quantities
2. **Picking Storage**: For order fulfillment
3. **Staging Storage**: For temporary storage
4. **Cross-dock Storage**: For immediate transfer

### Storage Requirements
- **Temperature**: Ambient, refrigerated, frozen
- **Humidity**: Standard, controlled humidity
- **Security**: Standard, high security
- **Access**: Forklift, manual, automated

## Integration with Warehouse Operations

### Inbound Operations
- **Receiving**: Assign handling units to received items
- **Putaway**: Place items in appropriate storage locations
- **Quality Control**: Track items through QC processes

### Outbound Operations
- **Picking**: Use handling units for order fulfillment
- **Packing**: Package items in appropriate containers
- **Shipping**: Load items onto transport vehicles

### Internal Operations
- **Transfers**: Move items between locations
- **Replenishment**: Restock picking locations
- **Cycle Counting**: Count items in handling units

## Advanced Configuration

### Custom Attributes
- **Material**: Wood, plastic, metal, cardboard
- **Color**: For visual identification
- **Supplier**: Source of the handling unit
- **Cost**: Purchase or rental cost

### Compliance Requirements
- **Regulatory**: Meet industry standards
- **Environmental**: Eco-friendly materials
- **Safety**: Safety requirements
- **Quality**: Quality standards

### Automation Integration
- **Barcode**: Barcode scanning capability
- **RFID**: RFID tag support
- **IoT**: Internet of Things integration
- **Robotics**: Robotic handling support

## Maintenance and Lifecycle

### Regular Maintenance
- **Inspection**: Regular condition checks
- **Cleaning**: Sanitization requirements
- **Repair**: Damage repair procedures
- **Replacement**: End-of-life replacement

### Lifecycle Tracking
- **Purchase Date**: When unit was acquired
- **First Use**: First operational use
- **Usage Count**: Number of uses
- **Retirement Date**: When unit is retired

## Common Issues

### Q: How do I change the capacity of a handling unit type?
A: Edit the Handling Unit Type record and update the capacity fields. Existing units will retain their current capacity.

### Q: Can I create custom handling unit types?
A: Yes, you can create any custom handling unit type that meets your operational needs.

### Q: How do I track handling units through operations?
A: Use the Warehouse Job system to track handling units through inbound, outbound, and transfer operations.

## Related Documentation
- [Storage Locations](./storage-locations)
- [Warehouse Jobs](./warehouse-jobs)
- [VAS Operations](./vas-operations)
- [Capacity Management](./capacity-management)
"""

    create_wiki_page("handling-unit-types", "Handling Unit Types Configuration", content, "warehousing")


def create_warehouse_jobs_guide():
    """Create warehouse jobs operations guide"""
    
    content = """# Warehouse Jobs Operations

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

### Job Configuration

#### Job Details
- **Type**: Inbound, Outbound, Transfer, VAS, etc.
- **Customer**: Customer for the job
- **Reference Order Type**: Sales Order, Purchase Order, etc.
- **Reference Order**: Specific order reference
- **VAS Order Type**: Type of value-added service

#### Docking Information
- **Docks**: Assigned dock doors
- **Staging Area**: Staging location for items
- **Allocations**: Item allocation details

#### Items and Operations
- **Items**: Items to be processed
- **Operations**: Specific operations to perform
- **Charges**: Applicable charges
- **Notes**: Additional information

## Job Workflow

### Job Lifecycle
1. **Draft**: Job is created but not active
2. **Open**: Job is active and ready for operations
3. **In Progress**: Operations are being performed
4. **Completed**: All operations are finished
5. **Cancelled**: Job is cancelled

### Status Management
- **Automatic Status**: System updates status based on operations
- **Manual Status**: Manual status updates when needed
- **Status Alerts**: Notifications for status changes

## Operations Management

### Operation Types
- **Staging In**: Prepare items for inbound processing
- **Staging Out**: Prepare items for outbound processing
- **Putaway**: Store items in storage locations
- **Pick**: Gather items for orders
- **Move**: Move items between locations
- **VAS**: Value-added services
- **Stocktake**: Count inventory

### Operation Configuration
- **Operation**: Specific operation to perform
- **Description**: Operation description
- **Unit Std Hours**: Standard hours for the operation
- **Handling Basis**: Basis for handling (Item Unit, Volume, Weight, etc.)
- **Handling UOM**: Unit of measure for handling
- **Quantity**: Quantity to process
- **Total Std Hours**: Total standard hours
- **Actual Hours**: Actual hours worked

## Item Management

### Item Allocation
- **Items**: Items to be processed
- **Quantities**: Quantities to process
- **Locations**: Source and destination locations
- **Handling Units**: Handling units to use

### Item Tracking
- **Serial Numbers**: Track individual items
- **Batch Numbers**: Track item batches
- **Handling Units**: Track handling units
- **Locations**: Track item locations

## Dock Management

### Dock Assignment
- **Dock Doors**: Assign dock doors to jobs
- **Dock Schedules**: Schedule dock usage
- **Dock Capacity**: Monitor dock capacity
- **Dock Status**: Track dock availability

### Dock Operations
- **Receiving**: Process inbound shipments
- **Shipping**: Process outbound shipments
- **Cross-dock**: Direct transfer operations
- **Staging**: Temporary storage at docks

## Quality Control

### QC Requirements
- **QA Required**: Quality assurance requirements
- **QC Procedures**: Quality control procedures
- **QC Standards**: Quality standards to meet
- **QC Documentation**: Required documentation

### QC Processes
- **Inspection**: Item inspection procedures
- **Testing**: Quality testing requirements
- **Certification**: Quality certifications
- **Documentation**: QC documentation

## Billing and Charges

### Charge Types
- **Storage Charges**: Charges for storage
- **Handling Charges**: Charges for handling
- **VAS Charges**: Value-added service charges
- **Special Charges**: Special service charges

### Charge Calculation
- **Volume-based**: Charges based on volume
- **Weight-based**: Charges based on weight
- **Time-based**: Charges based on time
- **Service-based**: Charges based on services

## Reporting and Analytics

### Job Reports
- **Job Status**: Current job status
- **Job Performance**: Performance metrics
- **Job Costs**: Cost analysis
- **Job Efficiency**: Efficiency metrics

### Operational Reports
- **Throughput**: Items processed
- **Efficiency**: Operational efficiency
- **Capacity**: Capacity utilization
- **Costs**: Operational costs

## Best Practices

### Job Planning
1. **Plan Ahead**: Plan jobs in advance
2. **Resource Allocation**: Allocate resources properly
3. **Capacity Planning**: Consider capacity constraints
4. **Scheduling**: Schedule jobs efficiently

### Execution
1. **Follow Procedures**: Follow standard procedures
2. **Document Everything**: Document all operations
3. **Quality Control**: Maintain quality standards
4. **Safety First**: Prioritize safety

### Monitoring
1. **Track Progress**: Monitor job progress
2. **Identify Issues**: Identify and resolve issues
3. **Optimize Performance**: Continuously improve
4. **Report Results**: Report on results

## Common Issues

### Q: How do I change the status of a warehouse job?
A: Use the status field in the Warehouse Job record. Some status changes are automatic based on operations.

### Q: Can I modify a job after it's started?
A: Yes, but some modifications may require cancelling and recreating the job.

### Q: How do I track job progress?
A: Use the operations section to track completed operations and the dashboard for overall progress.

## Related Documentation
- [Storage Locations](./storage-locations)
- [Handling Unit Types](./handling-unit-types)
- [VAS Operations](./vas-operations)
- [Billing and Contracts](./billing-contracts)
"""

    create_wiki_page("warehouse-jobs", "Warehouse Jobs Operations", content, "warehousing")


def create_vas_operations_guide():
    """Create VAS operations guide"""
    
    content = """# Value-Added Services (VAS) Operations

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

### Logistics Services
- **Cross-docking**: Direct transfer without storage
- **Consolidation**: Combine shipments
- **Deconsolidation**: Split shipments
- **Sorting**: Sort items by destination

## VAS Order Types

### Creating VAS Order Types
1. Go to **Warehousing** > **Setup** > **VAS Order Type**
2. Click **New** to create a new type
3. Configure the order type:
   - **Code**: Unique identifier
   - **Description**: Service description
   - **Category**: Service category
   - **Billing Method**: How to bill for the service
   - **Standard Hours**: Standard time required

### VAS Order Type Configuration

#### Service Categories
- **Packaging**: Packaging-related services
- **Quality**: Quality-related services
- **Processing**: Processing services
- **Logistics**: Logistics services

#### Billing Methods
- **Per Unit**: Charge per unit processed
- **Per Hour**: Charge per hour worked
- **Per Order**: Fixed charge per order
- **Per Volume**: Charge based on volume
- **Per Weight**: Charge based on weight

## VAS Orders

### Creating VAS Orders
1. Go to **Warehousing** > **Operations** > **VAS Order**
2. Click **New** to create a new order
3. Fill in the order details:
   - **Customer**: Customer for the service
   - **VAS Order Type**: Type of service
   - **Items**: Items to be processed
   - **Services**: Specific services required
   - **Charges**: Applicable charges

### VAS Order Management

#### Order Details
- **Customer**: Customer requesting the service
- **VAS Order Type**: Type of value-added service
- **Reference Order**: Related sales order or purchase order
- **Order Date**: Date the order was placed
- **Required Date**: Date service is required

#### Service Items
- **Items**: Items to be processed
- **Quantities**: Quantities to process
- **Services**: Specific services required
- **Charges**: Charges for each service

#### Service Operations
- **Operations**: Operations to perform
- **Resources**: Resources required
- **Timeline**: Service timeline
- **Quality**: Quality requirements

## VAS Operations

### Operation Types
- **Packaging**: Packaging operations
- **Labeling**: Labeling operations
- **Assembly**: Assembly operations
- **Inspection**: Inspection operations
- **Testing**: Testing operations
- **Documentation**: Documentation operations

### Operation Configuration
- **Operation**: Specific operation to perform
- **Description**: Operation description
- **Standard Hours**: Standard time required
- **Resources**: Resources needed
- **Quality**: Quality requirements
- **Documentation**: Required documentation

## Resource Management

### Resource Types
- **Labor**: Human resources
- **Equipment**: Equipment and machinery
- **Materials**: Consumable materials
- **Facilities**: Facility requirements

### Resource Allocation
- **Scheduling**: Schedule resources
- **Capacity**: Resource capacity
- **Availability**: Resource availability
- **Costs**: Resource costs

## Quality Management

### Quality Requirements
- **Standards**: Quality standards to meet
- **Procedures**: Quality procedures
- **Documentation**: Quality documentation
- **Certification**: Quality certifications

### Quality Control
- **Inspection**: Quality inspection
- **Testing**: Quality testing
- **Documentation**: Quality documentation
- **Certification**: Quality certification

## Billing and Pricing

### Pricing Models
- **Fixed Price**: Fixed price per service
- **Time and Materials**: Based on time and materials
- **Volume-based**: Based on volume processed
- **Weight-based**: Based on weight processed

### Charge Calculation
- **Service Charges**: Charges for services
- **Material Charges**: Charges for materials
- **Labor Charges**: Charges for labor
- **Overhead**: Overhead charges

## VAS Workflow

### Order Processing
1. **Order Creation**: Create VAS order
2. **Order Approval**: Approve the order
3. **Resource Allocation**: Allocate resources
4. **Service Execution**: Execute the service
5. **Quality Control**: Perform quality control
6. **Delivery**: Deliver completed service

### Status Management
- **Draft**: Order is being created
- **Approved**: Order is approved
- **In Progress**: Service is being performed
- **Completed**: Service is completed
- **Delivered**: Service is delivered

## Reporting and Analytics

### VAS Reports
- **Service Performance**: Performance metrics
- **Resource Utilization**: Resource utilization
- **Quality Metrics**: Quality performance
- **Cost Analysis**: Cost analysis

### Operational Reports
- **Throughput**: Services performed
- **Efficiency**: Operational efficiency
- **Quality**: Quality performance
- **Costs**: Operational costs

## Best Practices

### Service Design
1. **Customer Focus**: Focus on customer needs
2. **Quality Standards**: Maintain high quality
3. **Efficiency**: Optimize service delivery
4. **Innovation**: Continuously improve

### Resource Management
1. **Capacity Planning**: Plan resource capacity
2. **Scheduling**: Schedule resources efficiently
3. **Training**: Train resources properly
4. **Maintenance**: Maintain equipment

### Quality Management
1. **Standards**: Establish quality standards
2. **Procedures**: Follow quality procedures
3. **Documentation**: Document quality processes
4. **Continuous Improvement**: Continuously improve

## Common Issues

### Q: How do I create a new VAS order type?
A: Go to Warehousing > Setup > VAS Order Type and create a new record with the required configuration.

### Q: Can I modify a VAS order after it's started?
A: Yes, but some modifications may require approval or may not be possible depending on the service status.

### Q: How do I track VAS order progress?
A: Use the operations section to track completed operations and the dashboard for overall progress.

## Related Documentation
- [Warehouse Jobs](./warehouse-jobs)
- [Billing and Contracts](./billing-contracts)
- [Quality Management](./quality-management)
- [Resource Management](./resource-management)
"""

    create_wiki_page("vas-operations", "Value-Added Services (VAS) Operations", content, "warehousing")


def create_billing_contracts_guide():
    """Create billing and contracts guide"""
    
    content = """# Billing and Contracts Management

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

### Contract Configuration

#### Basic Information
- **Customer**: Customer for the contract
- **Contract Number**: Unique contract identifier
- **Contract Type**: Type of contract (Storage, Handling, VAS, etc.)
- **Status**: Contract status (Draft, Active, Expired, etc.)
- **Start Date**: Contract start date
- **End Date**: Contract end date

#### Contract Terms
- **Payment Terms**: Payment terms and conditions
- **Billing Frequency**: How often to bill (Monthly, Quarterly, etc.)
- **Currency**: Contract currency
- **Tax Settings**: Tax configuration
- **Discounts**: Applicable discounts

#### Contract Items
- **Services**: Services covered by the contract
- **Pricing**: Pricing for each service
- **Minimum Charges**: Minimum charges
- **Maximum Charges**: Maximum charges
- **Volume Discounts**: Volume-based discounts

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

### VAS Contracts
- **Packaging Services**: Packaging-related services
- **Quality Services**: Quality-related services
- **Processing Services**: Processing services
- **Logistics Services**: Logistics services

## Pricing Models

### Volume-based Pricing
- **Per Cubic Meter**: Charge per cubic meter
- **Per Pallet**: Charge per pallet
- **Per Container**: Charge per container
- **Tiered Pricing**: Different rates for different volumes

### Weight-based Pricing
- **Per Kilogram**: Charge per kilogram
- **Per Ton**: Charge per ton
- **Weight Tiers**: Different rates for different weights
- **Minimum Weight**: Minimum weight charges

### Time-based Pricing
- **Per Day**: Charge per day
- **Per Week**: Charge per week
- **Per Month**: Charge per month
- **Overtime Rates**: Overtime charges

### Service-based Pricing
- **Per Operation**: Charge per operation
- **Per Hour**: Charge per hour
- **Per Order**: Fixed charge per order
- **Per Item**: Charge per item processed

## Periodic Billing

### Billing Configuration
1. Go to **Warehousing** > **Billing** > **Periodic Billing**
2. Configure billing parameters:
   - **Billing Period**: Monthly, quarterly, etc.
   - **Billing Date**: When to generate bills
   - **Customer**: Customer to bill
   - **Contract**: Applicable contract

### Billing Process
1. **Data Collection**: Collect billing data
2. **Calculation**: Calculate charges
3. **Validation**: Validate billing data
4. **Generation**: Generate billing documents
5. **Approval**: Approve billing documents
6. **Delivery**: Deliver to customers

### Billing Components

#### Storage Charges
- **Volume Charges**: Charges based on volume
- **Weight Charges**: Charges based on weight
- **Time Charges**: Charges based on time
- **Location Charges**: Charges based on location

#### Handling Charges
- **Inbound Charges**: Inbound processing charges
- **Outbound Charges**: Outbound processing charges
- **Transfer Charges**: Transfer charges
- **Special Handling**: Special handling charges

#### VAS Charges
- **Service Charges**: Value-added service charges
- **Material Charges**: Material charges
- **Labor Charges**: Labor charges
- **Equipment Charges**: Equipment charges

## Charge Management

### Charge Types
- **Storage Charges**: Storage-related charges
- **Handling Charges**: Handling-related charges
- **VAS Charges**: Value-added service charges
- **Special Charges**: Special service charges

### Charge Calculation
- **Automatic Calculation**: System calculates charges
- **Manual Override**: Manual charge adjustments
- **Discounts**: Apply discounts
- **Taxes**: Calculate taxes

### Charge Validation
- **Data Validation**: Validate billing data
- **Calculation Verification**: Verify calculations
- **Approval Process**: Approval workflow
- **Exception Handling**: Handle exceptions

## Billing Reports

### Customer Billing
- **Invoice Summary**: Summary of invoices
- **Detailed Invoices**: Detailed invoice information
- **Payment Status**: Payment status tracking
- **Outstanding Balances**: Outstanding balances

### Operational Reports
- **Revenue Reports**: Revenue analysis
- **Cost Reports**: Cost analysis
- **Profitability**: Profitability analysis
- **Performance**: Performance metrics

## Contract Management

### Contract Lifecycle
1. **Draft**: Contract is being created
2. **Review**: Contract is under review
3. **Approved**: Contract is approved
4. **Active**: Contract is active
5. **Expired**: Contract has expired
6. **Renewed**: Contract is renewed

### Contract Monitoring
- **Performance**: Contract performance
- **Compliance**: Contract compliance
- **Renewals**: Contract renewals
- **Modifications**: Contract modifications

## Best Practices

### Contract Design
1. **Clear Terms**: Use clear and specific terms
2. **Fair Pricing**: Set fair and competitive pricing
3. **Flexibility**: Allow for modifications
4. **Risk Management**: Manage contract risks

### Billing Accuracy
1. **Data Quality**: Ensure data quality
2. **Validation**: Validate billing data
3. **Reconciliation**: Reconcile billing data
4. **Audit Trail**: Maintain audit trail

### Customer Relations
1. **Transparency**: Be transparent about charges
2. **Communication**: Communicate clearly
3. **Support**: Provide billing support
4. **Resolution**: Resolve billing issues quickly

## Common Issues

### Q: How do I modify a contract after it's active?
A: Create a contract amendment to modify active contracts. Some changes may require customer approval.

### Q: Can I change pricing during a contract period?
A: Yes, but changes typically require contract amendments and customer approval.

### Q: How do I handle billing disputes?
A: Use the billing dispute process to investigate and resolve billing issues with customers.

## Related Documentation
- [Warehouse Jobs](./warehouse-jobs)
- [VAS Operations](./vas-operations)
- [Periodic Billing](./periodic-billing)
- [Customer Management](./customer-management)
"""

    create_wiki_page("billing-contracts", "Billing and Contracts Management", content, "warehousing")


def create_sustainability_guide():
    """Create sustainability and reporting guide"""
    
    content = """# Sustainability and Reporting

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

### Waste Management
- **Waste Generation**: Track waste generation
- **Waste Types**: Categorize waste types
- **Recycling**: Track recycling rates
- **Disposal**: Monitor disposal methods

## Sustainability Configuration

### Carbon Emission Factors
1. Go to **Warehousing** > **Sustainability** > **Carbon Emission Factor**
2. Configure emission factors:
   - **Activity Type**: Type of activity
   - **Emission Factor**: CO2 equivalent per unit
   - **Unit of Measure**: Unit for the factor
   - **Source**: Source of the factor

### Energy Consumption Tracking
1. Go to **Warehousing** > **Sustainability** > **Energy Consumption**
2. Record energy consumption:
   - **Energy Type**: Type of energy (Electricity, Gas, etc.)
   - **Consumption**: Amount consumed
   - **Period**: Time period
   - **Source**: Energy source

### Green Certifications
1. Go to **Warehousing** > **Sustainability** > **Green Certification**
2. Manage certifications:
   - **Certification Type**: Type of certification
   - **Certification Body**: Certifying organization
   - **Valid From**: Certification start date
   - **Valid To**: Certification end date

## Sustainability Reports

### Carbon Footprint Reports
- **Total Emissions**: Total carbon emissions
- **Emission by Source**: Emissions by source
- **Emission Trends**: Emission trends over time
- **Reduction Progress**: Progress toward reduction targets

### Energy Reports
- **Energy Consumption**: Energy consumption data
- **Energy Efficiency**: Energy efficiency metrics
- **Cost Analysis**: Energy cost analysis
- **Optimization**: Optimization opportunities

### Waste Reports
- **Waste Generation**: Waste generation data
- **Recycling Rates**: Recycling performance
- **Waste Reduction**: Waste reduction progress
- **Disposal Methods**: Disposal method analysis

## Green Initiatives

### Renewable Energy
- **Solar Power**: Solar energy usage
- **Wind Power**: Wind energy usage
- **Other Renewables**: Other renewable sources
- **Green Energy Certificates**: Green energy certificates

### Energy Efficiency
- **LED Lighting**: LED lighting implementation
- **Smart Systems**: Smart building systems
- **Insulation**: Building insulation
- **HVAC Optimization**: HVAC system optimization

### Waste Reduction
- **Packaging Optimization**: Optimize packaging
- **Recycling Programs**: Implement recycling
- **Waste Reduction**: Reduce waste generation
- **Circular Economy**: Circular economy practices

## Compliance and Certifications

### Environmental Compliance
- **Regulatory Requirements**: Meet regulatory requirements
- **Environmental Standards**: Follow environmental standards
- **Audit Preparation**: Prepare for audits
- **Compliance Reporting**: Generate compliance reports

### Green Certifications
- **LEED Certification**: LEED building certification
- **ISO 14001**: ISO 14001 environmental management
- **BREEAM**: BREEAM sustainability assessment
- **Other Certifications**: Other green certifications

## Sustainability Dashboard

### Key Metrics
- **Carbon Footprint**: Total carbon footprint
- **Energy Consumption**: Energy consumption trends
- **Waste Generation**: Waste generation trends
- **Green Score**: Overall green score

### Performance Indicators
- **Emission Intensity**: Emissions per unit of activity
- **Energy Intensity**: Energy per unit of activity
- **Waste Intensity**: Waste per unit of activity
- **Efficiency Ratios**: Various efficiency ratios

### Trend Analysis
- **Historical Trends**: Historical performance
- **Forecasting**: Future projections
- **Benchmarking**: Industry benchmarking
- **Target Tracking**: Progress toward targets

## Best Practices

### Environmental Management
1. **Set Targets**: Set clear environmental targets
2. **Monitor Performance**: Monitor environmental performance
3. **Continuous Improvement**: Continuously improve
4. **Stakeholder Engagement**: Engage stakeholders

### Data Management
1. **Accurate Data**: Ensure data accuracy
2. **Regular Updates**: Update data regularly
3. **Validation**: Validate data quality
4. **Documentation**: Document processes

### Reporting
1. **Regular Reports**: Generate regular reports
2. **Transparency**: Be transparent about performance
3. **Stakeholder Communication**: Communicate with stakeholders
4. **Action Planning**: Plan corrective actions

## Common Issues

### Q: How do I set up carbon emission tracking?
A: Configure carbon emission factors and set up tracking for different activities in your warehouse operations.

### Q: Can I track energy consumption from different sources?
A: Yes, you can track energy consumption from electricity, gas, and other sources separately.

### Q: How do I generate sustainability reports?
A: Use the sustainability dashboard and reports section to generate various sustainability reports.

## Related Documentation
- [Warehouse Settings](./warehouse-settings)
- [Capacity Management](./capacity-management)
- [Billing and Contracts](./billing-contracts)
- [Reporting and Analytics](./reporting-analytics)
"""

    create_wiki_page("sustainability", "Sustainability and Reporting", content, "warehousing")


def create_wiki_page(page_name, title, content, space):
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
            "space": space,
            "published": 1
        })
        wiki_page.insert(ignore_permissions=True)
        print(f"✅ Wiki page '{page_name}' created")
    except Exception as e:
        print(f"ℹ️ Could not create wiki page '{page_name}': {e}")


if __name__ == "__main__":
    create_warehousing_wiki_documentation()

