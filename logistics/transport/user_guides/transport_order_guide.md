# Transport Order User Guide

## Overview

A **Transport Order** is a customer request for transportation services. It serves as the initial document that captures customer requirements and serves as the foundation for creating operational transport jobs.

## Creating a Transport Order

### 1. **Basic Information**

Navigate to **Transport > Transport Order > New**

#### **Header Fields**
- **Customer**: Select the customer requesting transport (required)
- **Transport Template**: Choose a predefined template (optional)
- **Booking Date**: Date when the order was placed
- **Scheduled Date**: When transport should be executed
- **Customer Ref No**: Customer's internal reference number
- **Vehicle Type**: Specific vehicle requirements

#### **Service Requirements**
- **Hazardous**: Check if cargo is hazardous (default: unchecked)
- **Refrigeration**: Check if refrigeration is required (default: unchecked)

### 2. **Packages Section**

Add packages being transported:

| Field | Description | Example |
|-------|-------------|---------|
| **Package Type** | Type of package | Box, Pallet, Container |
| **Quantity** | Number of packages | 5 |
| **Weight** | Total weight | 100 kg |
| **Volume** | Package volume | 2.5 m³ |
| **Description** | Package details | Electronics, Fragile |

### 3. **Charges Section**

Define transportation charges:

| Field | Description | Example |
|-------|-------------|---------|
| **Charge Type** | Type of charge | Base Rate, Fuel Surcharge |
| **Rate** | Charge amount | 150.00 |
| **Amount** | Calculated total | 750.00 |
| **Description** | Charge details | Per km rate |

### 4. **Legs Section**

Define transportation legs (route segments):

#### **From Location**
- **Facility Type From**: Type of origin facility (Shipper, Consignee, Container Yard, etc.)
- **Facility From**: Specific origin location (dynamic link based on facility type)
- **Pick Mode**: How goods are picked up (from Pick and Drop Mode)
- **Pick Address**: Detailed pickup address (from Address)

#### **To Location**
- **Facility Type To**: Type of destination facility (Shipper, Consignee, Container Yard, etc.)
- **Facility To**: Specific destination location (dynamic link based on facility type)
- **Drop Mode**: How goods are delivered (from Pick and Drop Mode)
- **Drop Address**: Detailed delivery address (from Address)

#### **Scheduling**
- **Scheduled Date**: When this leg should be executed

## Using Transport Templates

### **Template Selection**
1. Choose a **Transport Template** from the dropdown
2. Click **Get Leg Plan** to populate legs automatically
3. Review and modify generated legs as needed

### **Template Benefits**
- **Consistency**: Standardized route planning
- **Efficiency**: Faster order creation
- **Accuracy**: Pre-validated routes and operations
- **Compliance**: Built-in regulatory requirements

## Converting to Transport Job

### **Prerequisites**
- Transport Order must be **Submitted**
- All required fields must be completed
- Legs must be properly defined

### **Conversion Process**
1. Open the submitted Transport Order
2. Click **Create Transport Job**
3. System creates a new Transport Job with:
   - All order details copied
   - Legs converted to Transport Legs
   - Packages and charges transferred

### **Post-Conversion**
- Transport Order shows link to created job
- Transport Job is ready for execution
- Run Sheets can be created from the job

## Status Management

### **Order Statuses**
- **Draft**: Order being created
- **Submitted**: Order approved and ready
- **Completed**: All transport jobs completed
- **Cancelled**: Order cancelled

### **Status Transitions**
1. **Draft → Submitted**: Order approval
2. **Submitted → Completed**: All jobs finished
3. **Any Status → Cancelled**: Order cancellation

## Best Practices

### **Order Creation**
- **Complete Information**: Fill all required fields
- **Accurate Addresses**: Use detailed, verified addresses
- **Proper Scheduling**: Set realistic dates and times
- **Clear Requirements**: Specify special needs

### **Template Usage**
- **Standard Routes**: Use templates for common routes
- **Custom Modifications**: Adjust template legs as needed
- **Regular Updates**: Keep templates current

### **Documentation**
- **Customer References**: Always include customer ref numbers
- **Special Instructions**: Note any special requirements
- **Communication**: Maintain clear customer communication

## Common Issues and Solutions

### **Issue: Cannot Create Transport Job**
- **Solution**: Ensure order is submitted and all fields completed

### **Issue: Template Not Working**
- **Solution**: Verify template has legs defined and is active

### **Issue: Address Validation Errors**
- **Solution**: Use complete, standardized addresses

### **Issue: Scheduling Conflicts**
- **Solution**: Check vehicle availability and driver schedules

## Integration Points

### **Sales Integration**
- Links to Sales Orders
- Customer information sync
- Pricing integration

### **Transport Job Integration**
- Automatic job creation
- Leg and operation transfer
- Status synchronization

### **Accounting Integration**
- Charge calculation
- Revenue recognition
- Cost tracking

## Reporting and Analytics

### **Order Reports**
- Order status tracking
- Customer analysis
- Route performance
- Revenue reports

### **Key Metrics**
- Order completion rate
- Average delivery time
- Customer satisfaction
- Route efficiency

---

*This guide covers the essential aspects of Transport Order management. For advanced features and customization, refer to the system documentation.*
