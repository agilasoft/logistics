# Transport Job User Guide

## Overview

A **Transport Job** is the operational execution plan created from a Transport Order. It contains all the details needed to execute transportation services, including vehicle assignments, driver details, route legs, and operational requirements.

## Creating a Transport Job

### **From Transport Order**
1. Open a submitted **Transport Order**
2. Click **Create Transport Job**
3. System automatically creates job with:
   - All order details
   - Converted legs
   - Packages and charges
   - Customer information

### **Manual Creation**
Navigate to **Transport > Transport Job > New**

#### **Header Information**
- **Customer**: Customer for this job (required)
- **Transport Template**: Template used (required)
- **Transport Order**: Link to source order (if applicable)
- **Booking Date**: When job was created (required)
- **Customer Ref No**: Customer's reference number

#### **Service Details**
- **Transport Job Type**: Container, Non-Container, Special, Oversized, Multimodal, Heavy Haul
- **Vehicle Type**: Required vehicle type (required)
- **Hazardous**: Hazardous cargo indicator
- **Refrigeration**: Refrigeration required

#### **Container Details** (if Transport Job Type is Container)
- **Container Type**: Type of container (required for container jobs)
- **Container No**: Container number (required for container jobs)

#### **Entity Information**
- **Company**: Company for this job (required)
- **Branch**: Branch for this job (required)
- **Job Reference**: Job reference for financial transactions
- **Sales Invoice**: Generated sales invoice

## Transport Job Legs

### **Leg Management**
Transport jobs contain multiple legs representing route segments:

#### **Leg Details**
- **Transport Leg**: Link to Transport Leg document
- **Facility From/To**: Origin and destination facilities
- **Pick/Drop Mode**: Service delivery methods
- **Addresses**: Detailed location information
- **Scheduled Date**: When leg should be executed
- **Status**: Current leg status

#### **Leg Statuses**
- **Pending**: Not yet started
- **In Progress**: Currently being executed
- **Completed**: Successfully finished
- **Cancelled**: Leg cancelled

### **Adding Legs**
1. **From Template**: Use template legs
2. **Manual Entry**: Add legs manually
3. **Copy from Order**: Import from transport order

## Packages and Charges

### **Package Management**
- **Package Type**: Type of goods
- **Quantity**: Number of packages
- **Weight/Volume**: Physical dimensions
- **Description**: Package details
- **Special Requirements**: Handling instructions

### **Charge Management**
- **Charge Type**: Type of charge
- **Rate**: Charge per unit
- **Amount**: Total charge
- **Description**: Charge details
- **Tax Information**: Applicable taxes

## Run Sheet Creation

### **Creating Run Sheets**
1. Open the Transport Job
2. Click **Create Run Sheet**
3. Select vehicle and driver
4. System creates run sheet with job legs

### **Run Sheet Benefits**
- **Daily Planning**: Organize daily operations
- **Vehicle Assignment**: Assign vehicles to jobs
- **Driver Management**: Assign drivers to vehicles
- **Route Optimization**: Plan efficient routes

### **Run Sheet Process**
1. **Create**: Generate from transport job
2. **Plan**: Organize legs by sequence
3. **Dispatch**: Send to driver/vehicle
4. **Execute**: Track progress
5. **Complete**: Update status

## Status Management

### **Job Statuses**
- **Draft**: Job being created
- **Submitted**: Job approved and ready
- **In Progress**: Job being executed
- **Completed**: All legs completed
- **Cancelled**: Job cancelled

### **Status Workflow**
1. **Draft → Submitted**: Job approval
2. **Submitted → In Progress**: Execution starts
3. **In Progress → Completed**: All legs finished
4. **Any Status → Cancelled**: Job cancellation

## Sales Invoice Generation

### **Automatic Invoice Creation**
When all legs are completed:
1. Click **Create Sales Invoice**
2. System generates invoice with:
   - All completed legs
   - Calculated charges
   - Customer information
   - Tax details

### **Invoice Requirements**
- All legs must be completed
- Charges must be defined
- Customer must be valid
- No existing invoice for job

## Telematics Integration

### **Real-time Tracking**
- **Vehicle Position**: Live GPS tracking
- **Status Updates**: Automatic status changes
- **Event Monitoring**: Vehicle events
- **Performance Metrics**: Speed, fuel, etc.

### **Position Updates**
- **Automatic**: Via telematics devices
- **Manual**: Driver updates
- **Scheduled**: Regular updates
- **Event-based**: Status changes

## Best Practices

### **Job Planning**
- **Realistic Scheduling**: Set achievable timelines
- **Resource Allocation**: Ensure vehicle/driver availability
- **Route Optimization**: Plan efficient routes
- **Contingency Planning**: Prepare for delays

### **Execution Management**
- **Regular Updates**: Keep status current
- **Communication**: Maintain customer contact
- **Documentation**: Record all activities
- **Quality Control**: Monitor service delivery

### **Completion Process**
- **Verification**: Confirm all legs completed
- **Documentation**: Generate proof of delivery
- **Billing**: Create sales invoices
- **Analysis**: Review performance

## Common Issues and Solutions

### **Issue: Cannot Create Run Sheet**
- **Solution**: Ensure job is submitted and vehicle available

### **Issue: Leg Status Not Updating**
- **Solution**: Check telematics connection and manual updates

### **Issue: Sales Invoice Creation Fails**
- **Solution**: Verify all legs completed and charges defined

### **Issue: Vehicle Not Available**
- **Solution**: Check vehicle status and existing assignments

## Integration Points

### **Transport Order Integration**
- **Order Details**: Inherited from transport order
- **Status Sync**: Order status updates with job
- **Customer Info**: Customer details maintained

### **Run Sheet Integration**
- **Job Legs**: Legs transferred to run sheet
- **Vehicle Assignment**: Vehicle and driver details
- **Status Updates**: Real-time status synchronization

### **Accounting Integration**
- **Sales Invoices**: Automatic invoice generation
- **Revenue Recognition**: Revenue tracking
- **Cost Management**: Expense tracking

## Reporting and Analytics

### **Job Reports**
- **Job Status**: Current job status
- **Performance Metrics**: Delivery times, success rates
- **Revenue Analysis**: Job profitability
- **Customer Analysis**: Customer performance

### **Key Performance Indicators**
- **On-time Delivery**: Percentage of on-time deliveries
- **Job Completion Rate**: Success rate
- **Average Delivery Time**: Performance metrics
- **Customer Satisfaction**: Service quality

---

*This guide provides comprehensive information for managing Transport Jobs. For advanced features and customization options, refer to the system documentation.*
