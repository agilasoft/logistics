# Lalamove Integration Development Plan

## Executive Summary

This document outlines the development plan for integrating Lalamove API (v3) with multiple modules in the Logistics application for **last-mile delivery** services. The integration will enable users to create delivery orders on Lalamove directly from Transport Orders/Jobs, Warehouse Jobs, Air Shipments, and Sea Shipments, track order status, and manage deliveries seamlessly within the system.

**Integration Type**: Third-party API Integration  
**API Version**: Lalamove API v3  
**Target Modules**: Transport, Warehousing, Air Freight, Sea Freight  
**Primary Doctypes**: 
- **Transport**: Transport Order, Transport Job, Transport Leg
- **Warehousing**: Warehouse Job
- **Air Freight**: Air Shipment, Air Booking
- **Sea Freight**: Sea Shipment, Sea Booking

---

## 1. Objectives

### 1.1 Primary Goals
- Enable creation of Lalamove delivery orders from multiple logistics modules:
  - **Transport Module**: Transport Orders/Jobs for direct deliveries
  - **Warehousing Module**: Warehouse Jobs for outbound warehouse deliveries
  - **Air Freight Module**: Air Shipments for last-mile delivery after air cargo arrival
  - **Sea Freight Module**: Sea Shipments for last-mile delivery after sea cargo arrival
- Real-time synchronization of order status between Lalamove and all integrated modules
- Automatic price quotation retrieval from Lalamove
- Support for multiple delivery stops (up to 15 drop-offs)
- Webhook integration for status updates across all modules
- Support for both immediate and scheduled deliveries
- Unified last-mile delivery management across all logistics operations

### 1.2 Success Criteria
- Users can create Lalamove orders from all supported doctypes with minimal clicks
- Order status updates are reflected in real-time across all modules
- Quotation prices are accurate and valid for 5 minutes
- All Lalamove order events are logged and traceable
- Integration supports all Lalamove service types and special requests
- Last-mile delivery seamlessly integrated into existing logistics workflows

---

## 2. Architecture Overview

### 2.1 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Logistics Application                            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Lalamove Integration (Logistics Level)         │   │
│  │  ┌────────────────────────────────────────────────────┐     │   │
│  │  │  Lalamove Service (Unified, Module-Independent)   │     │   │
│  │  └────────────────────┬───────────────────────────────┘     │   │
│  └───────────────────────┼──────────────────────────────────────┘   │
│                          │                                          │
│  ┌───────────────────────┼──────────────────────────────────────┐   │
│  │                       │                                      │   │
│  │  ┌──────────────────┐│┌──────────────────┐                 │   │
│  │  │ Transport Module │││ Warehousing      │                 │   │
│  │  │ (Optional)       │││ (Optional)       │                 │   │
│  │  │ • Transport Order│││ • Warehouse Job │                 │   │
│  │  │ • Transport Job  │││                 │                 │   │
│  │  │ • Transport Leg  │││                 │                 │   │
│  │  └────────┬─────────┘│└────────┬─────────┘                 │   │
│  │           │          │         │                            │   │
│  │  ┌────────▼─────────┐│┌────────▼─────────┐                 │   │
│  │  │ Air Freight      │││ Sea Freight      │                 │   │
│  │  │ (Optional)       │││ (Optional)       │                 │   │
│  │  │ • Air Shipment   │││ • Sea Shipment   │                 │   │
│  │  │ • Air Booking    │││ • Sea Booking    │                 │   │
│  │  └──────────────────┘│└──────────────────┘                 │   │
│  │                      │                                      │   │
│  └──────────────────────┼──────────────────────────────────────┘   │
│                         │                                          │
└─────────────────────────┼──────────────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         │
┌─────────────────────────▼──────────────────────────────────────────┐
│                    Lalamove API v3                                   │
│  • Quotations API                                                    │
│  • Orders API                                                        │
│  • Order Details API                                                 │
│  • Driver Details API                                                │
│  • Webhook Endpoints                                                 │
└──────────────────────────────────────────────────────────────────────┘

Note: Lalamove is at Logistics level - works independently of any sub-module
```

### 2.2 Component Structure

```
logistics/
├── lalamove/                       # Lalamove integration module
│   ├── __init__.py
│   ├── client.py                    # Lalamove API client
│   ├── service.py                   # Business logic service
│   ├── mapper.py                    # Data mapping utilities
│   ├── webhook.py                   # Webhook handler
│   ├── exceptions.py                # Custom exceptions
│   └── utils.py                     # Helper utilities
├── doctype/
│   ├── lalamove_settings/            # Settings doctype
│   ├── lalamove_order/              # Lalamove order tracking
│   └── lalamove_quotation/           # Quotation cache
└── api/
    └── lalamove_api.py              # Public API endpoints
