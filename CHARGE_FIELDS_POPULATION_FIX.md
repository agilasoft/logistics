# Charge Fields Population Fix

## Problem Summary

When converting Sales Quotes into Bookings (Sea Booking, Air Booking) or Orders (Transport Order), several charge fields were not being populated correctly:

### Fields Not Getting Populated

1. **`item_code`** - Was being mapped as `charge_item` (wrong field name)
2. **`item_name`** - Was being mapped as `charge_name` (wrong field name)  
3. **`charge_category`** - Not being fetched from Sales Quote Charge
4. **`description`** - Not being populated from item description
5. **`item_tax_template`** - Not being populated from item
6. **`invoice_type`** - Not being populated from item
7. **`bill_to`** - Not being fetched from Sales Quote Charge (Sea Booking only)
8. **`pay_to`** - Not being fetched from Sales Quote Charge (Sea Booking only)

## Root Causes

### Sea Booking Issues
1. **Wrong field names**: The mapping function was using `charge_item` and `charge_name` instead of the correct `item_code` and `item_name` fields that exist in Sea Booking Charges
2. **Missing fields in fetch**: `charge_category`, `bill_to`, and `pay_to` were not included in the fields list when fetching from Sales Quote Charge
3. **Missing fields in mapping**: `charge_category`, `description`, `item_tax_template`, and `invoice_type` were not being mapped

### Air Booking Issues
1. **Missing field in fetch**: `charge_category` was not included in the fields list
2. **Missing fields in mapping**: `description`, `item_tax_template`, and `invoice_type` were not being mapped
3. **Charge category priority**: Was only checking item, not Sales Quote record first

### Transport Order Issues
1. **Missing fields in SALES_QUOTE_CHARGE_FIELDS**: `charge_category`, `bill_to`, and `pay_to` were not included
2. **Missing fields in mapping**: `charge_category`, `description`, `item_tax_template`, and `invoice_type` were not being mapped

## Fixes Implemented

### Sea Booking (`sea_booking.py`)

1. **Updated `charge_fields` list** (line ~2110):
   - Added `charge_category`
   - Added `bill_to`
   - Added `pay_to`

2. **Fixed mapping function** (`_map_sales_quote_sea_freight_to_charge`, line ~1057):
   - Changed `"charge_item"` → `"item_code"`
   - Changed `"charge_name"` → `"item_name"`
   - Added `charge_category` mapping (checks Sales Quote record first, then item, then defaults to "Other")
   - Added `description` mapping (from item description or item_name fallback)
   - Added `item_tax_template` mapping (from item if available)
   - Added `invoice_type` mapping (from item if available)

### Air Booking (`air_booking.py`)

1. **Updated `charge_fields` list** (line ~2377):
   - Added `charge_category`

2. **Updated mapping function** (`_map_sales_quote_air_freight_to_charge`, line ~1379):
   - Updated `charge_category` logic to check Sales Quote record first, then item, then default
   - Added `description` mapping (from item description or item_name fallback)
   - Added `item_tax_template` mapping (from item if available)
   - Added `invoice_type` mapping (from item if available)

### Transport Order (`transport_order.py`)

1. **Updated `SALES_QUOTE_CHARGE_FIELDS`** (line ~18):
   - Added `charge_category`
   - Added `bill_to`
   - Added `pay_to`

2. **Updated mapping function** (`_map_sales_quote_transport_to_charge`, line ~1183):
   - Added `charge_category` mapping (checks Sales Quote record first, then item, then defaults to "Other")
   - Added `description` mapping (from item description or item_name fallback)
   - Added `item_tax_template` mapping (from item if available)
   - Added `invoice_type` mapping (from item if available)
   - Improved item document handling with proper error handling

3. **Updated helper function** (`_map_sales_quote_transport_to_charge_dict`, line ~1565):
   - Applied same fixes as the main mapping function

## Field Mapping Priority

For fields that can come from multiple sources, the priority order is:

1. **Sales Quote Charge record** (highest priority)
2. **Item document** (fallback)
3. **Default value** (lowest priority)

This applies to:
- `charge_category`
- `item_name` (if not in Sales Quote)
- `description` (from item description)

## Testing Recommendations

After these fixes, verify that when converting a Sales Quote to a Booking/Order:

1. ✅ All charge rows have `item_code` and `item_name` populated
2. ✅ `charge_category` is populated from Sales Quote or Item
3. ✅ `description` is populated from item description
4. ✅ `item_tax_template` is populated if set on the item
5. ✅ `invoice_type` is populated if set on the item
6. ✅ `bill_to` and `pay_to` are populated from Sales Quote Charge (where applicable)

## Files Modified

1. `logistics/sea_freight/doctype/sea_booking/sea_booking.py`
2. `logistics/air_freight/doctype/air_booking/air_booking.py`
3. `logistics/transport/doctype/transport_order/transport_order.py`
