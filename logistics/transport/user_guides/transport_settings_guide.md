# Transport Settings User Guide

## Overview

**Transport Settings** is the central configuration hub for the Transport Module. It contains all system-wide settings, defaults, and integration configurations that control how the transportation system operates.

## Accessing Transport Settings

Navigate to **Transport > Transport Settings**

## General Settings

### **Transport Plan Settings**
- **Forward Days in Transport Plan**: Days to look forward for planning
- **Backward Days in Transport Plan**: Days to look backward for planning

## Telematics Integration

### **Telematics Provider Settings**
- **Default Telematics Provider**: Primary telematics service (from Telematics Provider)
- **Telematics Poll Interval (min)**: How often to poll for new data


## Routing Settings

### **Routing Provider**
- **Routing Provider**: Disabled, OSRM, Mapbox, Google
- **OSRM Base URL**: OSRM server URL (default: https://router.project-osrm.org)
- **Mapbox API Key**: Mapbox API key for routing
- **Google API Key**: Google API key for routing
- **Default Avg Speed (KPH)**: Default average speed (default: 40)

### **Routing Features**
- **Routing Auto Compute**: Automatically compute routes
- **Routing Show Map**: Show map in routing interface
- **Map Renderer**: OpenStreetMap, Google Maps, Mapbox, MapLibre
- **Routing Tiles URL**: Map tiles URL
- **Routing Tiles Attr**: Map tiles attribution
- **Routing Timeout (sec)**: Timeout for routing requests
- **Maps Enable External Links**: Enable external map links

## Carbon Management

### **Carbon Settings**
- **Carbon Autocompute**: Automatically compute carbon emissions
- **Carbon Default Factor (g/km)**: Default emission factor per km (default: 800)
- **Carbon Default Factor (g/Tkm)**: Default emission factor per ton-km (default: 62)

### **Carbon Provider**
- **Carbon Provider**: FACTOR_TABLE, CLIMATIQ, CARBON_INTERFACE, CUSTOM_WEBHOOK
- **Carbon Provider API Key**: API key for carbon provider
- **Carbon Provider URL**: URL for custom webhook provider

### **Emission Factors**
- **Emission Factors**: Table of transport emission factors for different vehicle types and conditions


## Best Practices

### **Configuration Management**
- **Regular Reviews**: Periodic settings review
- **Documentation**: Document all changes
- **Testing**: Test changes before deployment
- **Backup**: Backup configuration settings

### **Performance Optimization**
- **Monitor Performance**: Regular performance monitoring
- **Optimize Settings**: Optimize for performance
- **Resource Management**: Manage system resources
- **Scalability**: Plan for system growth

### **Security Management**
- **Regular Updates**: Keep settings current
- **Access Control**: Maintain proper access controls
- **Audit Trails**: Monitor system access
- **Compliance**: Ensure regulatory compliance

## Common Issues and Solutions

### **Issue: Settings Not Saving**
- **Solution**: Check user permissions and system status

### **Issue: Integration Not Working**
- **Solution**: Verify API credentials and endpoints

### **Issue: Performance Issues**
- **Solution**: Review and optimize settings

### **Issue: Access Denied**
- **Solution**: Check user permissions and roles


---

*This guide covers all aspects of Transport Settings configuration. For advanced features and customization options, refer to the system documentation.*