```

**Note**: Lalamove integration is at the Logistics module level, making it available to all sub-modules (Transport, Warehousing, Air Freight, Sea Freight) and independent of any specific module implementation.

---

## 3. Data Model Design

### 3.1 New Doctypes

#### 3.1.1 Lalamove Settings (Single DocType)
**Purpose**: Store Lalamove API credentials and configuration

**Fields**:
- `api_key` (Password) - Lalamove API Key
- `api_secret` (Password) - Lalamove API Secret
- `environment` (Select) - Sandbox/Production
- `market` (Data) - Market code (e.g., "HK_HKG", "SG_SIN")
- `webhook_url` (Data) - Webhook endpoint URL
- `webhook_secret` (Password) - Webhook secret for validation
- `auto_create_order` (Check) - Auto-create order on source document submit
- `default_service_type` (Select) - Default service type
- `enabled` (Check) - Enable/disable integration

#### 3.1.2 Lalamove Order (DocType)
**Purpose**: Track Lalamove orders linked to all logistics modules

**Fields**:
- `lalamove_order_id` (Data) - Lalamove order ID (19 digits)
- `quotation_id` (Link) - Reference to Lalamove Quotation
- `source_doctype` (Select) - Source doctype (Transport Order, Transport Job, Transport Leg, Warehouse Job, Air Shipment, Air Booking, Sea Shipment, Sea Booking)
- `source_docname` (Dynamic Link) - Source document name
- `transport_order` (Link) - Linked Transport Order (if applicable)
- `transport_job` (Link) - Linked Transport Job (if applicable)
- `transport_leg` (Link) - Linked Transport Leg (if applicable)
- `warehouse_job` (Link) - Linked Warehouse Job (if applicable)
- `air_shipment` (Link) - Linked Air Shipment (if applicable)
- `air_booking` (Link) - Linked Air Booking (if applicable)
- `sea_shipment` (Link) - Linked Sea Shipment (if applicable)
- `sea_booking` (Link) - Linked Sea Booking (if applicable)
- `status` (Select) - Order status (synced from Lalamove)
- `driver_name` (Data) - Driver name
- `driver_phone` (Data) - Driver phone
- `driver_photo` (Data) - Driver photo URL
- `vehicle_type` (Data) - Vehicle type
- `vehicle_number` (Data) - Vehicle number
- `price` (Currency) - Order price
- `currency` (Link) - Currency
- `distance` (Float) - Distance in km
- `scheduled_at` (Datetime) - Scheduled delivery time
- `completed_at` (Datetime) - Completion time
- `proof_of_delivery` (Attach) - POD image
- `metadata` (JSON) - Additional metadata
- `error_message` (Text) - Error details if any

**Indexes**:
- `lalamove_order_id` (Unique)
- `transport_order`
- `transport_job`
- `status`

#### 3.1.3 Lalamove Quotation (DocType)
**Purpose**: Cache quotations for reuse across all modules

**Fields**:
- `quotation_id` (Data) - Lalamove quotation ID (UUID)
- `source_doctype` (Select) - Source doctype
- `source_docname` (Dynamic Link) - Source document name
- `transport_order` (Link) - Related Transport Order (if applicable)
- `transport_job` (Link) - Related Transport Job (if applicable)
- `transport_leg` (Link) - Related Transport Leg (if applicable)
- `warehouse_job` (Link) - Related Warehouse Job (if applicable)
- `air_shipment` (Link) - Related Air Shipment (if applicable)
- `air_booking` (Link) - Related Air Booking (if applicable)
- `sea_shipment` (Link) - Related Sea Shipment (if applicable)
- `sea_booking` (Link) - Related Sea Booking (if applicable)
- `price` (Currency) - Quoted price
- `currency` (Link) - Currency
- `service_type` (Data) - Service type
- `expires_at` (Datetime) - Quotation expiry
- `price_breakdown` (JSON) - Price breakdown details
- `stops` (JSON) - Delivery stops
- `item` (JSON) - Item information
- `distance` (Float) - Distance
- `valid` (Check) - Is quotation still valid

**Indexes**:
- `quotation_id` (Unique)
- `transport_order`
- `transport_job`
- `expires_at`

### 3.2 Field Additions to Existing Doctypes

#### 3.2.1 Transport Module
**Transport Order**:
- `use_lalamove` (Check) - Enable Lalamove integration
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation

**Transport Job**:
- `use_lalamove` (Check) - Enable Lalamove integration
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation

**Transport Leg**:
- `use_lalamove` (Check) - Enable Lalamove integration
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation

#### 3.2.2 Warehousing Module
**Warehouse Job**:
- `use_lalamove` (Check) - Enable Lalamove integration for outbound delivery
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation
- `delivery_address` (Link) - Delivery address for last-mile (if not in customer)
- `delivery_contact` (Link) - Delivery contact person

#### 3.2.3 Air Freight Module
**Air Shipment**:
- `use_lalamove` (Check) - Enable Lalamove integration for last-mile delivery
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation
- `last_mile_delivery_required` (Check) - Flag for last-mile delivery requirement
- `last_mile_delivery_date` (Date) - Scheduled last-mile delivery date

**Air Booking**:
- `use_lalamove` (Check) - Enable Lalamove integration
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation

#### 3.2.4 Sea Freight Module
**Sea Shipment**:
- `use_lalamove` (Check) - Enable Lalamove integration for last-mile delivery
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation
- `last_mile_delivery_required` (Check) - Flag for last-mile delivery requirement
- `last_mile_delivery_date` (Date) - Scheduled last-mile delivery date

**Sea Booking**:
- `use_lalamove` (Check) - Enable Lalamove integration
- `lalamove_order` (Link) - Reference to Lalamove Order
- `lalamove_quotation` (Link) - Reference to Lalamove Quotation

---

## 4. API Integration Details

### 4.1 Lalamove API Endpoints to Integrate

#### 4.1.1 Get Quotation
- **Endpoint**: `POST /v3/quotations`
- **Purpose**: Get delivery price quotation
- **Use Case**: Before creating order, show price to user
- **Rate Limit**: 30/min (Sandbox), 100/min (Production)

#### 4.1.2 Get Quotation Details
- **Endpoint**: `GET /v3/quotations/{quotationId}`
- **Purpose**: Retrieve detailed quotation information
- **Use Case**: Display price breakdown, distance, etc.

#### 4.1.3 Place Order
- **Endpoint**: `POST /v3/orders`
- **Purpose**: Create delivery order on Lalamove
- **Use Case**: Create order from Transport Order/Job
- **Rate Limit**: 30/min (Sandbox), 100/min (Production)

#### 4.1.4 Get Order Details
- **Endpoint**: `GET /v3/orders/{orderId}`
- **Purpose**: Retrieve order status and details
- **Use Case**: Track order progress, get driver info
- **Rate Limit**: 50/min (Sandbox), 300/min (Production)

#### 4.1.5 Get Driver Details
- **Endpoint**: `GET /v3/drivers/{driverId}`
- **Purpose**: Get driver information
- **Use Case**: Display driver details in UI

#### 4.1.6 Cancel Order
- **Endpoint**: `PUT /v3/orders/{orderId}/cancel`
- **Purpose**: Cancel an active order
- **Use Case**: Cancel order from Transport Order/Job

#### 4.1.7 Change Driver
- **Endpoint**: `PUT /v3/orders/{orderId}/drivers`
- **Purpose**: Request driver change
- **Use Case**: Change driver if issues occur

#### 4.1.8 Add Priority Fee
- **Endpoint**: `PUT /v3/orders/{orderId}/priority`
- **Purpose**: Add priority fee to expedite delivery
- **Use Case**: Urgent delivery requests

#### 4.1.9 Edit Order
- **Endpoint**: `PUT /v3/orders/{orderId}`
- **Purpose**: Edit order details (limited fields)
- **Use Case**: Update delivery instructions, contact info

#### 4.1.10 Get City Info
- **Endpoint**: `GET /v3/cities`
- **Purpose**: Get available cities and service types
- **Use Case**: Validate city and service type availability

### 4.2 Webhook Integration

#### 4.2.1 Webhook Events to Handle
- `ORDER_STATUS_CHANGED` - Order status update
- `DRIVER_ASSIGNED` - Driver assigned to order
- `ORDER_AMOUNT_CHANGED` - Order amount changed
- `ORDER_REPLACED` - Order replaced by customer service
- `WALLET_BALANCE_CHANGED` - Wallet balance update
- `ORDER_EDITED` - Order edited

#### 4.2.2 Webhook Endpoint
- **URL**: `/api/method/logistics.lalamove.webhook.handle_webhook`
- **Method**: POST
- **Authentication**: Validate webhook secret
- **Payload**: Lalamove webhook payload

---

## 5. Module-Specific Use Cases

### 5.1 Transport Module Use Cases

**Use Case 1: Direct Delivery from Transport Order**
- User creates Transport Order with delivery addresses
- User requests Lalamove quotation
- User creates Lalamove order for last-mile delivery
- Track delivery status in real-time
- Update Transport Order status upon completion

**Use Case 2: Multi-Stop Delivery**
- Transport Job with multiple legs
- Create separate Lalamove orders for each leg
- Or create single order with multiple stops (up to 15)
- Track all deliveries from Transport Job

**Use Case 3: Scheduled Delivery**
- Transport Order with scheduled date
- Create scheduled Lalamove order
- Automatic order creation on scheduled date

### 5.2 Warehousing Module Use Cases

**Use Case 1: Outbound Warehouse Delivery**
- Warehouse Job completed (items ready for shipment)
- User creates Lalamove order for customer delivery
- Pick-up from warehouse address
- Delivery to customer address
- Track delivery status

**Use Case 2: Multiple Customer Deliveries**
- Warehouse Job with multiple customer orders
- Create separate Lalamove orders per customer
- Or create single order with multiple stops
- Track all deliveries from Warehouse Job

**Use Case 3: Express Warehouse Delivery**
- Urgent outbound delivery
- Use priority fee for faster delivery
- Real-time tracking

### 5.3 Air Freight Module Use Cases

**Use Case 1: Last-Mile Delivery After Air Arrival**
- Air Shipment arrives at destination airport/CFS
- Cargo cleared from customs
- User creates Lalamove order for last-mile delivery
- Pick-up from airport/CFS
- Delivery to consignee address
- Track delivery status

**Use Case 2: Time-Sensitive Air Cargo**
- Express air freight delivery
- Scheduled delivery based on ETA
- Priority handling for urgent shipments

**Use Case 3: Multiple Consignee Delivery**
- Air Shipment with multiple consignees
- Create separate Lalamove orders per consignee
- Track all deliveries from Air Shipment

### 5.4 Sea Freight Module Use Cases

**Use Case 1: Last-Mile Delivery After Sea Arrival**
- Sea Shipment arrives at destination port/CFS
- Container/cargo cleared from customs
- User creates Lalamove order for last-mile delivery
- Pick-up from port/CFS
- Delivery to consignee address
- Track delivery status

**Use Case 2: Container Delivery**
- FCL shipment requiring container delivery
- Use TRUCK service type
- Handle large/heavy cargo
- Special handling for containers

**Use Case 3: LCL Package Delivery**
- LCL shipment with individual packages
- Create Lalamove orders for package delivery
- Multiple deliveries from single Sea Shipment

### 5.5 Cross-Module Scenarios

**Scenario 1: Multi-Modal Logistics**
- Sea Shipment → Warehouse → Lalamove Delivery
- Air Shipment → Warehouse → Lalamove Delivery
- Track entire logistics chain

**Scenario 2: Consolidation Delivery**
- Multiple shipments consolidated
- Single Lalamove order for consolidated delivery
- Track from source shipments

---

## 6. Data Mapping

### 5.1 Multi-Module → Lalamove Quotation Request

#### 5.1.1 Transport Module → Lalamove

| Transport Module Field | Lalamove API Field | Notes |
|------------------------|-------------------|-------|
| `legs[0].pick_address` | `stops[0].coordinates` | Convert address to lat/lng |
| `legs[0].drop_address` | `stops[1].coordinates` | Convert address to lat/lng |
| `legs[0].pick_address` | `stops[0].address` | Full address string |
| `legs[0].drop_address` | `stops[1].address` | Full address string |
| `vehicle_type` | `serviceType` | Map to Lalamove service types |
| `scheduled_date` | `scheduleAt` | ISO 8601 format |
| `packages` | `item` | Map package details |
| `hazardous` | `specialRequests` | Add "HAZMAT" if true |
| `refrigeration` | `specialRequests` | Add "REEFER" if true |
| `customer` | `contact.name` | Customer name |
| `customer` (phone) | `contact.phone` | Customer phone |

#### 5.1.2 Warehousing Module → Lalamove

| Warehouse Job Field | Lalamove API Field | Notes |
|---------------------|-------------------|-------|
| Warehouse address (from settings) | `stops[0].coordinates` | Pick-up from warehouse |
| `delivery_address` or customer address | `stops[1].coordinates` | Delivery to customer |
| Warehouse address | `stops[0].address` | Full warehouse address |
| `delivery_address` or customer address | `stops[1].address` | Full delivery address |
| Package weight/volume | `serviceType` | Determine service type from weight/volume |
| `job_open_date` or current date | `scheduleAt` | ISO 8601 format |
| `items` (total weight/volume) | `item` | Map item details to package |
| `customer` | `contact.name` | Customer name |
| `delivery_contact` or customer contact | `contact.phone` | Delivery contact phone |

#### 5.1.3 Air Freight Module → Lalamove

| Air Shipment Field | Lalamove API Field | Notes |
|-------------------|-------------------|-------|
| Airport/CFS address (destination) | `stops[0].coordinates` | Pick-up from airport/CFS |
| `consignee_address` | `stops[1].coordinates` | Delivery to consignee |
| Airport/CFS address | `stops[0].address` | Full pick-up address |
| `consignee_address` | `stops[1].address` | Full consignee address |
| Package weight/volume | `serviceType` | Determine service type |
| `last_mile_delivery_date` or `eta` | `scheduleAt` | ISO 8601 format |
| `packages` | `item` | Map package details |
| `consignee` | `contact.name` | Consignee name |
| `consignee_contact` | `contact.phone` | Consignee phone |
| Dangerous goods flag | `specialRequests` | Add "HAZMAT" if applicable |

#### 5.1.4 Sea Freight Module → Lalamove

| Sea Shipment Field | Lalamove API Field | Notes |
|-------------------|-------------------|-------|
| Port/CFS address (destination) | `stops[0].coordinates` | Pick-up from port/CFS |
| `consignee_address` | `stops[1].coordinates` | Delivery to consignee |
| Port/CFS address | `stops[0].address` | Full pick-up address |
| `consignee_address` | `stops[1].address` | Full consignee address |
| Container/package weight | `serviceType` | Determine service type (usually TRUCK for containers) |
| `last_mile_delivery_date` or `eta` | `scheduleAt` | ISO 8601 format |
| `packages` or container details | `item` | Map package/container details |
| `consignee` | `contact.name` | Consignee name |
| `consignee_contact` | `contact.phone` | Consignee phone |
| Dangerous goods flag | `specialRequests` | Add "HAZMAT" if applicable |

### 5.2 Lalamove Order → All Modules

| Lalamove API Field | Module Field (All) | Notes |
|-------------------|-------------------|-------|
| `orderId` | `lalamove_order_id` | Store in Lalamove Order |
| `quotationId` | `quotation_id` | Link to Lalamove Quotation |
| `status` | `status` | Map status values (see 5.4) |
| `driver.name` | `driver_name` | Driver information |
| `driver.phone` | `driver_phone` | Driver contact |
| `driver.photo` | `driver_photo` | Driver photo URL |
| `price` | `price` | Order price |
| `distance` | `distance` | Distance in km |
| `scheduleAt` | `scheduled_at` | Scheduled time |
| `completedAt` | `completed_at` | Completion time |

**Status Updates**:
- Transport Order/Job: Update status based on Lalamove order status
- Warehouse Job: Update delivery status
- Air Shipment: Update last-mile delivery status
- Sea Shipment: Update last-mile delivery status

### 5.3 Service Type Mapping

#### 5.3.1 Transport Module
| Transport Module Vehicle Type | Lalamove Service Type | Notes |
|------------------------------|---------------------|-------|
| Motorcycle | MOTORCYCLE | Default for small packages |
| Van | VAN | Medium packages |
| Truck | TRUCK | Large packages |
| Container Truck | TRUCK | Container transport |

#### 5.3.2 Warehousing Module
| Package Weight/Volume | Lalamove Service Type | Notes |
|----------------------|---------------------|-------|
| < 5 kg, < 0.1 m³ | MOTORCYCLE | Small packages |
| 5-50 kg, 0.1-1 m³ | VAN | Medium packages |
| > 50 kg, > 1 m³ | TRUCK | Large packages |

#### 5.3.3 Air Freight Module
| Package Weight/Volume | Lalamove Service Type | Notes |
|----------------------|---------------------|-------|
| < 5 kg, < 0.1 m³ | MOTORCYCLE | Small air cargo |
| 5-50 kg, 0.1-1 m³ | VAN | Medium air cargo |
| > 50 kg, > 1 m³ | TRUCK | Large air cargo |

#### 5.3.4 Sea Freight Module
| Container/Package Type | Lalamove Service Type | Notes |
|----------------------|---------------------|-------|
| Small packages | MOTORCYCLE | Individual packages |
| LCL shipments | VAN | Less than container load |
| FCL shipments | TRUCK | Full container load |
| Containers | TRUCK | Container delivery |

### 5.4 Status Mapping (All Modules)

| Lalamove Status | Module Status | Notes |
|----------------|--------------|-------|
| ASSIGNING_DRIVER | Pending/Submitted | Waiting for driver |
| ON_GOING | In Progress | Driver on the way |
| PICKED_UP | In Progress | Package picked up |
| COMPLETED | Completed/Delivered | Delivery completed |
| CANCELLED | Cancelled | Order cancelled |
| EXPIRED | Cancelled | Order expired |

**Module-Specific Status Updates**:
- **Transport Order/Job**: Map to Transport Job status (Draft, Submitted, In Progress, Completed, Cancelled)
- **Warehouse Job**: Update delivery status field
- **Air Shipment**: Update last-mile delivery status
- **Sea Shipment**: Update last-mile delivery status

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Goal**: Set up basic infrastructure and API client

**Tasks**:
1. Create Lalamove Settings doctype
2. Create Lalamove Order doctype (with multi-module support)
3. Create Lalamove Quotation doctype (with multi-module support)
4. Implement base API client with authentication
5. Implement signature generation
6. Add fields to all target doctypes:
   - Transport Order/Job/Leg
   - Warehouse Job
   - Air Shipment/Air Booking
   - Sea Shipment/Sea Booking
7. Create mapper utilities for data transformation (all modules)

**Deliverables**:
- Settings doctype functional
- API client can authenticate and make basic calls
- Data models ready

### Phase 2: Quotation Integration (Week 2-3)
**Goal**: Enable quotation retrieval and caching

**Tasks**:
1. Implement Get Quotation API
2. Implement Get Quotation Details API
3. Create quotation caching mechanism
4. Add UI buttons to get quotation from all supported doctypes:
   - Transport Order/Job
   - Warehouse Job
   - Air Shipment/Air Booking
   - Sea Shipment/Sea Booking
5. Display quotation details in UI
6. Handle quotation expiry (5 minutes)
7. Implement module-specific address extraction logic

**Deliverables**:
- Users can get quotations from Transport Order/Job
- Quotations are cached and displayed
- Quotation validity is tracked

### Phase 3: Order Creation (Week 3-4)
**Goal**: Enable order creation on Lalamove

**Tasks**:
1. Implement Place Order API
2. Create unified order creation workflow (all modules)
3. Add UI for order creation in all modules
4. Handle order creation errors
5. Link Lalamove orders to all source doctypes:
   - Transport Orders/Jobs/Legs
   - Warehouse Jobs
   - Air Shipments/Air Bookings
   - Sea Shipments/Sea Bookings
6. Store order details in Lalamove Order doctype
7. Implement module-specific order creation logic

**Deliverables**:
- Users can create Lalamove orders from Transport Order/Job
- Orders are linked and tracked
- Error handling in place

### Phase 4: Order Management (Week 4-5)
**Goal**: Enable order tracking and management

**Tasks**:
1. Implement Get Order Details API
2. Implement Get Driver Details API
3. Implement Cancel Order API
4. Implement Change Driver API
5. Implement Add Priority Fee API
6. Implement Edit Order API
7. Add UI for order management actions
8. Create order status sync mechanism

**Deliverables**:
- Users can view order details and status
- Users can cancel orders
- Users can change drivers
- Order status is displayed in UI

### Phase 5: Webhook Integration (Week 5-6)
**Goal**: Real-time status updates via webhooks

**Tasks**:
1. Create webhook endpoint
2. Implement webhook signature validation
3. Handle ORDER_STATUS_CHANGED event
4. Handle DRIVER_ASSIGNED event
5. Handle ORDER_AMOUNT_CHANGED event
6. Handle ORDER_REPLACED event
7. Handle ORDER_EDITED event
8. Update status from webhooks for all modules:
   - Transport Order/Job/Leg
   - Warehouse Job
   - Air Shipment/Air Booking
   - Sea Shipment/Sea Booking
9. Test webhook reliability across all modules

**Deliverables**:
- Webhook endpoint functional
- Status updates sync in real-time
- All webhook events handled

### Phase 6: Advanced Features (Week 6-7)
**Goal**: Additional features and optimizations

**Tasks**:
1. Implement Get City Info API
2. Add city/service type validation
3. Implement route optimization support
4. Add proof of delivery retrieval
5. Create order history and audit trail
6. Add error logging and monitoring
7. Performance optimization

**Deliverables**:
- City validation working
- POD retrieval functional
- Comprehensive logging

### Phase 7: Testing & Documentation (Week 7-8)
**Goal**: Comprehensive testing and documentation

**Tasks**:
1. Unit tests for API client
2. Integration tests for workflows
3. Webhook testing
4. Error scenario testing
5. User acceptance testing
6. API documentation
7. User guide
8. Developer documentation

**Deliverables**:
- Test suite complete
- Documentation complete
- Ready for production

---

## 8. Technical Implementation Details

### 7.1 API Client Implementation

```python
# logistics/lalamove/client.py

