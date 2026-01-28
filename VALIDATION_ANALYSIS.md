# Booking to Shipment Conversion - Validation Analysis

## Overview
This document analyzes all validations and required fields for Booking and Shipment doctypes to ensure smooth conversion from Booking to Shipment.

---

## Sea Booking → Sea Shipment

### Sea Booking Required Fields (from JSON + Python validation)

**From JSON (reqd: 1):**
- `booking_date` ✓
- `local_customer` ✓
- `direction` ✓
- `company` ✓

**From Python `validate_required_fields()`:**
- `booking_date` ✓
- `local_customer` ✓
- `direction` ✓
- `shipper` ✓
- `consignee` ✓
- `origin_port` ✓
- `destination_port` ✓

**Additional Validations:**
- `validate_dates()`: ETD must be before ETA
- `validate_accounts()`: Cost center, profit center, and branch must belong to company

### Sea Shipment Required Fields (from JSON + Python validation)

**From JSON (reqd: 1):**
- `booking_date` ✓
- `shipper` ✓
- `consignee` ✓
- `origin_port` ✓
- `destination_port` ✓
- `direction` ✓
- `local_customer` ✓
- `company` ✓
- `branch` ✓
- `cost_center` ✓
- `profit_center` ✓

**From Python `validate_required_fields()`:**
- `booking_date` ✓
- `shipper` ✓
- `consignee` ✓
- `origin_port` ✓
- `destination_port` ✓
- `direction` ✓
- `local_customer` ✓
- `shipping_line` OR `master_bill` (conditional) ⚠️

**Additional Validations:**
- `validate_dates()`: ETD must be before ETA, booking date warning if future
- `validate_accounts()`: Cost center, profit center, and branch must belong to company
- `validate_weight_volume()`: Weight/volume must be positive, chargeable >= weight
- `validate_packages()`: Package weights/volumes should match totals
- `validate_containers()`: Container validation
- `validate_master_bill()`: Master bill validation if linked

### Conversion Issues Identified

1. **CRITICAL: Missing Required Fields in Conversion**
   - ❌ `branch` - Required in Sea Shipment but not always set in Sea Booking
   - ❌ `cost_center` - Required in Sea Shipment but not always set in Sea Booking
   - ❌ `profit_center` - Required in Sea Shipment but not always set in Sea Booking
   - ⚠️ `shipping_line` - Required in Sea Shipment unless `master_bill` is set, but conversion doesn't check this

2. **Field Mapping Issues**
   - `origin_port` and `destination_port` in Sea Booking use "Location" doctype, but Sea Shipment uses "UNLOCO" doctype
   - This could cause validation errors if the Location doesn't exist as UNLOCO

3. **Missing Validations in Conversion**
   - Conversion doesn't validate that all required fields are present before creating Shipment
   - No check for `shipping_line` or `master_bill` before conversion

---

## Air Booking → Air Shipment

### Air Booking Required Fields (from JSON + Python validation)

**From JSON (reqd: 1):**
- `booking_date` ✓
- `local_customer` ✓
- `direction` ✓
- `company` ✓
- `branch` ✓
- `cost_center` ✓
- `profit_center` ✓

**From Python `validate_required_fields()`:**
- `booking_date` ✓
- `local_customer` ✓
- `direction` ✓
- `shipper` ✓
- `consignee` ✓
- `origin_port` ✓
- `destination_port` ✓

**Additional Validations:**
- `validate_dates()`: ETD must be before ETA
- `validate_accounts()`: Cost center, profit center, and branch must belong to company (with field existence checks)
- `calculate_chargeable_weight()`: Auto-calculates chargeable weight

### Air Shipment Required Fields (from JSON + Python validation)

**From JSON (reqd: 1):**
- `booking_date` ✓
- `shipper` ✓
- `consignee` ✓
- `origin_port` ✓
- `destination_port` ✓
- `direction` ✓
- `local_customer` ✓
- `company` ✓
- `branch` ✓
- `cost_center` ✓
- `profit_center` ✓

**From Python `validate()` method:**
- No explicit `validate_required_fields()` method, but validates:
  - `validate_dates()`: ETD must be before ETA
  - `validate_weight_volume()`: Weight/volume validation
  - `validate_packages()`: Package validation
  - `validate_awb()`: AWB validation
  - `validate_uld()`: ULD validation
  - `validate_dangerous_goods()`: DG validation (if contains_dangerous_goods = 1)
  - `validate_dg_compliance()`: DG compliance validation
  - `validate_accounts()`: Account validation

**Additional Validations:**
- Dangerous Goods: If `contains_dangerous_goods = 1`, requires:
  - `dg_declaration_complete = 1` (if required by settings)
  - `dg_emergency_contact` (name, phone, email)
  - For DG packages: UN Number, Proper Shipping Name, DG Class, Packing Group, Emergency Contact

### Conversion Issues Identified

1. **CRITICAL: Missing Required Fields in Conversion**
   - ✅ `branch` - Already required in Air Booking, so conversion should work
   - ✅ `cost_center` - Already required in Air Booking, so conversion should work
   - ✅ `profit_center` - Already required in Air Booking, so conversion should work

