# Capacity Exceed Warning Implementation

This document explains how the feature that indicates "requirements may exceed the typical capacity" was implemented in the Transport Job and Transport Order doctypes.

## Overview

The capacity exceed warning feature validates whether the total requirements (weight, volume, and pallets) from packages exceed the typical capacity of the selected vehicle type. This helps users identify potential capacity issues before assigning vehicles to transport jobs or orders.

## Implementation Differences

The feature is implemented differently in two doctypes:

1. **Transport Order**: Throws validation errors (blocking) when capacity is exceeded
2. **Transport Job**: Shows warnings (non-blocking) when capacity may be exceeded (with 10% buffer)

## Location

### Transport Job
- **File**: `logistics/transport/doctype/transport_job/transport_job.py`
- **Method**: `validate_vehicle_type_capacity()` (lines 901-947)
- **Called from**: `validate()` method (line 48)

### Transport Order
- **File**: `logistics/transport/doctype/transport_order/transport_order.py`
- **Method**: `validate_vehicle_type_capacity()` (lines 415-454)
- **Called from**: `validate()` method (line 89)

## Implementation Flow

### 1. Trigger Point

The validation is automatically triggered during the document's `validate()` method:

```python
def validate(self):
    # ... other validations ...
    self.validate_vehicle_type_capacity()
    # ... other validations ...
```

### 2. Prerequisites Check

The method first checks if a vehicle type is assigned:

```python
def validate_vehicle_type_capacity(self):
    """Validate vehicle type capacity when vehicle_type is assigned"""
    if not getattr(self, 'vehicle_type', None):
        return  # Exit early if no vehicle type
```

### 3. Calculate Requirements

The system calculates total capacity requirements from all packages in the document:

```python
# Calculate capacity requirements
requirements = self.calculate_capacity_requirements()
```

**Method**: `calculate_capacity_requirements()` (Transport Job: lines 829-899, Transport Order: lines 456-520)

**What it does:**
- Iterates through all packages in the `packages` child table
- Sums up:
  - **Weight**: Converts all package weights to standard UOM
  - **Volume**: Uses direct volume or calculates from dimensions (length × width × height)
  - **Pallets**: Sums up `no_of_packs` field
- Returns a dictionary:
  ```python
  {
      'weight': total_weight,
      'weight_uom': standard_weight_uom,
      'volume': total_volume,
      'volume_uom': standard_volume_uom,
      'pallets': total_pallets
  }
  ```

**Early Exit:**
```python
if requirements['weight'] == 0 and requirements['volume'] == 0 and requirements['pallets'] == 0:
    return  # No requirements to validate
```

### 4. Get Vehicle Type Capacity Information

The system retrieves aggregated capacity information for the vehicle type:

```python
# Get vehicle type capacity information
capacity_info = get_vehicle_type_capacity_info(self.vehicle_type, self.company)
```

**Function**: `get_vehicle_type_capacity_info()` in `logistics/transport/capacity/vehicle_type_capacity.py` (lines 18-101)

**What it does:**
- Queries all Transport Vehicles of the specified vehicle type
- Aggregates capacity data:
  - `max_weight`: Maximum weight capacity across all vehicles
  - `max_volume`: Maximum volume capacity across all vehicles
  - `max_pallets`: Maximum pallet capacity across all vehicles
  - `avg_weight`: Average weight capacity
  - `min_weight`: Minimum weight capacity
  - `vehicle_count`: Number of vehicles of this type
- Converts all capacities to standard UOMs
- Returns capacity statistics dictionary

### 5. Capacity Validation

#### Transport Job (Warning-based)

Transport Job uses a **10% buffer** and shows **non-blocking warnings**:

```python
# Check capacity with buffer
buffer = 10.0 / 100.0  # 10% buffer

if requirements['weight'] > 0:
    max_weight = capacity_info.get('max_weight', 0) * (1 - buffer)
    if requirements['weight'] > max_weight:
        frappe.msgprint(_("Warning: Required weight ({0} {1}) may exceed capacity for vehicle type {2}").format(
            requirements['weight'], requirements['weight_uom'], self.vehicle_type
        ), indicator='orange')

if requirements['volume'] > 0:
    max_volume = capacity_info.get('max_volume', 0) * (1 - buffer)
    if requirements['volume'] > max_volume:
        frappe.msgprint(_("Warning: Required volume ({0} {1}) may exceed capacity for vehicle type {2}").format(
            requirements['volume'], requirements['volume_uom'], self.vehicle_type
        ), indicator='orange')

if requirements['pallets'] > 0:
    max_pallets = capacity_info.get('max_pallets', 0) * (1 - buffer)
    if requirements['pallets'] > max_pallets:
        frappe.msgprint(_("Warning: Required pallets ({0}) may exceed capacity for vehicle type {1}").format(
            requirements['pallets'], self.vehicle_type
        ), indicator='orange')
```

