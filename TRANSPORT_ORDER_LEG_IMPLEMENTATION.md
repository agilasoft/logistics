# Transport Order Leg Implementation Documentation

## Overview

The Transport Order Leg feature enables multi-leg transport orders by allowing users to define multiple pickup and drop-off locations within a single Transport Order. Each leg represents a segment of the transport journey, from one facility to another, with specific pick and drop modes, addresses, and transport requirements.

## Purpose and Use Cases

Transport Order Legs were implemented to support complex transport scenarios where:

- A single transport order requires multiple stops (e.g., pick up from multiple locations, deliver to multiple destinations)
- Different legs may have different vehicle types, transport job types, or scheduled dates
- Each leg may require different pick/drop modes (e.g., curbside, dock, warehouse)
- Legs need to be individually tracked and managed through the transport workflow

## Data Structure

### Transport Order Legs Child Table

The `Transport Order Legs` is a child table (`istable: 1`) that belongs to the `Transport Order` doctype. It contains the following key fields:

#### Location Fields
- **facility_type_from**: Link to DocType (Shipper, Consignee, Container Yard, Container Depot, Container Freight Station, Storage Facility, Sorting Hub, Truck Park, Transport Terminal)
- **facility_from**: Dynamic Link based on `facility_type_from`
- **facility_type_to**: Link to DocType (same options as `facility_type_from`)
- **facility_to**: Dynamic Link based on `facility_type_to`