class LalamoveAPIClient:
    """
    Lalamove API v3 Client
    
    Handles authentication, request signing, and API calls
    """
    
    def __init__(self, api_key: str, api_secret: str, environment: str = "sandbox"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self._get_base_url(environment)
        self.timezone = "UTC"
    
    def _get_base_url(self, environment: str) -> str:
        if environment == "production":
            return "https://rest.lalamove.com/v3"
        return "https://rest.sandbox.lalamove.com/v3"
    
    def _generate_signature(self, method: str, path: str, body: str, timestamp: str) -> str:
        """Generate HMAC signature for request authentication"""
        # Implementation per Lalamove docs
        pass
    
    def get_quotation(self, quotation_request: dict) -> dict:
        """Get delivery quotation"""
        pass
    
    def place_order(self, quotation_id: str, order_request: dict) -> dict:
        """Place delivery order"""
        pass
    
    def get_order_details(self, order_id: str) -> dict:
        """Get order details"""
        pass
    
    def cancel_order(self, order_id: str) -> dict:
        """Cancel order"""
        pass
```

### 7.2 Service Layer

```python
# logistics/lalamove/service.py

class LalamoveService:
    """
    Business logic service for Lalamove integration
    Supports all logistics modules: Transport, Warehousing, Air Freight, Sea Freight
    """
    
    def __init__(self):
        self.client = self._get_client()
        self.mapper = LalamoveMapper()
    
    def get_quotation(self, doctype: str, docname: str) -> dict:
        """Get quotation for any supported doctype"""
        pass
    
    def create_order(self, doctype: str, docname: str, quotation_id: str = None) -> dict:
        """Create Lalamove order from any supported doctype"""
        pass
    
    def sync_order_status(self, lalamove_order_id: str) -> dict:
        """Sync order status from Lalamove"""
        pass
    
    def get_quotation_for_transport_order(self, transport_order_name: str) -> dict:
        """Get quotation for a Transport Order (deprecated - use get_quotation)"""
        return self.get_quotation("Transport Order", transport_order_name)
    
    def create_order_from_transport_order(self, transport_order_name: str) -> dict:
        """Create Lalamove order from Transport Order (deprecated - use create_order)"""
        return self.create_order("Transport Order", transport_order_name)
```

### 7.3 Webhook Handler

```python
# logistics/lalamove/webhook.py

@frappe.whitelist(allow_guest=True)
def handle_webhook():
    """
    Handle incoming webhook from Lalamove
    Updates status for all supported doctypes across all modules
    """
    # Validate signature
    # Process webhook event
    # Update source document status (Transport, Warehousing, Air Freight, Sea Freight)
    pass
```

### 7.4 API Endpoints

```python
# logistics/api/lalamove_api.py

@frappe.whitelist()
def get_lalamove_quotation(doctype: str, docname: str):
    """
    Get Lalamove quotation for any supported doctype
    Supports: Transport Order/Job/Leg, Warehouse Job, Air Shipment/Booking, Sea Shipment/Booking
    """
    pass

@frappe.whitelist()
def create_lalamove_order(doctype: str, docname: str, quotation_id: str = None):
    """
    Create Lalamove order from any supported doctype
    Supports: Transport Order/Job/Leg, Warehouse Job, Air Shipment/Booking, Sea Shipment/Booking
    """
    pass

@frappe.whitelist()
def get_lalamove_order_status(lalamove_order_id: str):
    """Get current order status from Lalamove"""
    pass

@frappe.whitelist()
def cancel_lalamove_order(lalamove_order_id: str):
    """Cancel Lalamove order"""
    pass

@frappe.whitelist()
def sync_lalamove_order_status(lalamove_order_id: str):
    """Manually sync order status from Lalamove"""
    pass
```

---

## 9. UI/UX Enhancements

### 9.1 Transport Module Forms
**Transport Order Form**:
- Add "Lalamove Integration" section
- Add "Get Quotation" button
- Display quotation details (price, distance, validity)
- Add "Create Order" button (enabled after quotation)
- Display order status and driver info if order exists
- Add "Cancel Order" button for active orders

**Transport Job Form**:
- Similar UI enhancements as Transport Order
- Show Lalamove order status per leg if applicable
- Multi-leg delivery options

### 9.2 Warehousing Module Forms
**Warehouse Job Form**:
- Add "Last-Mile Delivery" section
- Add "Get Lalamove Quotation" button
- Display delivery address and contact
- Add "Create Delivery Order" button
- Show delivery status and driver info
- Track delivery completion

### 9.3 Air Freight Module Forms
**Air Shipment Form**:
- Add "Last-Mile Delivery" section
- Add "Get Lalamove Quotation" button (enabled after customs clearance)
- Display consignee address and contact
- Add "Create Delivery Order" button
- Show delivery status and driver info
- Link to arrival milestone

**Air Booking Form**:
- Similar UI enhancements
- Pre-configure delivery for future shipments

### 9.4 Sea Freight Module Forms
**Sea Shipment Form**:
- Add "Last-Mile Delivery" section
- Add "Get Lalamove Quotation" button (enabled after customs clearance)
- Display consignee address and contact
- Add "Create Delivery Order" button
- Show delivery status and driver info
- Handle container vs package delivery

**Sea Booking Form**:
- Similar UI enhancements
- Pre-configure delivery for future shipments

### 9.5 Lalamove Order Dashboard
- List view of all Lalamove orders across all modules
- Filter by:
  - Status, date
  - Source module (Transport, Warehousing, Air Freight, Sea Freight)
  - Source doctype
  - Customer/Consignee
- Quick actions: View Details, Cancel, Change Driver
- Cross-module order tracking

### 9.6 Status Indicators
- Color-coded status badges
- Real-time status updates across all modules
- Driver information display
- Proof of delivery viewer
- Module-specific status indicators

---

## 10. Error Handling & Logging

### 9.1 Error Categories
- **Authentication Errors**: Invalid API credentials
- **Validation Errors**: Invalid request data
- **Rate Limit Errors**: Too many requests
- **Network Errors**: Connection issues
- **Business Logic Errors**: Order already exists, quotation expired, etc.

### 9.2 Error Handling Strategy
- Log all errors with context
- Display user-friendly error messages
- Retry mechanism for transient errors
- Queue failed requests for retry
- Alert administrators for critical errors

### 9.3 Logging
- Log all API requests/responses
- Log webhook events
- Log order status changes
- Log errors with stack traces
- Maintain audit trail

---

## 11. Testing Strategy

### 10.1 Unit Tests
- API client methods
- Data mapping functions
- Service layer methods
- Webhook handler

### 10.2 Integration Tests
- End-to-end order creation workflow
- Quotation retrieval and caching
- Status synchronization
- Webhook processing

### 10.3 Test Scenarios
- Successful order creation
- Quotation expiry handling
- Order cancellation
- Driver assignment
- Status updates
- Error scenarios
- Rate limiting
- Network failures

### 10.4 Sandbox Testing
- Test all features in Lalamove sandbox
- Verify webhook delivery
- Test error scenarios
- Performance testing

---

## 12. Security Considerations

### 11.1 API Credentials
- Store credentials in Password fields (encrypted)
- Never log credentials
- Rotate credentials periodically
- Use environment-specific credentials

### 11.2 Webhook Security
- Validate webhook signatures
- Use HTTPS for webhook endpoint
- Implement rate limiting
- Log all webhook attempts

### 11.3 Data Privacy
- Don't store sensitive customer data unnecessarily
- Encrypt sensitive data at rest
- Follow data retention policies
- Comply with GDPR/local regulations

---

## 13. Deployment Plan

### 12.1 Pre-Deployment
1. Configure Lalamove Settings in production
2. Set up webhook URL in Lalamove Partner Portal
3. Test webhook endpoint accessibility
4. Verify API credentials
5. Set up monitoring and alerts

### 12.2 Deployment Steps
1. Deploy code to production
2. Run migrations (create doctypes, add fields)
3. Configure Lalamove Settings
4. Test with a single order
5. Monitor for errors
6. Gradual rollout

### 12.3 Post-Deployment
1. Monitor error logs
2. Check webhook delivery
3. Verify order creation success rate
4. Gather user feedback
5. Address issues promptly

---

## 14. Maintenance & Support

### 14.1 Monitoring
- API call success rate
- Webhook delivery rate
- Order creation success rate
- Error rates by type
- Response times

### 14.2 Regular Tasks
- Review error logs weekly
- Check Lalamove API status
- Update documentation as needed
- Review and optimize performance
- Update API client for new features

### 14.3 Support Contacts
- Lalamove Partner Support: partner.support@lalamove.com
- Internal support team contacts

---

## 15. Future Enhancements

### 14.1 Potential Features
- Bulk order creation
- Order scheduling optimization
- Multi-market support
- Advanced analytics and reporting
- Integration with other delivery providers
- Mobile app integration

### 14.2 API Updates
- Monitor Lalamove API changelog
- Plan for API version updates
- Implement new features as available

---

## 16. Dependencies

### 16.1 External Dependencies
- Lalamove API v3 (external service)
- Internet connectivity
- Valid Lalamove account and API credentials

### 16.2 Internal Dependencies
- Frappe Framework
- Address management system (for address to coordinates conversion)
- Customer management (for customer/consignee information)
- **Module Dependencies**: 
  - Transport Module: Optional (Lalamove works independently)
  - Warehousing Module: Optional (if using warehouse deliveries)
  - Air Freight Module: Optional (if using air freight last-mile)
  - Sea Freight Module: Optional (if using sea freight last-mile)
  
**Note**: Lalamove integration is implemented at the Logistics module level and does not require any specific sub-module to be implemented. It can function with any combination of modules or even standalone if needed.

### 16.3 Python Libraries
- `requests` - HTTP client
- `hmac` - Signature generation
- `hashlib` - Hashing functions
- `datetime` - Date/time handling
- `json` - JSON processing

---

## 17. Risk Assessment

### 17.1 Technical Risks
- **API Changes**: Lalamove may update API (mitigation: version pinning, monitoring)
- **Rate Limiting**: Exceeding rate limits (mitigation: request queuing, caching)
- **Network Issues**: Connectivity problems (mitigation: retry logic, error handling)
- **Webhook Failures**: Webhook delivery issues (mitigation: polling fallback)

### 17.2 Business Risks
- **Service Availability**: Lalamove service downtime (mitigation: status monitoring, fallback)
- **Pricing Changes**: Price fluctuations (mitigation: quotation caching, user approval)
- **Order Failures**: Order creation failures (mitigation: error handling, user notifications)

---

## 18. Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: Foundation | 2 weeks | Infrastructure, API client |
| Phase 2: Quotation | 1 week | Quotation retrieval |
| Phase 3: Order Creation | 1 week | Order creation workflow |
| Phase 4: Order Management | 1 week | Order tracking & management |
| Phase 5: Webhooks | 1 week | Real-time status updates |
| Phase 6: Advanced Features | 1 week | Additional features |
| Phase 7: Testing & Docs | 1 week | Testing & documentation |
| **Total** | **8 weeks** | **Production-ready integration** |

---

## 19. Success Metrics

### 18.1 Technical Metrics
- API call success rate > 99%
- Webhook delivery rate > 95%
- Average response time < 2 seconds
- Error rate < 1%

### 18.2 Business Metrics
- Order creation success rate > 95%
- User adoption rate
- Time saved per order
- Customer satisfaction

---

## 20. Appendix

### 19.1 Lalamove API Documentation
- Official Docs: https://developers.lalamove.com/
- API Reference: https://developers.lalamove.com/
- Support: partner.support@lalamove.com

### 19.2 Key API Specifications
- **Base URL (Sandbox)**: `https://rest.sandbox.lalamove.com/v3`
- **Base URL (Production)**: `https://rest.lalamove.com/v3`
- **Authentication**: HMAC signature-based
- **Content-Type**: `application/json`
- **Timezone**: UTC

### 19.3 Rate Limits
- Get Quotation: 30/min (Sandbox), 100/min (Production)
- Place Order: 30/min (Sandbox), 100/min (Production)
- Get Order Details: 50/min (Sandbox), 300/min (Production)
- Other APIs: See Lalamove documentation

---

## 21. Approval & Sign-off

**Prepared by**: Development Team  
**Date**: [Current Date]  
**Version**: 1.0  
**Status**: Draft

**Reviewers**:
- [ ] Technical Lead
- [ ] Product Manager
- [ ] QA Lead
- [ ] Security Team

**Approvals**:
- [ ] Development Manager
- [ ] Product Owner
- [ ] CTO/Technical Director

---

*This document is a living document and should be updated as the integration progresses.*

