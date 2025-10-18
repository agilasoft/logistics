# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def fix_all_wiki_links():
    """Fix all broken links and create missing guides"""
    
    print("🔧 Fixing all wiki links and creating missing guides...")
    
    # First, create all missing guides
    create_missing_guides()
    
    # Then fix all broken links
    fix_broken_links()
    
    print("✅ All wiki links and guides have been fixed!")


def create_missing_guides():
    """Create all missing guides"""
    
    print("📝 Creating missing guides...")
    
    missing_guides = [
        {
            "name": "inbound-operations",
            "title": "Inbound Operations",
            "content": """# Inbound Operations

## Overview
Inbound operations handle the receiving and processing of incoming shipments and materials.

## Key Processes

### Receiving
- **Documentation Review**: Check shipping documents
- **Physical Inspection**: Inspect items for damage
- **Quantity Verification**: Verify received quantities
- **Quality Control**: Perform quality checks

### Putaway
- **Location Assignment**: Assign storage locations
- **Inventory Update**: Update inventory records
- **Labeling**: Apply location labels
- **Documentation**: Complete putaway documentation

## Best Practices
- Verify all documentation before receiving
- Inspect items immediately upon arrival
- Update inventory records in real-time
- Maintain accurate location records

## Related Topics
- [Storage Locations Setup](./locations)
- [Warehouse Jobs Operations](./jobs)
- [Quality Management](./quality)
"""
        },
        {
            "name": "outbound-operations", 
            "title": "Outbound Operations",
            "content": """# Outbound Operations

## Overview
Outbound operations handle the picking, packing, and shipping of customer orders.

## Key Processes

### Picking
- **Order Review**: Review customer orders
- **Location Planning**: Plan picking routes
- **Item Collection**: Collect items from locations
- **Quality Check**: Verify picked items

### Packing
- **Packaging Selection**: Choose appropriate packaging
- **Item Protection**: Protect items during packing
- **Labeling**: Apply shipping labels
- **Documentation**: Complete packing documentation

## Best Practices
- Optimize picking routes for efficiency
- Use appropriate packaging materials
- Verify all items before packing
- Maintain accurate shipping records

## Related Topics
- [Storage Locations Setup](./locations)
- [Warehouse Jobs Operations](./jobs)
- [Quality Management](./quality)
"""
        },
        {
            "name": "transfer-operations",
            "title": "Transfer Operations",
            "content": """# Transfer Operations

## Overview
Transfer operations handle the movement of goods between different locations within the warehouse or between warehouses.

## Key Processes

### Internal Transfers
- **Location Planning**: Plan transfer routes
- **Item Movement**: Move items between locations
- **Documentation**: Update location records
- **Inventory Update**: Update inventory records

### Inter-Warehouse Transfers
- **Documentation**: Prepare transfer documentation
- **Shipping**: Arrange transportation
- **Receiving**: Process at destination
- **Reconciliation**: Reconcile inventory records

## Best Practices
- Plan transfers efficiently
- Maintain accurate documentation
- Update inventory records promptly
- Verify all transfers

## Related Topics
- [Storage Locations Setup](./locations)
- [Warehouse Jobs Operations](./jobs)
- [Capacity Management](./capacity)
"""
        },
        {
            "name": "periodic-billing",
            "title": "Periodic Billing",
            "content": """# Periodic Billing

## Overview
Periodic billing automatically generates invoices for warehouse services based on usage and contracts.

## Billing Components

### Storage Charges
- **Volume-based**: Charges based on storage volume
- **Weight-based**: Charges based on weight
- **Time-based**: Charges based on storage duration
- **Location-based**: Charges based on storage location

### Handling Charges
- **Inbound Processing**: Charges for receiving services
- **Outbound Processing**: Charges for shipping services
- **Transfer Services**: Charges for internal transfers
- **Special Handling**: Charges for special requirements

## Configuration
1. **Billing Periods**: Set up billing cycles
2. **Charge Rates**: Configure charge rates
3. **Customer Contracts**: Link to customer agreements
4. **Automation**: Enable automatic billing

## Best Practices
- Review billing data before generating invoices
- Maintain accurate usage records
- Communicate charges clearly to customers
- Process billing on schedule

## Related Topics
- [Billing and Contracts Management](./billing)
- [Charges Management](./charges)
- [Customer Management](./customer)
"""
        },
        {
            "name": "charges-management",
            "title": "Charges Management",
            "content": """# Charges Management

## Overview
Charges management handles the configuration and application of various warehouse service charges.

## Charge Types

### Storage Charges
- **Daily Storage**: Per-day storage charges
- **Monthly Storage**: Per-month storage charges
- **Volume-based**: Charges based on storage volume
- **Weight-based**: Charges based on weight

### Handling Charges
- **Receiving**: Charges for receiving services
- **Picking**: Charges for picking services
- **Packing**: Charges for packing services
- **Shipping**: Charges for shipping services

### Special Services
- **VAS Operations**: Value-added services
- **Quality Control**: Quality inspection charges
- **Special Handling**: Special requirement charges
- **Emergency Services**: Emergency service charges

## Configuration
1. **Charge Rates**: Set up charge rates
2. **Customer Contracts**: Link to customer agreements
3. **Automation**: Enable automatic charging
4. **Billing**: Link to billing processes

## Best Practices
- Maintain accurate charge records
- Review charges regularly
- Communicate charges clearly
- Process charges efficiently

## Related Topics
- [Periodic Billing](./periodic-billing)
- [Billing and Contracts Management](./billing)
- [Customer Management](./customer)
"""
        },
        {
            "name": "customer-management",
            "title": "Customer Management",
            "content": """# Customer Management

## Overview
Customer management handles customer information, contracts, and service agreements.

## Key Components

### Customer Information
- **Basic Details**: Name, address, contact information
- **Service Preferences**: Preferred services and options
- **Billing Information**: Billing address and payment terms
- **Service History**: Historical service records

### Contracts and Agreements
- **Service Contracts**: Service level agreements
- **Billing Terms**: Payment terms and conditions
- **Service Levels**: Service level commitments
- **Special Requirements**: Special handling requirements

## Best Practices
- Maintain accurate customer records
- Review contracts regularly
- Communicate clearly with customers
- Provide excellent service

## Related Topics
- [Billing and Contracts Management](./billing)
- [Periodic Billing](./periodic-billing)
- [Charges Management](./charges)
"""
        },
        {
            "name": "reporting-analytics",
            "title": "Reporting and Analytics",
            "content": """# Reporting and Analytics

## Overview
Reporting and analytics provide insights into warehouse operations, performance, and trends.

## Key Reports

### Operational Reports
- **Inventory Reports**: Current inventory levels
- **Movement Reports**: Item movement tracking
- **Performance Reports**: Operational performance metrics
- **Utilization Reports**: Resource utilization

### Financial Reports
- **Billing Reports**: Billing and revenue reports
- **Cost Reports**: Cost analysis and trends
- **Profitability Reports**: Profitability analysis
- **Customer Reports**: Customer-specific reports

### Analytics
- **Trend Analysis**: Performance trends
- **Forecasting**: Demand forecasting
- **Optimization**: Process optimization
- **Benchmarking**: Performance benchmarking

## Best Practices
- Generate reports regularly
- Analyze trends and patterns
- Use data for decision making
- Share insights with stakeholders

## Related Topics
- [Sustainability and Reporting](./sustainability)
- [Capacity Management](./capacity)
- [Quality Management](./quality)
"""
        },
        {
            "name": "best-practices",
            "title": "Best Practices",
            "content": """# Best Practices

## Overview
Best practices guide for warehouse operations to ensure efficiency, quality, and compliance.

## Operational Best Practices

### Inventory Management
- **Regular Audits**: Conduct regular inventory audits
- **Cycle Counting**: Implement cycle counting programs
- **Location Accuracy**: Maintain accurate location records
- **FIFO/LIFO**: Follow appropriate rotation methods

### Process Optimization
- **Standardization**: Standardize processes and procedures
- **Automation**: Automate repetitive tasks
- **Training**: Provide comprehensive training
- **Continuous Improvement**: Implement continuous improvement

### Quality Control
- **Inspection Procedures**: Implement inspection procedures
- **Quality Standards**: Maintain quality standards
- **Documentation**: Maintain quality documentation
- **Corrective Actions**: Implement corrective actions

## Best Practices
- Follow established procedures
- Maintain high quality standards
- Continuously improve processes
- Train staff effectively

## Related Topics
- [Quality Management](./quality)
- [Security and Compliance](./security)
- [Troubleshooting Guide](./troubleshooting)
"""
        },
        {
            "name": "integration-guide",
            "title": "Integration Guide",
            "content": """# Integration Guide

## Overview
Integration guide for connecting CargoNext with external systems and services.

## Integration Types

### ERP Integration
- **SAP Integration**: SAP system integration
- **Oracle Integration**: Oracle system integration
- **Custom ERP**: Custom ERP system integration
- **Data Synchronization**: Real-time data sync

### E-commerce Integration
- **Shopify Integration**: Shopify store integration
- **Magento Integration**: Magento store integration
- **WooCommerce Integration**: WooCommerce store integration
- **Custom E-commerce**: Custom e-commerce integration

### Logistics Integration
- **Shipping Carriers**: Shipping carrier integration
- **Tracking Systems**: Package tracking integration
- **Route Optimization**: Route optimization integration
- **Fleet Management**: Fleet management integration

## Configuration
1. **API Setup**: Configure API connections
2. **Authentication**: Set up authentication
3. **Data Mapping**: Map data fields
4. **Testing**: Test integrations

## Best Practices
- Test integrations thoroughly
- Maintain security standards
- Monitor integration performance
- Document integration processes

## Related Topics
- [Automation and Integration](./automation)
- [Security and Compliance](./security)
- [Troubleshooting Guide](./troubleshooting)
"""
        }
    ]
    
    created_count = 0
    for guide in missing_guides:
        try:
            if not frappe.db.exists("Wiki Page", {"route": f"warehousing/{guide['name']}"}):
                wiki_page = frappe.get_doc({
                    "doctype": "Wiki Page",
                    "title": guide["title"],
                    "content": guide["content"],
                    "route": f"warehousing/{guide['name']}",
                    "published": 1
                })
                wiki_page.insert(ignore_permissions=True)
                print(f"✅ Created: {guide['title']}")
                created_count += 1
            else:
                print(f"ℹ️ Already exists: {guide['title']}")
        except Exception as e:
            print(f"ℹ️ Could not create {guide['title']}: {e}")
    
    frappe.db.commit()
    print(f"\n✅ Created {created_count} missing guides")


