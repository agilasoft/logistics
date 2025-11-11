# Declaration DocType - Comprehensive Enhancements

## Summary

The Declaration doctype has been enhanced to comprehensively record all customs declaration data required for international trade operations.

## New Fields Added

### 1. **Parties Information Section**
- **Exporter/Shipper**: Link to Shipper master
- **Importer/Consignee**: Link to Consignee master
- **Customs Broker/Agent**: Link to Supplier (customs broker)
- **Notify Party**: Link to Customer (notify party for shipments)

### 2. **Transport Information Section**
- **Transport Mode**: Select (Sea, Air, Road, Rail, Courier, Post)
- **Port of Loading/Entry**: Link to UNLOCO (origin port)
- **Port of Discharge/Exit**: Link to UNLOCO (destination port)
- **Vessel/Flight/Vehicle Number**: Data field
- **Transport Document Number**: Data field (BL, AWB, CMR, etc.)
- **Transport Document Type**: Select (Bill of Lading, Air Waybill, CMR, Railway Bill, Courier Receipt, Other)
- **ETD (Expected Departure)**: Date field
- **ETA (Expected Arrival)**: Date field
- **Container Numbers**: Small Text (comma-separated list)

### 3. **Trade Information Section**
- **Incoterm**: Link to Incoterm master
- **Payment Terms**: Link to Payment Terms Template
- **Trade Agreement/Preference**: Data field (e.g., FTA, GSP)
- **Country of Origin**: Link to Country (at declaration level)
- **Country of Destination**: Link to Country (at declaration level)
- **Priority Level**: Select (Normal, Express, Urgent)

### 4. **Processing Information Section**
- **Submission Date**: Date field (auto-set on submission)
- **Submission Time**: Time field (auto-set on submission)
- **Approval Date**: Date field (read-only, auto-set on approval)
- **Rejection Date**: Date field (read-only, auto-set on rejection)
- **Rejection Reason**: Small Text (read-only)
- **Processing Officer**: Link to User
- **Expected Clearance Date**: Date field
- **Actual Clearance Date**: Date field (read-only)

### 5. **Financial Information Section**
- **Exchange Rate**: Float (if different from base currency)
- **Duty Amount**: Currency
- **Tax Amount**: Currency
- **Other Charges**: Currency
- **Total Payable**: Currency (read-only, auto-calculated)
- **Payment Status**: Select (Pending, Partially Paid, Paid, Overdue)

### 6. **Additional Information Section**
- **Marks and Numbers**: Long Text (shipping marks)
- **Special Instructions**: Long Text
- **Internal Notes**: Text Editor
- **External Reference Number**: Data field (reference from external systems)

## Automation Features

### Auto-Calculations
1. **Total Declaration Value**: Automatically calculated from commodities table
2. **Total Payable**: Automatically calculated from duty_amount + tax_amount + other_charges

### Auto-Date Updates
1. **Submission Date/Time**: Auto-set when status changes to "Submitted"
2. **Approval Date**: Auto-set when status changes to "Approved"
3. **Rejection Date**: Auto-set when status changes to "Rejected"

## Complete Field Structure

The Declaration now includes:

1. ✅ **Basic Information**: Customer, date, sales quote, customs authority, status
2. ✅ **Customs Details**: Declaration type, number, value, currency, exchange rate
3. ✅ **Parties Information**: Exporter, importer, broker, notify party
4. ✅ **Transport Information**: Mode, ports, vessel/flight, transport documents, ETD/ETA, containers
5. ✅ **Trade Information**: Incoterm, payment terms, trade agreements, countries, priority
6. ✅ **Processing Information**: Submission, approval, rejection dates and details
7. ✅ **Financial Information**: Duty, tax, charges, total payable, payment status
8. ✅ **Additional Information**: Marks, instructions, notes, references
9. ✅ **Commodities Tab**: Multiple commodities with full details
10. ✅ **Charges Tab**: Revenue and cost calculations
11. ✅ **Documents Tab**: Document attachments and verification
12. ✅ **Accounts Tab**: Company, branch, cost/profit centers, job costing
13. ✅ **Sustainability Tab**: Paper usage, carbon footprint tracking

## Integration Points

- Links to existing masters: Shipper, Consignee, UNLOCO (ports), Incoterm
- Compatible with sea freight and air freight modules
- Supports all transport modes
- Full integration with accounts and job costing

## Compliance Features

- Complete audit trail with submission/approval/rejection dates
- Document verification tracking
- Payment status tracking
- Processing officer assignment
- Expected vs actual clearance date tracking

The Declaration doctype is now comprehensive and ready to handle all customs declaration requirements for international trade operations.


