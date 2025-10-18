# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def create_additional_warehousing_guides():
    """Create additional specialized warehousing guides"""
    
    print("📚 Creating additional specialized warehousing guides...")
    
    # Create specialized guides
    create_capacity_management_guide()
    create_quality_management_guide()
    create_security_compliance_guide()
    create_automation_integration_guide()
    create_troubleshooting_guide()
    
    print("✅ Additional warehousing guides created successfully!")


def create_capacity_management_guide():
    """Create capacity management guide"""
    
    content = """# Capacity Management

## Overview
Capacity management ensures optimal utilization of warehouse space, equipment, and resources. It provides real-time monitoring, alerts, and optimization recommendations.

## Capacity Types

### Volume Capacity
- **Total Volume**: Total available volume
- **Used Volume**: Currently used volume
- **Available Volume**: Available volume
- **Utilization %**: Volume utilization percentage

### Weight Capacity
- **Total Weight**: Total weight capacity
- **Used Weight**: Currently used weight
- **Available Weight**: Available weight capacity
- **Utilization %**: Weight utilization percentage

### Handling Unit Capacity
- **Total Units**: Total handling unit capacity
- **Used Units**: Currently used units
- **Available Units**: Available unit capacity
- **Utilization %**: Unit utilization percentage

## Capacity Monitoring

### Real-time Monitoring
- **Dashboard**: Real-time capacity dashboard
- **Alerts**: Capacity alert system
- **Thresholds**: Capacity threshold settings
- **Notifications**: Automated notifications

### Capacity Reports
- **Utilization Reports**: Capacity utilization reports
- **Trend Analysis**: Capacity trend analysis
- **Forecasting**: Capacity forecasting
- **Optimization**: Optimization recommendations

## Capacity Planning

### Planning Process
1. **Current Analysis**: Analyze current capacity
2. **Demand Forecasting**: Forecast future demand
3. **Capacity Planning**: Plan capacity requirements
4. **Implementation**: Implement capacity changes

### Planning Tools
- **Capacity Models**: Capacity planning models
- **Scenario Analysis**: Scenario analysis tools
- **Optimization**: Optimization algorithms
- **Simulation**: Capacity simulation

## Best Practices

### Capacity Optimization
1. **Regular Monitoring**: Monitor capacity regularly
2. **Proactive Management**: Manage capacity proactively
3. **Optimization**: Continuously optimize capacity
4. **Planning**: Plan for future capacity needs

### Resource Management
1. **Efficient Allocation**: Allocate resources efficiently
2. **Flexibility**: Maintain operational flexibility
3. **Scalability**: Plan for scalability
4. **Cost Optimization**: Optimize capacity costs
"""

    create_wiki_page("capacity-management", "Capacity Management", content, "warehousing")


def create_quality_management_guide():
    """Create quality management guide"""
    
    content = """# Quality Management

## Overview
Quality management ensures consistent quality standards across all warehouse operations. It includes quality control, quality assurance, and continuous improvement processes.

## Quality Standards

### Quality Control
- **Inspection Procedures**: Quality inspection procedures
- **Testing Protocols**: Quality testing protocols
- **Documentation**: Quality documentation
- **Certification**: Quality certifications

### Quality Assurance
- **Process Standards**: Process quality standards
- **Training**: Quality training programs
- **Audits**: Quality audits
- **Continuous Improvement**: Continuous improvement processes

## Quality Processes

### Inbound Quality
- **Receiving Inspection**: Inbound quality inspection
- **Documentation Review**: Documentation review
- **Sampling**: Quality sampling procedures
- **Acceptance Criteria**: Acceptance criteria

### Outbound Quality
- **Packing Quality**: Packing quality standards
- **Documentation**: Outbound documentation
- **Final Inspection**: Final quality inspection
- **Customer Requirements**: Customer quality requirements

### Internal Quality
- **Process Quality**: Internal process quality
- **Storage Quality**: Storage quality standards
- **Handling Quality**: Handling quality standards
- **Documentation**: Internal quality documentation

## Quality Tools

### Quality Metrics
- **Defect Rates**: Defect rate tracking
- **Quality Scores**: Quality performance scores
- **Customer Satisfaction**: Customer satisfaction metrics
- **Process Efficiency**: Process efficiency metrics

### Quality Reports
- **Quality Dashboard**: Quality performance dashboard
- **Trend Analysis**: Quality trend analysis
- **Root Cause Analysis**: Root cause analysis
- **Improvement Plans**: Quality improvement plans

## Best Practices

### Quality Culture
1. **Quality First**: Prioritize quality in all operations
2. **Training**: Train staff on quality standards
3. **Communication**: Communicate quality requirements
4. **Recognition**: Recognize quality achievements

### Continuous Improvement
1. **Regular Reviews**: Review quality performance regularly
2. **Feedback**: Collect and act on feedback
3. **Innovation**: Innovate quality processes
4. **Benchmarking**: Benchmark against best practices
"""

    create_wiki_page("quality-management", "Quality Management", content, "warehousing")