2. **Field Mapping Issues**
   - ⚠️ `service_level`, `release_type`, `uld_type` - Conversion checks if these exist before copying, which is good
   - However, if they don't exist, they're set to None, which might cause issues if they're required

3. **Link Field Validation**
   - Conversion has error handling for invalid link fields (service_level, release_type)
   - This is good, but could be improved by validating before insert

4. **Missing Validations in Conversion**
   - No validation that dangerous goods fields are complete if `contains_dangerous_goods = 1`
   - No validation for required accounting fields before conversion

---

## Recommendations

### For Sea Booking → Sea Shipment Conversion

1. **Add Pre-Conversion Validation**
   ```python
   def validate_before_conversion(self):
       """Validate that all required fields are present before conversion"""
       # Check required accounting fields
       if not self.branch:
           frappe.throw(_("Branch is required for conversion to Sea Shipment"))
       if not self.cost_center:
           frappe.throw(_("Cost Center is required for conversion to Sea Shipment"))
       if not self.profit_center:
           frappe.throw(_("Profit Center is required for conversion to Sea Shipment"))
       
       # Check shipping_line or master_bill
       if not self.shipping_line and not self.master_bill:
           frappe.throw(_("Shipping Line or Master Bill is required for conversion to Sea Shipment"))
       
       # Validate port types (Location vs UNLOCO)
       if self.origin_port:
           if not frappe.db.exists("UNLOCO", self.origin_port):
               frappe.throw(_("Origin Port must be a valid UNLOCO code"))
       if self.destination_port:
           if not frappe.db.exists("UNLOCO", self.destination_port):
               frappe.throw(_("Destination Port must be a valid UNLOCO code"))
   ```

2. **Update Conversion Method**
   - Call `validate_before_conversion()` at the start of `convert_to_shipment()`
   - Ensure all required fields are mapped
   - Add validation for port type conversion (Location → UNLOCO)

### For Air Booking → Air Shipment Conversion

1. **Add Pre-Conversion Validation**
   ```python
   def validate_before_conversion(self):
       """Validate that all required fields are present before conversion"""
       # Check dangerous goods requirements
       if self.contains_dangerous_goods:
           if not self.dg_declaration_complete:
               frappe.throw(_("Dangerous Goods Declaration must be complete before conversion"))
           if not self.dg_emergency_contact:
               frappe.throw(_("Dangerous Goods Emergency Contact is required"))
           if not self.dg_emergency_phone:
               frappe.throw(_("Dangerous Goods Emergency Phone is required"))
       
       # Validate link fields exist
       if self.service_level and not frappe.db.exists("Service Level Agreement", self.service_level):
           frappe.throw(_("Service Level '{0}' does not exist").format(self.service_level))
       if self.release_type and not frappe.db.exists("Release Type", self.release_type):
           frappe.throw(_("Release Type '{0}' does not exist").format(self.release_type))
       if self.uld_type and not frappe.db.exists("ULD Type", self.uld_type):
           frappe.throw(_("ULD Type '{0}' does not exist").format(self.uld_type))
   ```

2. **Update Conversion Method**
   - Call `validate_before_conversion()` at the start of `convert_to_shipment()`
   - Validate dangerous goods fields if applicable
   - Ensure all link fields are valid before copying

### General Recommendations

1. **Add Conversion Button Validation**
   - Disable "Convert to Shipment" button if required fields are missing
   - Show helpful message indicating which fields are missing

2. **Add Conversion Checklist**
   - Create a method that returns a list of missing required fields
   - Display this to the user before conversion

3. **Improve Error Messages**
   - Provide specific field names in error messages
   - Suggest how to fix the issue

4. **Add Field Mapping Documentation**
   - Document which fields are mapped from Booking to Shipment
   - Document any field type conversions (e.g., Location → UNLOCO)

---

## Summary of Critical Issues

### Sea Booking → Sea Shipment
1. ❌ **CRITICAL**: Missing `branch`, `cost_center`, `profit_center` validation before conversion
2. ❌ **CRITICAL**: Missing `shipping_line` or `master_bill` validation
3. ⚠️ **WARNING**: Port type mismatch (Location vs UNLOCO)

### Air Booking → Air Shipment
1. ✅ **GOOD**: All required accounting fields are already required in Air Booking
2. ⚠️ **WARNING**: Dangerous goods validation not checked before conversion
3. ⚠️ **WARNING**: Link field validation could be improved

---

## Action Items

1. [ ] Add `validate_before_conversion()` method to Sea Booking
2. [ ] Add `validate_before_conversion()` method to Air Booking
3. [ ] Update Sea Booking `convert_to_shipment()` to call validation
4. [ ] Update Air Booking `convert_to_shipment()` to call validation
5. [ ] Add port type validation/conversion for Sea Booking
6. [ ] Add dangerous goods validation for Air Booking conversion
7. [ ] Update UI to show conversion readiness status
8. [ ] Add conversion checklist/preview feature
