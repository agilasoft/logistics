# Issue: Charges from Sales Quote Not Populating to Bookings and Orders

## Problem Summary

When creating Bookings (Air Booking, Sea Booking) or Orders (Transport Order) from a Sales Quote, **only charges matching the specific service type are being populated**, while charges of other service types are ignored.

## Root Cause

The charge population functions in each booking/order type filter charges by `service_type`:

### Air Booking
- **Location**: `logistics/air_freight/doctype/air_booking/air_booking.py` (line 823)
- **Filter**: Only fetches charges where `service_type = "Air"`
- **Result**: Customs, Warehousing, or other service type charges are excluded

### Sea Booking  
- **Location**: `logistics/sea_freight/doctype/sea_booking/sea_booking.py` (line 801)
- **Filter**: Only fetches charges where `service_type = "Sea"`
- **Result**: Customs, Warehousing, or other service type charges are excluded

### Transport Order
- **Location**: `logistics/transport/doctype/transport_order/transport_order.py` (line 1026)
- **Filter**: Only fetches charges where `service_type = "Transport"`
- **Result**: Customs, Warehousing, or other service type charges are excluded

## Example Scenario

If a Sales Quote contains:
- 3 Air charges (service_type = "Air")
- 2 Customs charges (service_type = "Customs")
- 1 Warehousing charge (service_type = "Warehousing")

When creating an **Air Booking** from this quote:
- ✅ 3 Air charges will populate
- ❌ 2 Customs charges will NOT populate
- ❌ 1 Warehousing charge will NOT populate

## Why This Happens

The charge population logic was designed to only populate charges relevant to the specific booking/order type. However, in practice, Sales Quotes often contain multiple service types (e.g., Air + Customs, Sea + Warehousing), and users expect all charges to transfer.

## Impact

1. **Missing Charges**: Important charges like Customs, Warehousing, or other services are not automatically transferred
2. **Manual Work**: Users must manually add these charges after creating the booking/order
3. **Data Inconsistency**: The booking/order doesn't reflect the complete pricing from the Sales Quote
4. **Billing Errors**: Missing charges can lead to incorrect invoicing

## Solution Options

### Option 1: Populate All Charges (Recommended)
Modify the charge population functions to fetch **all charges** from the Sales Quote, regardless of service_type. This would require:
- Removing or modifying the `service_type` filter in the database queries
- Ensuring the booking/order charge tables can handle different service types
- Testing that all charge types map correctly to the target document structure

### Option 2: Populate Main Service + Related Services
Create a mapping of which service types should populate to which booking/order types:
- Air Booking: Air + Customs + Warehousing (if applicable)
- Sea Booking: Sea + Customs + Warehousing (if applicable)  
- Transport Order: Transport + Customs + Warehousing (if applicable)

### Option 3: User Selection
Add a UI option when creating bookings/orders to let users choose:
- "Populate only [Service Type] charges" (current behavior)
- "Populate all charges" (new behavior)

## Files That Need Modification

1. `logistics/air_freight/doctype/air_booking/air_booking.py` - `_populate_charges_from_sales_quote()` method
2. `logistics/sea_freight/doctype/sea_booking/sea_booking.py` - `_populate_charges_from_sales_quote()` method  
3. `logistics/transport/doctype/transport_order/transport_order.py` - `_populate_charges_from_sales_quote()` method
4. Potentially the charge mapping functions if they need to handle different service types

## Technical Details

The filtering happens in the database query using `frappe.get_all()`:

```python
# Current (filtered by service_type)
filters={"parent": sq_name, "parenttype": "Sales Quote", "service_type": "Air"}

# Proposed (all charges)
filters={"parent": sq_name, "parenttype": "Sales Quote"}
```

## Next Steps

1. Verify that booking/order charge tables can accept charges of different service types
2. Test charge mapping functions with different service types
3. Implement the chosen solution
4. Test with real Sales Quotes containing multiple service types
5. Update documentation if needed