def create_security_compliance_guide():
    """Create security and compliance guide"""
    
    content = """# Security and Compliance

## Overview
Security and compliance management ensures warehouse operations meet regulatory requirements and security standards. It includes access control, security monitoring, and compliance reporting.

## Security Measures

### Access Control
- **Physical Access**: Physical access control systems
- **Digital Access**: Digital access control
- **Authorization**: Authorization procedures
- **Monitoring**: Access monitoring

### Security Systems
- **Surveillance**: Security surveillance systems
- **Alarms**: Security alarm systems
- **Sensors**: Security sensors
- **Response**: Security response procedures

### Data Security
- **Data Protection**: Data protection measures
- **Encryption**: Data encryption
- **Backup**: Data backup procedures
- **Recovery**: Data recovery procedures

## Compliance Management

### Regulatory Compliance
- **Industry Standards**: Industry compliance standards
- **Government Regulations**: Government regulations
- **International Standards**: International standards
- **Local Requirements**: Local compliance requirements

### Compliance Monitoring
- **Audits**: Compliance audits
- **Reporting**: Compliance reporting
- **Documentation**: Compliance documentation
- **Training**: Compliance training

### Compliance Tools
- **Compliance Dashboard**: Compliance monitoring dashboard
- **Alert System**: Compliance alert system
- **Reporting**: Compliance reporting tools
- **Documentation**: Compliance documentation system

## Best Practices

### Security Implementation
1. **Risk Assessment**: Assess security risks
2. **Security Policies**: Implement security policies
3. **Training**: Train staff on security procedures
4. **Monitoring**: Monitor security continuously

### Compliance Management
1. **Regular Audits**: Conduct regular compliance audits
2. **Documentation**: Maintain compliance documentation
3. **Training**: Provide compliance training
4. **Updates**: Keep up with regulatory changes
"""

    create_wiki_page("security-compliance", "Security and Compliance", content, "warehousing")


def create_automation_integration_guide():
    """Create automation and integration guide"""
    
    content = """# Automation and Integration

## Overview
Automation and integration capabilities enhance warehouse operations through technology integration, process automation, and system connectivity.

## Automation Systems

### Warehouse Management Systems (WMS)
- **WMS Integration**: WMS system integration
- **Data Synchronization**: Data synchronization
- **Process Automation**: Process automation
- **Real-time Updates**: Real-time system updates

### Material Handling Systems
- **Conveyor Systems**: Conveyor system integration
- **Automated Storage**: Automated storage systems
- **Robotic Systems**: Robotic system integration
- **Sorting Systems**: Automated sorting systems

### Information Systems
- **ERP Integration**: ERP system integration
- **TMS Integration**: Transportation management integration
- **Customer Systems**: Customer system integration
- **Supplier Systems**: Supplier system integration

## Integration Capabilities

### API Integration
- **REST APIs**: REST API integration
- **SOAP APIs**: SOAP API integration
- **Webhooks**: Webhook integration
- **Real-time Sync**: Real-time synchronization

### Data Integration
- **Data Mapping**: Data mapping and transformation
- **Data Validation**: Data validation and cleansing
- **Data Synchronization**: Data synchronization
- **Error Handling**: Error handling and recovery

### Process Integration
- **Workflow Integration**: Workflow integration
- **Process Automation**: Process automation
- **Business Rules**: Business rule integration
- **Exception Handling**: Exception handling

## Best Practices

### Integration Planning
1. **Requirements Analysis**: Analyze integration requirements
2. **System Design**: Design integration architecture
3. **Testing**: Test integration thoroughly
4. **Documentation**: Document integration processes

### Automation Implementation
1. **Process Analysis**: Analyze processes for automation
2. **Technology Selection**: Select appropriate technology
3. **Implementation**: Implement automation solutions
4. **Monitoring**: Monitor automation performance
"""

    create_wiki_page("automation-integration", "Automation and Integration", content, "warehousing")


def create_troubleshooting_guide():
    """Create troubleshooting guide"""
    
    content = """# Troubleshooting Guide

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

#### Operations Not Completing
**Problem**: Operations are not completing properly
**Solutions**:
1. Check operation status and dependencies
2. Verify resource availability
3. Review operation parameters
4. Check for system constraints

### Storage Location Issues

#### Location Not Available
**Problem**: Storage location is not available for allocation
**Solutions**:
1. Check location status (active/inactive)
2. Verify capacity availability
3. Check access permissions
4. Review location constraints

#### Capacity Exceeded
**Problem**: Storage location capacity is exceeded
**Solutions**:
1. Check current utilization
2. Reallocate items to other locations
3. Increase location capacity
4. Implement capacity management rules

### Billing Issues

#### Charges Not Calculating
**Problem**: Billing charges are not calculating correctly
**Solutions**:
1. Check billing configuration
2. Verify contract terms
3. Review charge definitions
4. Check billing rules and formulas

#### Billing Discrepancies
**Problem**: Billing amounts don't match expectations
**Solutions**:
1. Review billing calculations
2. Check for manual overrides
3. Verify contract terms
4. Audit billing data

### System Performance Issues

#### Slow Performance
**Problem**: System is running slowly
**Solutions**:
1. Check system resources
2. Review database performance
3. Optimize queries
4. Check for system bottlenecks

#### Data Sync Issues
**Problem**: Data is not syncing between systems
**Solutions**:
1. Check integration status
2. Verify data mapping
3. Review sync schedules
4. Check for data conflicts

## Diagnostic Tools

### System Diagnostics
- **System Health**: Check system health status
- **Performance Metrics**: Review performance metrics
- **Error Logs**: Review system error logs
- **Resource Usage**: Monitor resource usage

### Data Validation
- **Data Integrity**: Check data integrity
- **Data Consistency**: Verify data consistency
- **Data Completeness**: Check data completeness
- **Data Accuracy**: Validate data accuracy

### Process Monitoring
- **Process Status**: Monitor process status
- **Process Performance**: Review process performance
- **Process Errors**: Check for process errors
- **Process Optimization**: Identify optimization opportunities

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

### Escalation Procedures
- **Level 1**: Basic support and troubleshooting
- **Level 2**: Advanced technical support
- **Level 3**: Expert consultation and development
- **Emergency**: Critical issue escalation
"""

    create_wiki_page("troubleshooting", "Troubleshooting Guide", content, "warehousing")


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
    create_additional_warehousing_guides()

