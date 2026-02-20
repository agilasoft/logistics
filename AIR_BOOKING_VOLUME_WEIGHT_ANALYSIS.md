# Air Booking Volume and Weight Field Analysis

## Current Implementation Review

### Volume Field
- **Storage**: Stored in m³ (cubic meters) at header level
- **Aggregation**: ✅ Automatically aggregated from packages via `aggregate_volume_from_packages()`
- **UOM Conversion**: ✅ Supports UOM conversion from package volumes
- **Usage**: Used in chargeable weight calculation

### Weight Field
- **Storage**: Stored in kg (kilograms) at header level
- **Aggregation**: ❌ **NOT automatically aggregated from packages** (only volume is aggregated)
- **UOM Conversion**: ⚠️ Packages have weight_uom, but header weight is not aggregated
- **Usage**: Used in chargeable weight calculation

### Chargeable Weight Calculation
- **Formula**: `chargeable = max(actual_weight, volume_weight)`
- **Volume Weight Formula**: `volume_weight = volume (m³) × 1,000,000 / divisor`
- **Default Divisor**: 6000 (IATA standard = 167 kg/m³)
- **Custom Divisor**: Supported via airline settings or manual override

---

## Real-World Air Freight Standards

### IATA Standards
1. **Volume Weight Calculation**: 
   - Standard divisor: **6000 cm³/kg** (167 kg/m³)
   - Formula: `Volume (cm³) ÷ 6000 = Volume Weight (kg)`
   - Alternative: `Volume (m³) × 167 = Volume Weight (kg)`

2. **Chargeable Weight**:
   - Always the **higher** of actual weight or volumetric weight
   - This is correctly implemented in the system

3. **Common Airline Divisors**:
   - **IATA Standard**: 6000 (most airlines)
   - **Some Airlines**: 5000 (200 kg/m³) - for denser cargo
   - **Some Airlines**: 7000 (143 kg/m³) - for lighter cargo
   - **Custom Routes**: May vary by origin/destination

### Real-World Scenarios

#### Scenario 1: Lightweight, Bulky Cargo
- **Dimensions**: 100 cm × 200 cm × 500 cm = 10,000,000 cm³ = 10 m³
- **Actual Weight**: 500 kg
- **Volume Weight**: 10 m³ × 167 = 1,670 kg
- **Chargeable Weight**: 1,670 kg (volume weight is higher)
- **Issue**: Shippers pay for 1,170 kg more than actual weight
- **Impact**: High cost for low-density goods

#### Scenario 2: Dense, Heavy Cargo
- **Dimensions**: 50 cm × 50 cm × 50 cm = 125,000 cm³ = 0.125 m³
- **Actual Weight**: 200 kg
- **Volume Weight**: 0.125 m³ × 167 = 20.875 kg
- **Chargeable Weight**: 200 kg (actual weight is higher)
- **Issue**: None - actual weight is used

#### Scenario 3: Mixed Packages
- **Package 1**: 1 m³, 100 kg → Volume weight: 167 kg → Chargeable: 167 kg
- **Package 2**: 0.5 m³, 150 kg → Volume weight: 83.5 kg → Chargeable: 150 kg
- **Total Actual**: 250 kg
- **Total Volume**: 1.5 m³ → Volume weight: 250.5 kg
- **Total Chargeable**: max(250, 250.5) = **250.5 kg**

---

## Issues Identified

### 🔴 Critical Issues

#### 1. Weight Not Aggregated from Packages
**Current Behavior**: 
- Volume is automatically aggregated from packages
- Weight is NOT aggregated from packages
- User must manually enter header weight

**Real-World Impact**:
- Risk of data inconsistency
- Manual entry errors
- Discrepancy between package totals and header weight

**Example**:
```
Package 1: 50 kg
Package 2: 75 kg
Package 3: 25 kg
Total: 150 kg

But header weight might be manually entered as 140 kg (error!)
```

#### 2. No Validation for Weight/Volume Consistency
**Current Behavior**:
- No validation to ensure header weight matches package weight totals
- No warning when chargeable weight differs significantly from actual weight

**Real-World Impact**:
- Billing errors
- Customer disputes
- Revenue loss

### ⚠️ Medium Priority Issues

#### 3. Volume Aggregation Overwrites Manual Entry
**Current Behavior**:
- `aggregate_volume_from_packages()` always overwrites header volume if packages exist
- No option to preserve manual volume entry

**Real-World Impact**:
- Cannot handle cases where header volume needs manual adjustment
- Loss of manual corrections

#### 4. No Density Validation
**Current Behavior**:
- No check for unrealistic density values
- No warning for low-density cargo (high volume, low weight)

**Real-World Impact**:
- Missed optimization opportunities
- Unexpected high charges for customers

