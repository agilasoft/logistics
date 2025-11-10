# Air Freight Settings

## Overview

Air Freight Settings is a configuration document that stores company-specific settings and defaults for the Air Freight module. This document is used to configure default values, business rules, calculation methods, alert settings, and integration options for air freight operations.

## Purpose

The Air Freight Settings document is used to:
- Configure company-specific defaults for air freight operations
- Set up default accounting dimensions (branch, cost center, profit center)
- Configure default locations (airports, ports)
- Set up business rules and automation options
- Configure calculation methods and chargeable weight factors
- Enable alerts and notifications
- Configure integration settings
- Set up document generation and consolidation rules
- Configure billing automation

## Access

Navigate to **Air Freight > Setup > Air Freight Settings**

**Note**: Air Freight Settings is company-specific. Each company can have its own settings document.

## Document Structure

The Air Freight Settings document contains the following sections:

### General Settings

Company and accounting defaults:

- **Company**: Company for these settings (required, unique)
- **Default Branch**: Default branch for air freight operations
- **Default Cost Center**: Default cost center for cost tracking
- **Default Profit Center**: Default profit center for profitability analysis
- **Default Currency**: Default currency for air freight operations
- **Default Incoterm**: Default Incoterm (EXW, FCA, CPT, CIP, DAP, DPU, DDP, FAS, FOB, CFR, CIF)
- **Default Service Level**: Default service level (Standard, Express, Economy, Premium)

### Location Settings

Default location settings:

- **Default Origin Airport**: Default origin airport for shipments
- **Default Destination Airport**: Default destination airport for shipments
- **Default Origin Port**: Default origin port (UNLOCO code)
- **Default Destination Port**: Default destination port (UNLOCO code)

### Business Settings

Business rules and defaults:

- **Default Airline**: Default airline for shipments
- **Default Freight Agent**: Default freight agent (user)
- **Allow Creation of Sales Order**: Checkbox to allow creation of sales orders from air shipments
- **Auto-create Job Costing Number**: Checkbox to automatically create job costing numbers (default: enabled)
- **Enable Milestone Tracking**: Checkbox to enable milestone tracking (default: enabled)
- **Default House Type**: Default house type (Direct, Consolidation, Break-Bulk)
- **Default Direction**: Default direction (Import, Export, Domestic)
- **Default Release Type**: Default release type (Prepaid, Collect, Third Party)
- **Default Entry Type**: Default entry type (Direct, Transit, Break-Bulk)

### Calculation Settings

Calculation methods and factors:

- **Volume to Weight Factor (kg/m³)**: Factor to convert volume to weight (default: 167 kg/m³ - IATA standard)
  - IATA standard: 167 kg/m³ (6 m³/1000 kg)
  - Used for chargeable weight calculation
- **Chargeable Weight Calculation**: Method for calculating chargeable weight
  - Actual Weight
  - Volume Weight
  - Higher of Both (default)
- **Default Charge Basis**: Default charge basis
  - Per kg
  - Per m³
  - Per package
  - Per shipment
  - Fixed amount

### Alert Settings

Alert and notification configuration:

- **Enable Delay Alerts**: Checkbox to enable delay alerts (default: enabled)
- **Enable ETA Alerts**: Checkbox to enable ETA alerts (default: enabled)
- **Alert Check Interval (Hours)**: Interval for checking alerts (default: 1 hour)
- **Enable Dangerous Goods Compliance Alerts**: Checkbox to enable DG compliance alerts (default: enabled)

### Integration Settings

Integration and tracking options:

- **Enable Flight Tracking**: Checkbox to enable flight tracking
- **Enable IATA Integration**: Checkbox to enable IATA integration
- **Enable Customs Clearance Tracking**: Checkbox to enable customs clearance tracking
- **Enable Real-time Tracking**: Checkbox to enable real-time tracking

### Document Settings

Document generation and requirements:

