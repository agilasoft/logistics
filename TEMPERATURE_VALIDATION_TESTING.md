# Temperature Validation Testing Guide

This guide explains how to test the global temperature validation implementation in each module.

## Prerequisites

1. **Configure Global Temperature Limits**
   - Go to **Logistics Settings** (`/app/logistics-settings`)
   - Navigate to the **Temperature Validation** tab
   - Set **Minimum Temperature (°C)**: e.g., `-50`
   - Set **Maximum Temperature (°C)**: e.g., `50`
   - Save the document

## Testing Scenarios

### Test Case 1: Valid Temperature Range
- **Min Temperature**: `-20`
- **Max Temperature**: `20`
- **Expected**: Should save successfully

### Test Case 2: Temperature Below Global Minimum
- **Min Temperature**: `-60` (below -50)
- **Max Temperature**: `20`
- **Expected**: Should show error: "Temperature for Minimum Temperature (-60°C) is below the minimum allowed temperature (-50°C)."

### Test Case 3: Temperature Above Global Maximum
- **Min Temperature**: `-20`
- **Max Temperature**: `60` (above 50)
- **Expected**: Should show error: "Temperature for Maximum Temperature (60°C) is above the maximum allowed temperature (50°C)."

### Test Case 4: Min Temperature Greater Than Max Temperature
- **Min Temperature**: `30`
- **Max Temperature**: `20`
- **Expected**: Should show error: "Minimum temperature must be less than maximum temperature."

### Test Case 5: No Global Limits Configured
- Set both `min_temp` and `max_temp` to `0` or empty in Logistics Settings
- **Expected**: Validation should be skipped (allows any temperature values)

---

## Module-Specific Testing

### 1. Air Shipment Module

#### Setup
1. Navigate to **Air Shipment** (`/app/air-shipment`)
2. Create a new Air Shipment or open an existing one
3. Enable **Requires Temperature Control** checkbox

#### Test Steps

**Test 1.1: Valid Temperature Range**
1. Set **Minimum Temperature**: `-20`
2. Set **Maximum Temperature**: `20`
3. Click **Save**
4. **Expected**: Document saves successfully

**Test 1.2: Temperature Below Global Minimum**
1. Set **Minimum Temperature**: `-60` (below configured min)
2. Set **Maximum Temperature**: `20`
3. Click **Save**
4. **Expected**: Error message appears: "Temperature for Minimum Temperature (-60°C) is below the minimum allowed temperature (-50°C)."

**Test 1.3: Temperature Above Global Maximum**
1. Set **Minimum Temperature**: `-20`
2. Set **Maximum Temperature**: `60` (above configured max)
3. Click **Save**
4. **Expected**: Error message appears: "Temperature for Maximum Temperature (60°C) is above the maximum allowed temperature (50°C)."

**Test 1.4: Min Greater Than Max**
1. Set **Minimum Temperature**: `30`
2. Set **Maximum Temperature**: `20`
3. Click **Save**
4. **Expected**: Error message appears: "Minimum temperature must be less than maximum temperature."

**Test 1.5: Temperature Control Disabled**
1. Uncheck **Requires Temperature Control**
2. Set any temperature values (even invalid ones)
3. Click **Save**
4. **Expected**: Document saves (validation only runs when temperature control is enabled)

---

### 2. Transport Order Package Module

#### Setup
1. Navigate to **Transport Order** (`/app/transport-order`)
2. Create a new Transport Order or open an existing one
3. Go to the **Packages** child table
4. Add a new package row
5. Enable **Temp Controlled** checkbox

#### Test Steps

**Test 2.1: Valid Temperature Range**
1. In a package row, check **Temp Controlled**
2. Set **Min Temperature**: `-20`
3. Set **Max Temperature**: `20`
4. Click **Save** on the Transport Order
5. **Expected**: Document saves successfully

**Test 2.2: Temperature Below Global Minimum**
1. In a package row, check **Temp Controlled**
2. Set **Min Temperature**: `-60`
3. Set **Max Temperature**: `20`
4. Click **Save** on the Transport Order
5. **Expected**: Error message appears: "Temperature for Minimum Temperature (-60°C) is below the minimum allowed temperature (-50°C)."

**Test 2.3: Temperature Above Global Maximum**
1. In a package row, check **Temp Controlled**
2. Set **Min Temperature**: `-20`
3. Set **Max Temperature**: `60`
4. Click **Save** on the Transport Order
5. **Expected**: Error message appears: "Temperature for Maximum Temperature (60°C) is above the maximum allowed temperature (50°C)."