#### Address Fields
- **pick_address**: Link to Address (auto-filled from facility's primary address)
- **pick_address_html**: Read-only text field displaying formatted address
- **drop_address**: Link to Address (auto-filled from facility's primary address)
- **drop_address_html**: Read-only text field displaying formatted address

#### Pick/Drop Mode Fields
- **pick_mode**: Link to Pick and Drop Mode (filtered to modes where `allow_in_pick = 1`)
- **drop_mode**: Link to Pick and Drop Mode (filtered to modes where `allow_in_drop = 1`)

#### Transport Details
- **scheduled_date**: Date field for leg-specific scheduling
- **vehicle_type**: Link to Vehicle Type
- **transport_job_type**: Select field (Container, Non-Container, Special, Oversized, Multimodal, Heavy Haul)

## Implementation Details

### 1. Doctype Definition

**File**: `logistics/transport/doctype/transport_order_legs/transport_order_legs.json`

- Created: 2025-09-10
- Type: Child Table (`istable: 1`)
- Editable Grid: Yes (`editable_grid: 1`)
- Grid Page Length: 50 rows

### 2. Python Implementation

**File**: `logistics/transport/doctype/transport_order_legs/transport_order_legs.py`

#### Key Methods

##### `validate()`
Automatically calls `auto_fill_addresses()` during validation to ensure addresses are populated from facility primary addresses.

##### `auto_fill_addresses()`
Auto-fills `pick_address` and `drop_address` based on facility primary addresses:
- First attempts to use facility-specific primary address fields (e.g., `shipper_primary_address`, `consignee_primary_address`)
- Falls back to querying Address records linked via Dynamic Links
- Prioritizes addresses marked as `is_primary_address` or `is_shipping_address`

##### `_get_primary_address(facility_type, facility_name)`
Helper method that retrieves the primary address for a given facility:
- Maps facility types to their primary address field names
- Handles facility types without dedicated primary address fields
- Returns the most appropriate address based on priority flags

#### Whitelisted API Methods

##### `get_addresses_for_facility(facility_type, facility_name)`
Returns all addresses linked to a facility via Dynamic Links. Used by frontend query filters to populate address dropdowns.

##### `get_primary_address(facility_type, facility_name)`
Returns the primary address for a facility. Used by frontend to auto-fill address fields when a facility is selected.

### 3. Frontend Implementation

**File**: `logistics/transport/doctype/transport_order/transport_order.js`

#### Child Table Event Handlers

The frontend implements several event handlers for the Transport Order Legs child table:

##### `legs_add`
- Auto-populates `vehicle_type` and `transport_job_type` from parent Transport Order when a new leg is added
- Only sets values if they're not already present in the leg

##### `transport_job_type`
- Clears `vehicle_type` when `transport_job_type` changes (to force re-selection with updated filters)

##### `vehicle_type`
- Validates vehicle type compatibility when changed

##### `facility_type_from` / `facility_from`
- Auto-fills pick address when facility is selected
- Clears pick address if facility is cleared
- Calls `auto_fill_pick_address()` which uses the `get_primary_address` API

##### `facility_type_to` / `facility_to`
- Auto-fills drop address when facility is selected
- Clears drop address if facility is cleared
- Calls `auto_fill_drop_address()` which uses the `get_primary_address` API

#### Address Auto-fill Functions

- `auto_fill_pick_address(frm, cdt, cdn)`: Fetches and sets primary address for pick location
- `auto_fill_drop_address(frm, cdt, cdn)`: Fetches and sets primary address for drop location
- `render_pick_address_html(frm, cdt, cdn)`: Renders formatted HTML for pick address
- `render_drop_address_html(frm, cdt, cdn)`: Renders formatted HTML for drop address

### 4. Integration with Transport Order

**File**: `logistics/transport/doctype/transport_order/transport_order.py`

#### Validation

##### `_validate_transport_legs()`
Called during `before_submit()` to ensure:
- At least one leg exists
- Each leg has required fields:
  - `facility_type_from`, `facility_from`
  - `facility_type_to`, `facility_to`
  - `vehicle_type`
  - `transport_job_type`
- If `scheduled_date` is set on a leg, it must be valid

##### `_validate_leg_facilities()`
Validates that:
- Pick and drop facilities cannot be the same unless different addresses are specified
- Pick and drop addresses cannot be the same

#### Template Integration

##### `action_get_leg_plan(docname, replace, save)`
Populates Transport Order legs from a selected Transport Template:
- Fetches legs from the template
- Maps template leg fields to Transport Order Legs
- Calculates `scheduled_date` based on `day_offset` from template
- Auto-fills `transport_job_type` from parent Transport Order
- Can replace existing legs or append to them

#### Transport Job Creation

##### `_create_and_attach_job_legs_from_order_legs()`
When creating a Transport Job from a Transport Order, this function:
1. Iterates through each Transport Order Leg
2. Validates `pick_mode` and `drop_mode` are valid Pick and Drop Mode records
3. Creates a new `Transport Leg` document for each order leg
4. Copies fields from order leg to transport leg:
   - Facility information (from/to)
   - Pick/drop modes and addresses
   - Vehicle type and transport job type
5. Links the Transport Leg to the Transport Job
6. Creates a denormalized entry in `Transport Job Legs` child table for quick viewing/filtering

**Key Field Mapping**:
```
Transport Order Leg → Transport Leg
- facility_type_from → facility_type_from
- facility_from → facility_from
- pick_mode → pick_mode (validated)
- pick_address → pick_address
- facility_type_to → facility_type_to
- facility_to → facility_to
- drop_mode → drop_mode (validated)
- drop_address → drop_address
- vehicle_type → vehicle_type
- transport_job_type → transport_job_type
- scheduled_date (from order) → date
```

## Key Features

### 1. Address Auto-fill
- Automatically populates pick and drop addresses from facility primary addresses
- Supports multiple facility types with different primary address field names
- Falls back to Dynamic Link-based address lookup for facility types without dedicated primary address fields

### 2. Pick/Drop Mode Support
- Links to Pick and Drop Mode records (not literal strings)
- Validates modes are appropriate for pick or drop operations
- Filters available modes based on `allow_in_pick` and `allow_in_drop` flags

### 3. Per-Leg Scheduling
- Each leg can have its own `scheduled_date`
- Defaults to parent Transport Order's `scheduled_date` if not specified
- Supports day offsets when populated from templates

### 4. Per-Leg Transport Requirements
- Each leg can specify its own `vehicle_type` and `transport_job_type`
- Defaults to parent Transport Order values when leg is created
- Validates vehicle type compatibility

### 5. Template Integration
- Can populate legs from Transport Templates
- Supports day offsets for multi-day transport plans
- Preserves facility and address information from templates

## Validation Rules

1. **Minimum Legs**: Transport Order must have at least one leg before submission
2. **Required Fields**: Each leg must have:
   - Facility type and facility for both pick and drop locations
   - Vehicle type
   - Transport job type
3. **Facility Validation**: 
   - Pick and drop facilities cannot be the same unless different addresses are specified
   - Pick and drop addresses cannot be the same
4. **Mode Validation**: 
   - `pick_mode` must be a valid Pick and Drop Mode with `allow_in_pick = 1`
   - `drop_mode` must be a valid Pick and Drop Mode with `allow_in_drop = 1`
5. **Date Validation**: If `scheduled_date` is set on a leg, it must be a valid date

## Workflow

### 1. Creating Transport Order Legs

**Manual Creation**:
1. User creates or opens a Transport Order
2. Navigates to "Leg Plan" tab
3. Adds rows to the `legs` child table
4. Selects facility types and facilities for pick and drop locations
5. Addresses are auto-filled from facility primary addresses
6. Optionally sets pick/drop modes, vehicle type, transport job type, and scheduled date

**Template-Based Creation**:
1. User selects a Transport Template on the Transport Order
2. Clicks "Leg Plan" → "Create" button
3. System calls `action_get_leg_plan()` which:
   - Fetches legs from the template
   - Maps template fields to Transport Order Legs
   - Calculates scheduled dates based on day offsets
   - Populates the legs table

### 2. Validation and Submission

1. User fills in required leg information
2. System validates legs during `validate()`:
   - Auto-fills addresses if missing
   - Validates facility compatibility
3. Before submission, `before_submit()` validates:
   - At least one leg exists
   - All required fields are present
   - Facilities and addresses are valid

### 3. Transport Job Creation

1. User submits Transport Order
2. User creates Transport Job from Transport Order
3. System calls `_create_and_attach_job_legs_from_order_legs()`:
   - Creates a Transport Leg document for each Transport Order Leg
   - Validates pick/drop modes
   - Copies all relevant fields
   - Links Transport Legs to Transport Job
   - Creates denormalized entries in Transport Job Legs table

### 4. Run Sheet Creation

1. User creates Run Sheet from Transport Job
2. System can group all legs in one Run Sheet or create separate Run Sheets per leg
3. Transport Legs are added to Run Sheet for execution

## Code Structure

### Files and Locations

```
logistics/transport/doctype/
├── transport_order_legs/
│   ├── transport_order_legs.json          # Doctype definition
│   ├── transport_order_legs.py            # Python class and API methods
│   └── __pycache__/                       # Python bytecode
├── transport_order/
│   ├── transport_order.json               # Parent doctype (references legs table)
│   ├── transport_order.py                 # Validation, job creation logic
│   └── transport_order.js                 # Frontend event handlers
└── transport_leg/
    └── transport_leg.py                   # Target doctype created from order legs
```

### Key Constants

- `ORDER_LEGS_FIELDNAME_FALLBACKS`: List of possible field names for the legs child table (e.g., `["legs", "transport_order_legs"]`)

### Helper Functions

- `_find_child_table_fieldname()`: Discovers the actual field name for the legs child table
- `_safe_set()`: Sets a field value only if the field exists on the document
- `_copy_child_rows_by_common_fields()`: Copies child table rows between documents based on common fields
- `_map_template_row_to_order_row()`: Maps template leg data to Transport Order Leg format

## Technical Notes

### Address Resolution Strategy

The address auto-fill uses a two-tier approach:

1. **Primary Address Fields**: For facility types with dedicated primary address fields (Shipper, Consignee, Container Yard, etc.), directly accesses the field
2. **Dynamic Link Fallback**: For facility types without dedicated fields or when primary address is not set, queries Address records linked via Dynamic Links, prioritizing:
   - `is_primary_address = 1`
   - `is_shipping_address = 1`
   - First created address

### Pick/Drop Mode Validation

Pick and Drop Modes are validated at two points:
1. **Frontend**: Link filters restrict available modes based on `allow_in_pick` and `allow_in_drop` flags
2. **Backend**: When creating Transport Legs from Order Legs, validates that selected modes exist and are appropriate

### Denormalization Strategy

When creating Transport Legs from Order Legs, the system creates:
1. **Transport Leg Document**: Full document with all details (source of truth)
2. **Transport Job Legs Entry**: Denormalized snapshot in child table for quick viewing/filtering

This allows efficient querying and filtering while maintaining a single source of truth in the Transport Leg document.

## Future Enhancements

Potential areas for future development:

1. **Leg Sequencing**: Visual ordering and sequencing of legs
2. **Leg Dependencies**: Define dependencies between legs (e.g., leg 2 must start after leg 1 completes)
3. **Leg Status Tracking**: Individual status tracking per leg
4. **Leg Costing**: Per-leg cost calculation and allocation
5. **Leg Optimization**: Route optimization across multiple legs
6. **Leg Templates**: Reusable leg configurations

## Related Documentation

- Transport Order: Main parent document
- Transport Job: Created from Transport Order, contains Transport Legs
- Transport Leg: Executable leg created from Transport Order Leg
- Transport Template: Template for populating legs
- Pick and Drop Mode: Defines pick/drop operation types
- Facility Types: Shipper, Consignee, Container Yard, etc.