- **Auto-generate House AWB Number**: Checkbox to automatically generate House AWB numbers
- **Auto-generate Master AWB Number**: Checkbox to automatically generate Master AWB numbers
- **Require Dangerous Goods Declaration**: Checkbox to require DG declaration for shipments
- **Require Customs Declaration**: Checkbox to require customs declaration for shipments
- **Default ULD Type**: Default Unit Load Device type

### Consolidation Settings

Consolidation rules and limits:

- **Default Consolidation Type**: Default consolidation type
  - Direct Consolidation
  - Transit Consolidation
  - Break-Bulk Consolidation
  - Multi-Country Consolidation
- **Auto-assign to Consolidation**: Checkbox to automatically assign shipments to consolidations
- **Max Consolidation Weight (kg)**: Maximum weight for automatic consolidation assignment
- **Max Consolidation Volume (m³)**: Maximum volume for automatic consolidation assignment

### Billing Settings

Billing automation and configuration:

- **Enable Auto Billing**: Checkbox to enable automatic billing
- **Default Billing Currency**: Default currency for billing
- **Billing Check Interval (Hours)**: Interval for checking billing status (default: 24 hours)
- **Enable Billing Alerts**: Checkbox to enable billing alerts (default: enabled)

## Creating Air Freight Settings

### Step 1: Access Settings

1. Navigate to **Air Freight > Setup > Air Freight Settings**
2. If settings don't exist for your company, click **New**
3. Select **Company** (required)

### Step 2: General Settings

1. Select **Default Branch** if applicable
2. Select **Default Cost Center** if applicable
3. Select **Default Profit Center** if applicable
4. Select **Default Currency**
5. Select **Default Incoterm** if applicable
6. Select **Default Service Level** if applicable

### Step 3: Location Settings

1. Select **Default Origin Airport** if applicable
2. Select **Default Destination Airport** if applicable
3. Select **Default Origin Port** (UNLOCO code) if applicable
4. Select **Default Destination Port** (UNLOCO code) if applicable

### Step 4: Business Settings

1. Select **Default Airline** if applicable
2. Select **Default Freight Agent** if applicable
3. Check **Allow Creation of Sales Order** if applicable
4. Check **Auto-create Job Costing Number** (recommended: enabled)
5. Check **Enable Milestone Tracking** (recommended: enabled)
6. Select **Default House Type** if applicable
7. Select **Default Direction** if applicable
8. Select **Default Release Type** if applicable
9. Select **Default Entry Type** if applicable

### Step 5: Calculation Settings

1. Enter **Volume to Weight Factor** (default: 167 kg/m³ - IATA standard)
2. Select **Chargeable Weight Calculation** method (default: Higher of Both)
3. Select **Default Charge Basis** if applicable

### Step 6: Alert Settings

1. Check **Enable Delay Alerts** (recommended: enabled)
2. Check **Enable ETA Alerts** (recommended: enabled)
3. Enter **Alert Check Interval (Hours)** (default: 1 hour)
4. Check **Enable Dangerous Goods Compliance Alerts** (recommended: enabled)

### Step 7: Integration Settings

1. Check **Enable Flight Tracking** if using flight tracking
2. Check **Enable IATA Integration** if using IATA integration
3. Check **Enable Customs Clearance Tracking** if applicable
4. Check **Enable Real-time Tracking** if applicable

### Step 8: Document Settings

1. Check **Auto-generate House AWB Number** if applicable
2. Check **Auto-generate Master AWB Number** if applicable
3. Check **Require Dangerous Goods Declaration** if applicable
4. Check **Require Customs Declaration** if applicable
5. Select **Default ULD Type** if applicable

### Step 9: Consolidation Settings

1. Select **Default Consolidation Type** if applicable
2. Check **Auto-assign to Consolidation** if applicable
3. Enter **Max Consolidation Weight (kg)** if using auto-assignment
4. Enter **Max Consolidation Volume (m³)** if using auto-assignment

### Step 10: Billing Settings

1. Check **Enable Auto Billing** if applicable
2. Select **Default Billing Currency** if applicable
3. Enter **Billing Check Interval (Hours)** (default: 24 hours)
4. Check **Enable Billing Alerts** (recommended: enabled)