def fix_broken_links():
    """Fix all broken links in wiki pages"""
    
    print("🔗 Fixing broken links...")
    
    # Define the correct link mappings
    link_mappings = {
        "./warehouse-settings": "./settings",
        "./storage-locations": "./locations", 
        "./handling-unit-types": "./handling-units",
        "./warehouse-jobs": "./jobs",
        "./vas-operations": "./vas",
        "./billing-contracts": "./billing",
        "./capacity-management": "./capacity",
        "./quality-management": "./quality",
        "./sustainability": "./sustainability",
        "./security-compliance": "./security",
        "./troubleshooting": "./troubleshooting",
        "./inbound-operations": "./inbound-operations",
        "./outbound-operations": "./outbound-operations",
        "./periodic-billing": "./periodic-billing",
        "./charges-management": "./charges",
        "./customer-management": "./customer",
        "./reporting-analytics": "./reporting-analytics",
        "./best-practices": "./best-practices",
        "./integration-guide": "./integration-guide",
        "./storage-types": "./handling-units",  # Map to handling units
        "./resource-management": "./capacity"   # Map to capacity management
    }
    
    # Get all wiki pages
    pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'content'])
    
    updated_count = 0
    for page in pages:
        if page.content:
            content = page.content
            original_content = content
            
            # Replace all broken links with correct ones
            for old_link, new_link in link_mappings.items():
                content = content.replace(old_link, new_link)
            
            # If content was updated, save it
            if content != original_content:
                try:
                    frappe.db.set_value('Wiki Page', page.name, 'content', content)
                    print(f"✅ Fixed links in: {page.title}")
                    updated_count += 1
                except Exception as e:
                    print(f"ℹ️ Could not update {page.title}: {e}")
    
    frappe.db.commit()
    print(f"\n✅ Fixed links in {updated_count} pages")


if __name__ == "__main__":
    fix_all_wiki_links()

