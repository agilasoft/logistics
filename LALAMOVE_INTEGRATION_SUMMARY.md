# Lalamove Integration - Quick Reference Summary

## Overview
Integration of Lalamove API v3 with **multiple logistics modules** for **last-mile delivery** services. Enables delivery order creation, tracking, and management from Transport, Warehousing, Air Freight, and Sea Freight modules.

**Integration Level**: Logistics Module (shared service, independent of sub-modules)  
**Availability**: Available to all modules, functional even if Transport module is not implemented

## Key Components

### New Doctypes
1. **Lalamove Settings** - API credentials and configuration
2. **Lalamove Order** - Track Lalamove orders linked to all modules (unified tracking)
3. **Lalamove Quotation** - Cache quotations for reuse across all modules

### Integration Points

**Transport Module**:
- **Transport Order** → Create Lalamove orders
- **Transport Job** → Create Lalamove orders
- **Transport Leg** → Individual leg delivery orders

**Warehousing Module**:
- **Warehouse Job** → Outbound warehouse deliveries to customers

**Air Freight Module**:
- **Air Shipment** → Last-mile delivery after air cargo arrival
- **Air Booking** → Pre-configure last-mile delivery

**Sea Freight Module**:
- **Sea Shipment** → Last-mile delivery after sea cargo arrival
- **Sea Booking** → Pre-configure last-mile delivery

## Core Features

### 1. Quotation Management
- Get delivery price quotations from all modules
- Cache quotations (5-minute validity)
- Display price breakdown and distance
- Module-specific address extraction

### 2. Order Creation
- Create orders from all supported doctypes:
  - Transport Orders/Jobs/Legs
  - Warehouse Jobs
  - Air Shipments/Bookings
  - Sea Shipments/Bookings
- Support multiple stops (up to 15 drop-offs)
- Immediate and scheduled deliveries
- Unified order creation workflow

### 3. Order Tracking
- Real-time status updates via webhooks across all modules
- Driver information display
- Proof of delivery retrieval
- Cross-module order dashboard

### 4. Order Management
- Cancel orders from any module
- Change drivers
- Add priority fees
- Edit order details
- Module-specific status updates

## Implementation Timeline

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1 | 2 weeks | Foundation & API Client |
| Phase 2 | 1 week | Quotation Integration |
| Phase 3 | 1 week | Order Creation |
| Phase 4 | 1 week | Order Management |
| Phase 5 | 1 week | Webhook Integration |
| Phase 6 | 1 week | Advanced Features |
| Phase 7 | 1 week | Testing & Documentation |
| **Total** | **8 weeks** | **Production Ready** |

## API Endpoints to Implement

1. `POST /v3/quotations` - Get quotation
2. `GET /v3/quotations/{quotationId}` - Get quotation details
3. `POST /v3/orders` - Place order
4. `GET /v3/orders/{orderId}` - Get order details
5. `GET /v3/drivers/{driverId}` - Get driver details
6. `PUT /v3/orders/{orderId}/cancel` - Cancel order
7. `PUT /v3/orders/{orderId}/drivers` - Change driver
8. `PUT /v3/orders/{orderId}/priority` - Add priority fee
9. `PUT /v3/orders/{orderId}` - Edit order
10. `GET /v3/cities` - Get city info

## Webhook Events

- `ORDER_STATUS_CHANGED` - Status updates
- `DRIVER_ASSIGNED` - Driver assignment
- `ORDER_AMOUNT_CHANGED` - Price changes
- `ORDER_REPLACED` - Order replacement
- `ORDER_EDITED` - Order edits

## Data Mapping Highlights

### All Modules → Lalamove
- **Address Extraction**:
  - Transport: From legs (pick/drop addresses)
  - Warehousing: Warehouse address → Customer address
  - Air Freight: Airport/CFS → Consignee address
  - Sea Freight: Port/CFS → Consignee address
- **Service Type**: Determined by weight/volume/vehicle type
- **Scheduled Date**: From module-specific date fields
- **Packages**: Mapped from module-specific package/container data
- **Special Requests**: Hazardous, refrigeration flags

### Lalamove → All Modules
- Order ID → lalamove_order_id (stored in Lalamove Order)
- Status → Module-specific status fields
- Driver Info → driver_name, driver_phone, driver_photo
- Price → price
- Distance → distance
- Updates reflected in source documents

## File Structure

```
logistics/
├── lalamove/               # Lalamove integration module (Logistics level)
│   ├── client.py           # API client
│   ├── service.py          # Business logic
│   ├── mapper.py           # Data mapping
│   ├── webhook.py          # Webhook handler
│   └── utils.py            # Helper utilities
├── doctype/
│   ├── lalamove_settings/
│   ├── lalamove_order/
│   └── lalamove_quotation/
└── api/
    └── lalamove_api.py     # Public endpoints
```

**Note**: Lalamove is at the Logistics module level, making it available to all sub-modules and independent of any specific module implementation.

## Key Technical Details

- **Module Level**: Logistics (shared service, not Transport-specific)
- **Webhook Endpoint**: `/api/method/logistics.lalamove.webhook.handle_webhook`
- **Import Path**: `logistics.lalamove.*` (not `logistics.transport.*`)
- **Authentication**: HMAC signature-based
- **Environment**: Sandbox & Production
- **Rate Limits**: Varies by endpoint (30-300/min)
- **Quotation Validity**: 5 minutes
- **Order ID Format**: 19 digits
- **Timezone**: UTC
- **Module Independence**: Works even if Transport module is not implemented

## Success Criteria

- ✅ Order creation from all supported modules
- ✅ Real-time status synchronization across all modules
- ✅ Accurate price quotations
- ✅ Webhook reliability > 95%
- ✅ Error handling and logging
- ✅ Unified last-mile delivery management
- ✅ Module-specific workflows maintained

## Next Steps

1. Review and approve development plan
2. Set up Lalamove sandbox account
3. Begin Phase 1 implementation
4. Configure development environment
5. Start API client development

## Resources

- **Full Plan**: `LALAMOVE_INTEGRATION_PLAN.md`
- **Lalamove Docs**: https://developers.lalamove.com/
- **Support**: partner.support@lalamove.com

---

*Last Updated: [Current Date]*