**Key Characteristics:**
- **10% buffer**: Applies `(1 - buffer)` to maximum capacity, so warnings appear at 90% of max capacity
- **Non-blocking**: Uses `frappe.msgprint()` with orange indicator
- **Allows save**: Document can still be saved despite warnings
- **User-friendly**: Warns before actual capacity is exceeded

#### Transport Order (Error-based)

Transport Order uses **strict validation** and throws **blocking errors**:

```python
# Validate capacity
if requirements['weight'] > 0 and capacity_info.get('max_weight', 0) < requirements['weight']:
    frappe.throw(_("Total weight ({0} {1}) exceeds typical capacity for vehicle type {2}").format(
        requirements['weight'], requirements['weight_uom'], self.vehicle_type
    ))

if requirements['volume'] > 0 and capacity_info.get('max_volume', 0) < requirements['volume']:
    frappe.throw(_("Total volume ({0} {1}) exceeds typical capacity for vehicle type {2}").format(
        requirements['volume'], requirements['volume_uom'], self.vehicle_type
    ))

if requirements['pallets'] > 0 and capacity_info.get('max_pallets', 0) < requirements['pallets']:
    frappe.throw(_("Total pallets ({0}) exceeds typical capacity for vehicle type {1}").format(
        requirements['pallets'], self.vehicle_type
    ))
```

**Key Characteristics:**
- **No buffer**: Direct comparison against maximum capacity
- **Blocking**: Uses `frappe.throw()` which prevents document save
- **Strict enforcement**: Ensures Transport Orders cannot exceed capacity
- **Early prevention**: Catches issues at the booking stage

### 6. Error Handling

Both implementations include error handling:

```python
except ImportError:
    # Capacity management not fully implemented yet
    pass
except Exception as e:
    frappe.log_error(f"Error validating vehicle type capacity: {str(e)}", "Capacity Validation Error")
```

**ImportError**: Silently handles cases where capacity management modules are not available
**General Exception**: Logs errors for debugging without breaking the document save process

## Supporting Functions

### `calculate_capacity_requirements()`

**Location**: 
- Transport Job: `transport_job.py` lines 829-899
- Transport Order: `transport_order.py` lines 456-520

**Purpose**: Aggregates capacity requirements from all packages

**Process**:
1. Gets default UOMs for the company
2. Iterates through packages child table
3. For each package:
   - **Weight**: Converts to standard UOM using `convert_weight()`
   - **Volume**: Uses direct volume or calculates from dimensions using `calculate_volume_from_dimensions()`
   - **Pallets**: Sums `no_of_packs` field
4. Returns aggregated totals with UOMs

**UOM Conversion**:
- Uses `logistics.transport.capacity.uom_conversion` module
- Converts all values to company's default UOMs
- Handles different UOMs per package

### `get_vehicle_type_capacity_info()`

**Location**: `logistics/transport/capacity/vehicle_type_capacity.py` lines 18-101

**Purpose**: Aggregates capacity statistics for a vehicle type

**Process**:
1. Queries all Transport Vehicles with the specified vehicle type
2. Extracts capacity fields:
   - `capacity_weight`, `capacity_weight_uom`
   - `capacity_volume`, `capacity_volume_uom`
   - `capacity_pallets`
3. Converts all values to standard UOMs
4. Calculates statistics:
   - Maximum values (used for validation)
   - Average and minimum values (for reference)
5. Returns aggregated capacity information

**Returns**:
```python
{
    'max_weight': float,
    'max_volume': float,
    'max_pallets': float,
    'avg_weight': float,
    'min_weight': float,
    'vehicle_count': int,
    'weight_uom': str,
    'volume_uom': str
}
```

## Design Decisions

### Why Different Behavior in Transport Job vs Transport Order?

