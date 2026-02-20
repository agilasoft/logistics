# Chargeable Weight Analysis: Transport Order Package vs Real-World Scenarios

## Executive Summary

**Issue Found**: Transport Order Package has `chargeable_weight` and `chargeable_weight_uom` fields but **does NOT automatically calculate chargeable weight**, unlike Air and Sea freight modules which do.

## Current Implementation Status

### ✅ Air Freight (Air Booking / Air Shipment)
- **Automatic calculation**: YES
- **Method**: IATA standard with 6000 divisor
- **Formula**: `volume_weight = volume (m³) × 1,000,000 / 6000`
- **Chargeable weight**: `max(actual_weight, volume_weight)`
- **Location**: `air_booking.py` - `calculate_chargeable_weight()` method
- **Real-world standard**: ✅ Matches IATA standard (167 kg/m³)

### ✅ Sea Freight (Sea Shipment)
- **Automatic calculation**: YES
- **Method**: Direction-based factors
- **Formula**: 
  - Domestic: `volume_weight = volume × 333`
  - International: `volume_weight = volume × 1000`
- **Chargeable weight**: `max(actual_weight, volume_weight)`
- **Location**: `sea_shipment.py` - `compute_chargeable()` method
- **Real-world standard**: ✅ Matches common sea freight practices

### ❌ Transport Order Package
- **Automatic calculation**: NO
- **Fields exist**: `chargeable_weight`, `chargeable_weight_uom`
- **Current behavior**: Manual entry only
- **Real-world standard**: ❌ Missing automatic calculation

## Real-World Standards for Road Transport

Based on industry research:

1. **Common Factor**: 1:3 ratio (÷ 3000)
   - Formula: `volume_weight = volume (m³) × 1,000,000 / 3000`
   - Equivalent to: 333 kg/m³ density

2. **Regional Variations**:
   - Europe: Often uses 3000 divisor
   - Asia: Varies by carrier (2500-4000 range)
   - North America: Typically 3000-5000 divisor

3. **Calculation Method**:
   - Always uses: `chargeable_weight = max(actual_weight, volume_weight)`
   - This ensures carriers bill based on whichever is greater

## Comparison Table

| Module | Auto-Calculate | Factor/Divisor | Real-World Match |
|--------|---------------|----------------|------------------|
| Air Freight | ✅ Yes | 6000 (IATA) | ✅ Yes |
| Sea Freight | ✅ Yes | 333/1000 | ✅ Yes |
| **Transport Order** | ❌ **No** | **None** | ❌ **No** |

## Impact

1. **User Experience**: Users must manually calculate and enter chargeable weight
2. **Accuracy Risk**: Manual calculations prone to errors
3. **Inconsistency**: Different from Air/Sea freight behavior
4. **Real-World Gap**: Doesn't match how carriers actually bill

## Recommendation

Implement automatic chargeable weight calculation for Transport Order Package similar to Air and Sea freight:

1. **Add to Transport Settings**:
   - `volume_to_weight_divisor` field (default: 3000 for road transport)
   - `chargeable_weight_calculation` method (default: "Higher of Both")

2. **Implement Calculation**:
   - Server-side: Add `calculate_chargeable_weight()` method in `transport_order_package.py`
   - Client-side: Add calculation trigger in `transport_order_package.js` when volume/weight changes

3. **Formula**:
   ```python
   volume_weight = volume (m³) × 1,000,000 / divisor
   chargeable_weight = max(actual_weight, volume_weight)
   ```

4. **Default Divisor**: 3000 (common road transport standard)

## Files to Modify

1. `logistics/transport/doctype/transport_settings/transport_settings.json`
   - Add `volume_to_weight_divisor` field
   - Add `chargeable_weight_calculation` field

2. `logistics/transport/doctype/transport_order_package/transport_order_package.py`
   - Add `calculate_chargeable_weight()` method

3. `logistics/transport/doctype/transport_order_package/transport_order_package.js`
   - Add calculation triggers on volume/weight changes

## Conclusion

Transport Order Package is missing automatic chargeable weight calculation that exists in Air and Sea freight modules. This creates inconsistency and doesn't match real-world carrier billing practices. Implementation should follow the same pattern as Air/Sea freight for consistency.
