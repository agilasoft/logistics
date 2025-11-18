# Location Overflow Implementation Summary

## Overview
Implemented location overflow functionality that allows handling units to be split across multiple storage locations when capacity is exceeded. This feature is controlled by warehouse settings and uses a `storage_location_size` field on Handling Units to determine how many locations a HU will occupy.

## Changes Made

### 1. Warehouse Settings (`warehouse_settings.json`)
**Added Field**: `enable_location_overflow`
- **Type**: Check (Boolean)
- **Default**: 0 (disabled)
- **Location**: Capacity Management section
- **Description**: When enabled, allows handling units to be split across multiple storage locations based on the 'Storage Location Size' field in the Handling Unit.

### 2. Handling Unit (`handling_unit.json`)
**Added Field**: `storage_location_size`
- **Type**: Int
- **Default**: 1
- **Location**: Capacity Management tab
- **Description**: Number of storage locations this handling unit will occupy. When location overflow is enabled, the system will split the handling unit's quantity, volume, and dimensions across this many locations.

### 3. Putaway Allocation Logic (`putaway.py`)

#### New Helper Functions

**`_get_location_overflow_enabled(company)`**
- Checks if location overflow is enabled in warehouse settings for a company
- Returns `False` if company is not provided or settings don't exist

**`_get_hu_storage_location_size(handling_unit)`**
- Gets the `storage_location_size` field from a handling unit
- Returns 1 (default) if not set or handling unit doesn't exist

**`_select_multiple_destinations_for_hu(...)`**
- Selects multiple destination locations for a handling unit
- Parameters include item, quantity, company, branch, staging area, level limit, used locations, exclude locations, handling unit, and number of locations needed
- Returns a list of location names (may be fewer than requested if not enough available)
- Uses priority filtering and capacity validation

#### Modified Allocation Flow

**Location Selection** (Lines 1951-2007):
- Checks if location overflow is enabled and gets HU storage location size
- If enabled and size > 1: Uses `_select_multiple_destinations_for_hu()` to get multiple locations
- Otherwise: Uses original single location selection (`_select_dest_for_hu_with_capacity_validation()`)

**Item Creation** (Lines 2120-2292):
- When multiple locations are selected:
  - Calculates split values: `qty_per_location`, `volume_per_location`, `weight_per_location`, `length_per_location`, `width_per_location`, `height_per_location`
  - Creates one job item per location
  - Last location gets remainder quantity to avoid rounding issues
  - Each item gets proportional split of volume, weight, and dimensions
  - Adds location overflow notes indicating split across multiple locations

## How It Works

### Example Scenario
1. **Setup**:
   - Warehouse Settings: `enable_location_overflow` = 1 (enabled)
   - Handling Unit "HU-001": `storage_location_size` = 3
   - Order: 100 units, volume = 30 m³, weight = 500 kg

2. **Allocation**:
   - System detects location overflow is enabled
   - Gets `storage_location_size` = 3 from HU
   - Selects 3 storage locations (e.g., "LOC-A", "LOC-B", "LOC-C")
   - Splits allocation:
     - LOC-A: 33.33 units, 10 m³, 166.67 kg
     - LOC-B: 33.33 units, 10 m³, 166.67 kg
     - LOC-C: 33.34 units, 10 m³, 166.66 kg (gets remainder)

3. **Result**:
   - Creates 3 job items (one per location)
   - Each item has the same handling unit but different location
   - Quantity, volume, and dimensions are proportionally split
   - Allocation notes indicate the split

## Key Features

### ✅ Proportional Splitting
- Quantity: Split evenly across locations (last location gets remainder)
- Volume: Split proportionally
- Weight: Split proportionally
- Dimensions (length, width, height): Split proportionally
- Signed quantities (for VAS): Split proportionally

### ✅ Location Selection
- Uses same priority hierarchy as single location selection
- Respects capacity validation
- Honors allocation level limits
- Filters out used locations
- Falls back to single location if not enough locations available

### ✅ Backward Compatibility
- Default behavior unchanged (single location) when:
  - Location overflow is disabled
  - `storage_location_size` = 1 or not set
- Existing functionality preserved

### ✅ Allocation Notes
- Single location: Standard location allocation note
- Multiple locations: Location overflow note with:
  - Total number of locations
  - Current location index
  - Quantity split information

## Testing Recommendations

1. **Basic Test**:
   - Enable location overflow in warehouse settings
   - Set a handling unit's `storage_location_size` = 2
   - Create putaway job with items
   - Verify items are split across 2 locations

2. **Edge Cases**:
   - Test with `storage_location_size` = 1 (should use single location)
   - Test with location overflow disabled (should use single location)
   - Test when not enough locations available (should use fewer locations)
   - Test with very large quantities to verify rounding

3. **Validation**:
   - Verify total quantity equals sum of split quantities
   - Verify total volume equals sum of split volumes
   - Verify total weight equals sum of split weights
   - Check allocation notes are correct

## Files Modified

1. `/logistics/warehousing/doctype/warehouse_settings/warehouse_settings.json`
   - Added `enable_location_overflow` field

2. `/logistics/warehousing/doctype/handling_unit/handling_unit.json`
   - Added `storage_location_size` field

3. `/logistics/warehousing/api_parts/putaway.py`
   - Added helper functions for location overflow
   - Modified `_hu_anchored_putaway_from_orders()` to handle multiple locations
   - Updated item creation logic to split across locations

## Next Steps

1. **Review Changes**: Review the implementation before taking effect
2. **Test**: Test with various scenarios to ensure correctness
3. **Deploy**: After approval, deploy changes
4. **Configure**: Enable location overflow in warehouse settings and set `storage_location_size` on handling units as needed

## Notes

- The implementation maintains backward compatibility
- Location overflow only applies when both conditions are met:
  1. `enable_location_overflow` is enabled in warehouse settings
  2. Handling unit has `storage_location_size` > 1
- If not enough locations are available, the system will use as many as possible
- Rounding is handled carefully to ensure totals match (last location gets remainder)