#### 5. No Package-Level Chargeable Weight Validation
**Current Behavior**:
- Package-level chargeable weight exists but is not validated against header
- No consistency check

---

## Recommendations

### 🔧 High Priority Fixes

#### 1. Implement Weight Aggregation from Packages
**Action**: Add `aggregate_weight_from_packages()` method similar to volume aggregation

```python
def aggregate_weight_from_packages(self):
    """Set header weight from sum of package weights, converted to base/default weight UOM."""
    packages = getattr(self, "packages", []) or []
    if not packages:
        return
    try:
        from logistics.utils.measurements import convert_weight, get_default_uoms
        defaults = get_default_uoms(company=getattr(self, "company", None))
        target_weight_uom = defaults.get("weight")  # Typically "Kg"
        if not target_weight_uom:
            return
        target_normalized = str(target_weight_uom).strip().upper()
        total = 0
        for pkg in packages:
            pkg_weight = flt(getattr(pkg, "weight", 0) or 0)
            if pkg_weight <= 0:
                continue
            pkg_weight_uom = getattr(pkg, "weight_uom", None) or defaults.get("weight")
            if not pkg_weight_uom:
                continue
            if str(pkg_weight_uom).strip().upper() == target_normalized:
                total += pkg_weight
            else:
                total += convert_weight(
                    pkg_weight,
                    from_uom=pkg_weight_uom,
                    to_uom=target_weight_uom,
                    company=getattr(self, "company", None),
                )
        if total > 0:
            self.weight = total
    except Exception:
        pass
```

**Call in `validate()` method**:
```python
def validate(self):
    # ... existing code ...
    self.aggregate_volume_from_packages()
    self.aggregate_weight_from_packages()  # ADD THIS
    self.calculate_chargeable_weight()
```

#### 2. Add Weight/Volume Consistency Validation
**Action**: Add validation to warn when header weight doesn't match package totals

```python
def validate_weight_consistency(self):
    """Warn if header weight doesn't match package weight totals."""
    packages = getattr(self, "packages", []) or []
    if not packages:
        return
    
    try:
        from logistics.utils.measurements import convert_weight, get_default_uoms
        defaults = get_default_uoms(company=getattr(self, "company", None))
        target_weight_uom = defaults.get("weight")
        if not target_weight_uom:
            return
        
        total_package_weight = 0
        for pkg in packages:
            pkg_weight = flt(getattr(pkg, "weight", 0) or 0)
            if pkg_weight <= 0:
                continue
            pkg_weight_uom = getattr(pkg, "weight_uom", None) or defaults.get("weight")
            if not pkg_weight_uom:
                continue
            if str(pkg_weight_uom).strip().upper() == str(target_weight_uom).strip().upper():
                total_package_weight += pkg_weight
            else:
                total_package_weight += convert_weight(
                    pkg_weight,
                    from_uom=pkg_weight_uom,
                    to_uom=target_weight_uom,
                    company=getattr(self, "company", None),
                )
        
        header_weight = flt(self.weight) or 0
        if header_weight > 0 and total_package_weight > 0:
            difference = abs(header_weight - total_package_weight)
            difference_percent = (difference / max(header_weight, total_package_weight)) * 100
            
            # Warn if difference is more than 5%
            if difference_percent > 5:
                frappe.msgprint(
                    _("Warning: Header weight ({0} kg) differs from package total ({1} kg) by {2:.1f}%").format(
                        header_weight, total_package_weight, difference_percent
                    ),
                    title=_("Weight Mismatch"),
                    indicator="orange"
                )
    except Exception:
        pass
```

### 🔧 Medium Priority Improvements

#### 3. Add Density Warning
**Action**: Warn users about low-density cargo that will incur high volumetric charges

```python
def validate_density(self):
    """Warn if cargo density is very low (high volume, low weight)."""
    if not self.volume or not self.weight or self.volume <= 0 or self.weight <= 0:
        return
    
    # Calculate density: kg/m³
    density = self.weight / self.volume
    
    # IATA standard: 167 kg/m³ (6000 divisor)
    # Warn if density is less than 50% of standard (83.5 kg/m³)
    if density < 83.5:
        volume_weight = self.volume * 167
        extra_charge = volume_weight - self.weight
        frappe.msgprint(
            _("Low density cargo detected ({0:.1f} kg/m³). "
              "Volumetric weight ({1:.1f} kg) exceeds actual weight ({2:.1f} kg) by {3:.1f} kg. "
              "Consider optimizing packaging to reduce volume.").format(
                density, volume_weight, self.weight, extra_charge
            ),
            title=_("Density Warning"),
            indicator="orange"
        )
```