1. **Transport Order (Strict)**:
   - Represents customer booking/commitment
   - Should prevent impossible bookings
   - Catches issues early in the process
   - Ensures data integrity

2. **Transport Job (Warning)**:
   - Represents operational execution
   - May need flexibility for edge cases
   - 10% buffer accounts for real-world variations
   - Allows experienced users to proceed with caution

### Why 10% Buffer in Transport Job?

- Accounts for measurement variations
- Allows for slight over-capacity in exceptional cases
- Provides early warning without being too restrictive
- Balances safety with operational flexibility

### Why Check All Three Dimensions?

- **Weight**: Critical for vehicle safety and legal compliance
- **Volume**: Important for space utilization
- **Pallets**: Relevant for loading/unloading operations

All three dimensions are independent and must be checked separately.

## User Experience

### Transport Order

When capacity is exceeded:
- **Error message** appears preventing save
- User must either:
  - Change vehicle type
  - Reduce package quantities
  - Split into multiple orders

**Example Error**:
```
Total weight (5000 kg) exceeds typical capacity for vehicle type Small Truck
```

### Transport Job

When capacity may be exceeded:
- **Warning message** appears (orange indicator)
- Document can still be saved
- User can proceed with caution
- Warning appears in message area

**Example Warning**:
```
Warning: Required weight (4500 kg) may exceed capacity for vehicle type Small Truck
```

## Dependencies

### Required Modules

1. **Capacity Management**:
   - `logistics.transport.capacity.vehicle_type_capacity`
   - `logistics.transport.capacity.uom_conversion`

2. **Doctypes**:
   - Transport Vehicle (for capacity data)
   - Vehicle Type (for grouping vehicles)
   - Transport Job / Transport Order (implementing doctypes)

### Required Data

1. **Transport Vehicles** must have:
   - `vehicle_type` field set
   - `capacity_weight` and `capacity_weight_uom`
   - `capacity_volume` and `capacity_volume_uom`
   - `capacity_pallets`

2. **Packages** must have:
   - Weight or volume information
   - Appropriate UOM fields

## Testing Considerations

### Test Cases

1. **No Vehicle Type**:
   - Should skip validation
   - Should not raise errors

2. **No Requirements**:
   - Empty packages or zero values
   - Should skip validation

3. **Within Capacity**:
   - Requirements below maximum
   - Should pass without warnings/errors

4. **Exceeds Capacity (Transport Order)**:
   - Should throw error
   - Should prevent save

5. **Exceeds Capacity with Buffer (Transport Job)**:
   - Requirements > 90% of max capacity
   - Should show warning
   - Should allow save

6. **Multiple Dimensions**:
   - Test weight, volume, and pallets separately
   - Test combinations

7. **UOM Conversion**:
   - Packages with different UOMs
   - Should convert correctly

8. **Missing Capacity Data**:
   - Vehicle type with no vehicles
   - Should handle gracefully

## Related Features

### Vehicle Capacity Validation

Similar validation exists for individual vehicles:
- `validate_capacity()` in Transport Job (line 948)
- Validates against specific vehicle capacity (not vehicle type)

### Capacity Manager

The `CapacityManager` class provides more advanced capacity checking:
- Real-time capacity availability
- Reservation management
- Buffer calculations
- Used in Run Sheet assignments

## Future Enhancements

Potential improvements:

1. **Configurable Buffer**: Make 10% buffer configurable per company
2. **Warning Thresholds**: Different thresholds for warning vs error
3. **Capacity Suggestions**: Suggest alternative vehicle types
4. **Historical Data**: Consider historical over-capacity success rates
5. **Multi-Vehicle Options**: Suggest splitting across multiple vehicles
6. **Visual Indicators**: Show capacity utilization in UI
7. **Batch Validation**: Validate multiple documents at once

## Code References

### Transport Job
- `validate_vehicle_type_capacity()`: Lines 901-947
- `calculate_capacity_requirements()`: Lines 829-899
- Called from `validate()`: Line 48

### Transport Order
- `validate_vehicle_type_capacity()`: Lines 415-454
- `calculate_capacity_requirements()`: Lines 456-520
- Called from `validate()`: Line 89

### Supporting Modules
- `vehicle_type_capacity.py`: Lines 18-101 (`get_vehicle_type_capacity_info`)
- `uom_conversion.py`: UOM conversion utilities
