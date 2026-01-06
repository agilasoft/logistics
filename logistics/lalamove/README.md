# Lalamove Integration - Implementation Guide

## Phase 2: Quotation Integration - Implementation Status

### Completed Components ✅

#### 1. JavaScript Utilities ✅
- `utils.js` - Core Lalamove client-side utilities
- `lalamove_form.js` - Form integration utilities
- Quotation dialog display
- Order status display
- Order management functions

#### 2. Form Scripts ✅
- Transport Order - Lalamove integration added
- Transport Job - Lalamove integration added
- Warehouse Job - Lalamove script created
- Air Shipment - Lalamove script created
- Sea Shipment - Lalamove script created

#### 3. Hooks Configuration ✅
- JavaScript files added to `app_include_js` in hooks.py
- Files will be loaded globally

### Next Steps

#### 1. Add Fields to Doctypes

Fields need to be added to the following doctypes. This can be done via:
- **Option A**: Customize doctypes in Frappe UI
- **Option B**: Run migration script (see `patches/add_lalamove_fields.py`)

**Fields to add:**

**Transport Order/Job/Leg:**
- `use_lalamove` (Check)
- `lalamove_order` (Link to Lalamove Order)
- `lalamove_quotation` (Link to Lalamove Quotation)

**Warehouse Job:**
- `use_lalamove` (Check)
- `lalamove_order` (Link)
- `lalamove_quotation` (Link)
- `delivery_address` (Link to Address)
- `delivery_contact` (Link to Contact)

**Air Shipment/Booking:**
- `use_lalamove` (Check)
- `last_mile_delivery_required` (Check)
- `last_mile_delivery_date` (Date)
- `lalamove_order` (Link)
- `lalamove_quotation` (Link)

**Sea Shipment/Booking:**
- `use_lalamove` (Check)
- `last_mile_delivery_required` (Check)
- `last_mile_delivery_date` (Date)
- `lalamove_order` (Link)
- `lalamove_quotation` (Link)

#### 2. Build Assets

After adding JavaScript files, rebuild assets:
```bash
bench build --app logistics
```

#### 3. Install Doctypes

Run migration to install new doctypes:
```bash
bench --site [site-name] migrate
```

#### 4. Configure Settings

1. Go to Lalamove Settings
2. Enter API credentials
3. Select environment (Sandbox/Production)
4. Set market code
5. Configure webhook URL
6. Enable integration

#### 5. Test Integration

1. Create a test Transport Order
2. Enable "Use Lalamove" checkbox
3. Save the document
4. Click "Lalamove" button
5. Test "Get Quotation"
6. Test "Create Order"

### File Locations

**JavaScript Files:**
- `/logistics/lalamove/utils.js` - Core utilities
- `/logistics/lalamove/lalamove_form.js` - Form utilities
- `/logistics/public/lalamove/` - Public assets (copied)

**Form Scripts:**
- `/logistics/transport/doctype/transport_order/transport_order.js` - Updated
- `/logistics/transport/doctype/transport_job/transport_job.js` - Updated
- `/logistics/warehousing/doctype/warehouse_job/warehouse_job_lalamove.js` - New
- `/logistics/air_freight/doctype/air_shipment/air_shipment_lalamove.js` - New
- `/logistics/sea_freight/doctype/sea_shipment/sea_shipment_lalamove.js` - New

### Known Issues / TODOs

1. **Field Addition**: Fields need to be added to doctypes (manual or via patch)
2. **Asset Building**: JavaScript files need to be built and served
3. **Address Geocoding**: Need to ensure addresses have coordinates
4. **Airport/Port Addresses**: Need to implement lookup from master data
5. **Form Script Loading**: May need to adjust how scripts are loaded

### Testing Checklist

- [ ] Add fields to all source doctypes
- [ ] Build assets (`bench build --app logistics`)
- [ ] Install doctypes (`bench migrate`)
- [ ] Configure Lalamove Settings
- [ ] Test quotation retrieval
- [ ] Test quotation display dialog
- [ ] Test order creation
- [ ] Test order status sync
- [ ] Test webhook endpoint
- [ ] Test error handling

---

**Status**: Phase 2 - In Progress  
**Next**: Complete field additions and testing