**Test 2.4: Multiple Packages with Different Temperatures**
1. Add multiple package rows
2. In Package 1: Temp Controlled = Yes, Min = `-20`, Max = `20` (valid)
3. In Package 2: Temp Controlled = Yes, Min = `-60`, Max = `20` (invalid)
4. Click **Save** on the Transport Order
5. **Expected**: Error message appears for Package 2

**Test 2.5: Temp Controlled Disabled**
1. In a package row, leave **Temp Controlled** unchecked
2. Set any temperature values (even invalid ones)
3. Click **Save** on the Transport Order
4. **Expected**: Document saves (validation only runs when temp_controlled is enabled)

---

### 3. Transport Job Package Module

#### Setup
1. Navigate to **Transport Job** (`/app/transport-job`)
2. Create a new Transport Job or open an existing one
3. Go to the **Packages** child table
4. Add a new package row
5. Enable **Temp Controlled** checkbox

#### Test Steps

**Test 3.1: Valid Temperature Range**
1. In a package row, check **Temp Controlled**
2. Set **Min Temperature**: `-20`
3. Set **Max Temperature**: `20`
4. Click **Save** on the Transport Job
5. **Expected**: Document saves successfully

**Test 3.2: Temperature Below Global Minimum**
1. In a package row, check **Temp Controlled**
2. Set **Min Temperature**: `-60`
3. Set **Max Temperature**: `20`
4. Click **Save** on the Transport Job
5. **Expected**: Error message appears: "Temperature for Minimum Temperature (-60°C) is below the minimum allowed temperature (-50°C)."

**Test 3.3: Temperature Above Global Maximum**
1. In a package row, check **Temp Controlled**
2. Set **Min Temperature**: `-20`
3. Set **Max Temperature**: `60`
4. Click **Save** on the Transport Job
5. **Expected**: Error message appears: "Temperature for Maximum Temperature (60°C) is above the maximum allowed temperature (50°C)."

**Test 3.4: Min Greater Than Max**
1. In a package row, check **Temp Controlled**
2. Set **Min Temperature**: `30`
3. Set **Max Temperature**: `20`
4. Click **Save** on the Transport Job
5. **Expected**: Error message appears: "Minimum temperature must be less than maximum temperature."

**Test 3.5: Temp Controlled Disabled**
1. In a package row, leave **Temp Controlled** unchecked
2. Set any temperature values (even invalid ones)
3. Click **Save** on the Transport Job
4. **Expected**: Document saves (validation only runs when temp_controlled is enabled)

---

## Quick Test Script (Python Console)

You can also test the validation programmatically using Frappe's Python console:

```python
# Test the validation utility directly
from logistics.utils.temperature_validation import validate_temperature, validate_temperature_range

# Test 1: Valid temperature
result = validate_temperature(25, "Test Temperature", raise_exception=False)
print(f"Test 1 - Valid: {result}")  # Should be (True, None)

# Test 2: Temperature below minimum (assuming min_temp = -50)
result = validate_temperature(-60, "Test Temperature", raise_exception=False)
print(f"Test 2 - Below Min: {result}")  # Should be (False, error_message)

# Test 3: Temperature above maximum (assuming max_temp = 50)
result = validate_temperature(60, "Test Temperature", raise_exception=False)
print(f"Test 3 - Above Max: {result}")  # Should be (False, error_message)

# Test 4: Valid temperature range
result = validate_temperature_range(-20, 20, raise_exception=False)
print(f"Test 4 - Valid Range: {result}")  # Should be (True, None)

# Test 5: Invalid range (min > max)
result = validate_temperature_range(30, 20, raise_exception=False)
print(f"Test 5 - Invalid Range: {result}")  # Should be (False, error_message)
```

---

## Verification Checklist

After testing, verify:

- [ ] Valid temperature ranges save successfully
- [ ] Temperatures below global minimum show error
- [ ] Temperatures above global maximum show error
- [ ] Min > Max shows error
- [ ] Validation is skipped when temperature control is disabled
- [ ] Validation is skipped when global limits are not configured
- [ ] Error messages are clear and informative
- [ ] All three modules (AirShipment, TransportOrderPackage, TransportJobPackage) work correctly

---

## Troubleshooting

### Validation Not Running
- Check that **Temperature Control** or **Temp Controlled** checkbox is enabled
- Verify that temperature values are actually set (not None)
- Check that global limits are configured in Logistics Settings

### Validation Always Fails
- Verify global limits in Logistics Settings are reasonable
- Check that the temperature values you're testing are within the configured range

### No Error Messages
- Ensure you're testing with values outside the configured range
- Check browser console for JavaScript errors
- Verify the validation is being called (check server logs)

---

## Notes

- The validation only runs when temperature control is explicitly enabled
- If global limits are not configured (both are None or 0), validation is skipped
- The validation checks both individual temperature values and temperature ranges
- Error messages include the specific temperature value and the limit that was exceeded