### Step 11: Save

1. Review all settings
2. Click **Save**

## Key Settings Explained

### Company-Specific Settings

Air Freight Settings is company-specific. Each company can have its own settings document. The company field is required and unique, ensuring one settings document per company.

### Volume to Weight Factor

The volume to weight factor is used to convert volume (cubic meters) to weight (kilograms) for chargeable weight calculation:

- **IATA Standard**: 167 kg/m³ (6 m³/1000 kg)
- This means 1 cubic meter = 167 kilograms
- Used when calculating chargeable weight based on volume

### Chargeable Weight Calculation

Determines how chargeable weight is calculated:

- **Actual Weight**: Use actual weight only
- **Volume Weight**: Use volume weight only (volume × volume to weight factor)
- **Higher of Both**: Use the higher of actual weight or volume weight (IATA standard)

### Auto-create Job Costing

When enabled, the system automatically creates a Job Costing Number when a new Air Shipment is created. This enables cost tracking by shipment.

### Milestone Tracking

When enabled, the system tracks shipment milestones and provides visual milestone dashboards. This helps monitor on-time performance and identify delays.

### Auto-assign to Consolidation

When enabled, the system automatically assigns shipments to consolidations based on:
- Consolidation type
- Weight limits (Max Consolidation Weight)
- Volume limits (Max Consolidation Volume)
- Route compatibility

### Alert Settings

Alerts help monitor shipments and identify issues:

- **Delay Alerts**: Notify when shipments are delayed
- **ETA Alerts**: Notify when ETAs are approaching or missed
- **DG Compliance Alerts**: Notify when DG declarations are incomplete or non-compliant

### Integration Settings

Integration settings enable external system connections:

- **Flight Tracking**: Enable flight schedule and tracking integration
- **IATA Integration**: Enable IATA message processing and status updates
- **Customs Clearance Tracking**: Enable customs clearance status tracking
- **Real-time Tracking**: Enable real-time flight and shipment tracking

## Best Practices

1. **Company-Specific**: Configure settings for each company separately
2. **Default Values**: Set defaults that match your most common operations
3. **IATA Standards**: Use IATA standard volume to weight factor (167 kg/m³)
4. **Chargeable Weight**: Use "Higher of Both" for IATA compliance
5. **Automation**: Enable automation features (auto-create job costing, milestone tracking) for efficiency
6. **Alerts**: Enable alerts for better visibility and issue detection
7. **Regular Review**: Review and update settings periodically
8. **Documentation**: Document any custom configurations

## Settings Impact

Settings affect:

- **New Documents**: Default values in new Air Shipment documents
- **Calculations**: Chargeable weight and rate calculations
- **Automation**: Automatic job costing creation, consolidation assignment
- **Alerts**: Alert generation and notifications
- **Integration**: External system connections and data synchronization
- **Workflow**: Business rules and document requirements

## Validation

The system validates settings:

- **Company**: Must be set (required)
- **Volume to Weight Factor**: Must be greater than 0
- **Max Consolidation Weight**: Must be greater than 0 (if set)
- **Max Consolidation Volume**: Must be greater than 0 (if set)
- **Alert Check Interval**: Must be greater than 0 (if set)
- **Billing Check Interval**: Must be greater than 0 (if set)

## Related Documents

- **Air Shipment**: Uses default values from settings
- **Air Consolidation**: Uses consolidation settings
- **Master Air Waybill**: Uses document generation settings
- **IATA Settings**: Works with IATA integration settings
- **Flight Schedule Settings**: Works with flight tracking settings

## Next Steps

- Review [Setup Guide](setup.md) for initial configuration
- Learn about [IATA Settings](iata-settings.md) for IATA integration
- Understand [Flight Schedule Settings](flight-schedule-settings.md) for flight tracking
- Learn about [Air Shipment](air-shipment.md) management

---

*For detailed setup instructions, refer to the [Setup Guide](setup.md).*

