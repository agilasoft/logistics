# Transport Vehicle User Guide

## Overview

**Transport Vehicles** are the core assets in the transportation system. They represent the fleet of vehicles used for transportation services, including trucks, vans, cars, and specialized vehicles. Each vehicle can be equipped with telematics devices for real-time tracking and monitoring.

## Creating a Transport Vehicle

### **Basic Information**

Navigate to **Transport > Transport Vehicle > New**

#### **Vehicle Details**
- **Code**: Unique vehicle code (required, auto-generated)
- **Vehicle Name**: Name of the vehicle (required)
- **Vehicle Type**: Category of vehicle (required)
- **Make**: Vehicle manufacturer (from Vehicle Make)
- **Model**: Vehicle model
- **Company Owned**: Whether vehicle is company owned

#### **Transport Company** (if not company owned)
- **Transport Company**: External transport company

#### **Capacity Information**
- **Capacity Weight**: Maximum weight capacity
- **Capacity Volume**: Maximum volume capacity
- **Capacity Pallets**: Maximum pallet capacity
- **Can Carry Container**: Whether vehicle can carry containers
- **Max Container Count**: Maximum number of containers
- **Container Types**: Supported container types
- **Reefer**: Whether vehicle has refrigeration
- **Minimum Temp**: Minimum temperature (if reefer)
- **Maximum Temp**: Maximum temperature (if reefer)

## Telematics Integration

### **Telematics Setup**
- **Telematics Provider**: Select telematics service provider
- **Telematics External ID**: Device ID from telematics provider

### **Position Tracking**
- **Last Telematics TS**: Latest position timestamp
- **Last Telematics Lat**: Latest latitude
- **Last Telematics Lon**: Latest longitude
- **Last Speed (kph)**: Current speed in km/h
- **Last Ignition On**: Engine on/off status
- **Last Odometer (km)**: Current odometer reading
- **Last Provider**: Provider that provided last data

### **Real-time Features**
- **Live Tracking**: Real-time position updates
- **Route History**: Historical route data
- **Event Monitoring**: Vehicle events and alerts
- **Performance Metrics**: Speed, fuel, maintenance

## Vehicle Management

### **Status Management**
- **Active**: Vehicle available for assignment
- **Inactive**: Vehicle not available
- **Under Maintenance**: Vehicle being serviced
- **Retired**: Vehicle no longer in service

### **Assignment Management**
- **Current Job**: Currently assigned transport job
- **Current Driver**: Assigned driver
- **Current Location**: Last known location
- **Next Assignment**: Upcoming assignments

## Vehicle Types and Categories

### **Standard Types**
- **Truck**: Heavy goods vehicles
- **Van**: Light commercial vehicles
- **Car**: Passenger vehicles
- **Motorcycle**: Two-wheeled vehicles
- **Specialized**: Custom vehicles

### **Capacity Categories**
- **Light**: Small capacity vehicles
- **Medium**: Medium capacity vehicles
- **Heavy**: Large capacity vehicles
- **Specialized**: Custom capacity vehicles

## Permits and Compliance

### **Vehicle Permits**
- **Permit Type**: Type of permit required
- **Permit Number**: Official permit number
- **Issue Date**: When permit was issued
- **Expiry Date**: Permit expiry date
- **Issuing Authority**: Authority that issued permit

### **Compliance Tracking**
- **Safety Inspections**: Regular safety checks
- **Emission Tests**: Environmental compliance
- **Insurance**: Coverage requirements
- **Licensing**: Driver licensing requirements

## Zones and Operations

### **Operational Zones**
- **Zone Assignment**: Geographic areas of operation
- **Zone Types**: Urban, Rural, Interstate
- **Restrictions**: Operational limitations
- **Permissions**: Special permissions

### **Route Planning**
- **Preferred Routes**: Standard route preferences
- **Restricted Areas**: Areas to avoid
- **Time Windows**: Operating hours
- **Distance Limits**: Maximum distance per trip

## Maintenance and Service

### **Maintenance Records**
- **Service History**: Previous maintenance
- **Next Service**: Upcoming maintenance
- **Service Provider**: Maintenance company
- **Cost Tracking**: Maintenance costs

### **Service Scheduling**
- **Regular Service**: Scheduled maintenance
- **Emergency Service**: Unscheduled repairs
- **Parts Replacement**: Component changes
- **Warranty Tracking**: Warranty information

## Driver Assignment

### **Driver Management**
- **Current Driver**: Assigned driver
- **Driver History**: Previous drivers
- **Driver Qualifications**: Required qualifications
- **Training Records**: Driver training

### **Assignment Rules**
- **Driver-Vehicle Compatibility**: Matching requirements
- **License Requirements**: Required licenses
- **Experience Level**: Required experience
- **Availability**: Driver availability

## Telematics Features

### **Position Tracking**
- **GPS Coordinates**: Latitude and longitude
- **Heading**: Direction of travel
- **Speed**: Current speed
- **Altitude**: Elevation information

### **Vehicle Events**
- **Ignition On/Off**: Engine status
- **Door Open/Close**: Door status
- **Panic Button**: Emergency alerts
- **Geofence**: Zone entry/exit

### **Performance Monitoring**
- **Fuel Consumption**: Fuel usage tracking
- **Idle Time**: Engine idle duration
- **Harsh Braking**: Aggressive driving detection
- **Speed Violations**: Speed limit violations

## Best Practices

### **Vehicle Setup**
- **Complete Information**: Fill all required fields
- **Accurate Specifications**: Correct capacity and dimensions
- **Regular Updates**: Keep information current
- **Documentation**: Maintain all records

### **Telematics Management**
- **Device Maintenance**: Regular device checks
- **Data Quality**: Ensure accurate data
- **Privacy Compliance**: Follow privacy regulations
- **Security**: Protect tracking data

### **Maintenance Planning**
- **Scheduled Service**: Regular maintenance
- **Preventive Care**: Proactive maintenance
- **Cost Management**: Track maintenance costs
- **Performance Monitoring**: Monitor vehicle performance

## Common Issues and Solutions

### **Issue: Telematics Not Working**
- **Solution**: Check device connection and provider settings

### **Issue: Position Not Updating**
- **Solution**: Verify device status and network connection

### **Issue: Vehicle Not Available**
- **Solution**: Check vehicle status and current assignments

### **Issue: Driver Assignment Failed**
- **Solution**: Verify driver qualifications and availability

## Integration Points

### **Transport Job Integration**
- **Job Assignment**: Vehicle assigned to jobs
- **Status Updates**: Real-time status updates
- **Route Tracking**: Job route monitoring

### **Run Sheet Integration**
- **Daily Planning**: Vehicle scheduling
- **Driver Assignment**: Driver-vehicle pairing
- **Route Optimization**: Efficient route planning

### **Maintenance Integration**
- **Service Scheduling**: Maintenance planning
- **Cost Tracking**: Maintenance cost management
- **Performance Analysis**: Vehicle performance metrics

## Reporting and Analytics

### **Vehicle Reports**
- **Fleet Status**: Current fleet status
- **Utilization**: Vehicle utilization rates
- **Performance**: Vehicle performance metrics
- **Cost Analysis**: Operating cost analysis

### **Key Metrics**
- **Fleet Utilization**: Percentage of vehicles in use
- **Average Speed**: Fleet speed performance
- **Fuel Efficiency**: Fuel consumption metrics
- **Maintenance Costs**: Cost per vehicle

---

*This guide covers all aspects of Transport Vehicle management. For advanced features and customization options, refer to the system documentation.*