#### 4. Add Option to Preserve Manual Volume/Weight
**Action**: Add checkbox to prevent automatic aggregation

**Field in JSON**:
```json
{
  "fieldname": "auto_aggregate_measurements",
  "fieldtype": "Check",
  "default": 1,
  "label": "Auto Aggregate from Packages"
}
```

**Modify aggregation methods**:
```python
def aggregate_volume_from_packages(self):
    if not getattr(self, "auto_aggregate_measurements", True):
        return
    # ... existing code ...
```

#### 5. Add Package-Level Chargeable Weight Calculation
**Action**: Calculate chargeable weight per package and validate against header

```python
def validate_package_chargeable_weights(self):
    """Calculate and validate package-level chargeable weights."""
    packages = getattr(self, "packages", []) or []
    if not packages:
        return
    
    divisor = self.get_volume_to_weight_divisor()
    total_package_chargeable = 0
    
    for pkg in packages:
        pkg_weight = flt(getattr(pkg, "weight", 0) or 0)
        pkg_volume = flt(getattr(pkg, "volume", 0) or 0)
        
        if pkg_volume > 0:
            # Convert package volume to m³ if needed
            from logistics.utils.measurements import convert_volume, get_default_uoms
            defaults = get_default_uoms(company=getattr(self, "company", None))
            target_volume_uom = get_aggregation_volume_uom(company=getattr(self, "company", None))
            pkg_volume_uom = getattr(pkg, "volume_uom", None) or defaults.get("volume")
            
            if pkg_volume_uom != target_volume_uom:
                pkg_volume = convert_volume(
                    pkg_volume,
                    from_uom=pkg_volume_uom,
                    to_uom=target_volume_uom,
                    company=getattr(self, "company", None),
                )
            
            pkg_volume_weight = pkg_volume * (1000000.0 / divisor)
            pkg_chargeable = max(pkg_weight, pkg_volume_weight)
            total_package_chargeable += pkg_chargeable
    
    header_chargeable = flt(self.chargeable) or 0
    if header_chargeable > 0 and total_package_chargeable > 0:
        difference = abs(header_chargeable - total_package_chargeable)
        if difference > 0.1:  # Allow small rounding differences
            frappe.msgprint(
                _("Package chargeable weight total ({0:.2f} kg) differs from header chargeable weight ({1:.2f} kg)").format(
                    total_package_chargeable, header_chargeable
                ),
                title=_("Chargeable Weight Mismatch"),
                indicator="orange"
            )
```

### 📊 UI/UX Improvements

#### 6. Add Visual Indicators
- Show density ratio (actual weight / volume weight)
- Color-code chargeable weight field:
  - Green: Actual weight is chargeable (dense cargo)
  - Orange: Volume weight is chargeable (light cargo)
- Display warning icon when volumetric weight exceeds actual by >20%

#### 7. Add Calculation Summary
Show breakdown in a read-only section:
```
Actual Weight: 500 kg
Volume: 10 m³
Volume Weight: 1,670 kg (10 × 167)
Chargeable Weight: 1,670 kg (Volume Weight)
Density: 50 kg/m³ (Low - consider packaging optimization)
```

---

## Implementation Priority

1. **🔴 Critical**: Implement weight aggregation from packages
2. **🔴 Critical**: Add weight/volume consistency validation
3. **⚠️ High**: Add density warning
4. **⚠️ Medium**: Add option to preserve manual entries
5. **⚠️ Medium**: Add package-level chargeable weight validation
6. **📊 Low**: UI/UX improvements

---

## Testing Scenarios

### Test Case 1: Weight Aggregation
1. Create Air Booking with 3 packages:
   - Package 1: 50 kg
   - Package 2: 75 kg
   - Package 3: 25 kg
2. Expected: Header weight = 150 kg (auto-calculated)

### Test Case 2: Volume Weight Calculation
1. Create Air Booking:
   - Volume: 10 m³
   - Weight: 500 kg
2. Expected: Chargeable = 1,670 kg (volume weight)

### Test Case 3: Consistency Warning
1. Create Air Booking:
   - Package total weight: 150 kg
   - Manual header weight: 140 kg
2. Expected: Warning message about 6.7% difference

### Test Case 4: Density Warning
1. Create Air Booking:
   - Volume: 10 m³
   - Weight: 100 kg
   - Density: 10 kg/m³ (very low)
2. Expected: Warning about low density and high volumetric charges

---

## Conclusion

The current implementation correctly follows IATA standards for chargeable weight calculation. However, **weight aggregation from packages is missing**, which is a critical gap compared to volume aggregation. Adding weight aggregation and validation will improve data consistency and reduce manual entry errors.

The system should also provide better feedback to users about density issues and chargeable weight calculations to help optimize shipping costs.
