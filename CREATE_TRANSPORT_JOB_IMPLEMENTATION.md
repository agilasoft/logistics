# Create Transport Job Implementation

This document explains how the "Create>>Transport Job" feature is implemented in the Transport Order doctype.

## Overview

The "Create>>Transport Job" feature allows users to create a Transport Job from a submitted Transport Order. This action transforms a Transport Order (which represents a customer booking) into an executable Transport Job that can be assigned to vehicles and drivers.

## User Interface

### Button Display Logic

The "Create>>Transport Job" button appears in the Transport Order form's refresh event handler (`transport_order.js`, lines 353-409):

```javascript
// Add Create Transport Job button if document is submitted
if (frm.doc.docstatus === 1) {
    // Check if a Transport Job already exists for this Transport Order
    frappe.db.get_value('Transport Job', { transport_order: frm.doc.name }, 'name', function(r) {
        if (r && r.name) {
            // Transport Job already exists - show link to existing job
            frm.add_custom_button(__("Transport Job"), function() {
                frappe.set_route("Form", "Transport Job", r.name);
            }, __("View"));
        } else {
            // No Transport Job exists - show create button
            frm.add_custom_button(__("Transport Job"), function() {
                // Call backend function to create Transport Job
            }, __("Create"));
        }
    });
}
```

**Key Points:**
- Button only appears when `docstatus === 1` (submitted Transport Order)
- System checks if a Transport Job already exists before showing the button
- If job exists: Shows "View" button that navigates to the existing Transport Job
- If job doesn't exist: Shows "Create" button that triggers job creation

### Button Action

When the "Create" button is clicked, it calls the backend function:

```javascript
frappe.call({
    method: "logistics.transport.doctype.transport_order.transport_order.action_create_transport_job",
    args: {
        docname: frm.doc.name
    },
    freeze: true,
    freeze_message: __("Creating transport job..."),
    callback: function(response) {
        // Handle success/error responses
    }
});
```

## Backend Implementation

### Main Function: `action_create_transport_job`

**Location:** `transport_order.py`, lines 1211-1306

**Function Signature:**
```python
@frappe.whitelist()
def action_create_transport_job(docname: str):
    """Create (or reuse) a Transport Job from a submitted Transport Order."""
```

### Implementation Flow

#### 1. Validation

```python
doc = frappe.get_doc("Transport Order", docname)

if doc.docstatus != 1:
    frappe.throw(_("Please submit the Transport Order before creating a Transport Job."))
```

**Requirement:** Transport Order must be submitted (`docstatus = 1`) before creating a Transport Job.

#### 2. Duplicate Prevention

```python
# Reuse if already created
existing = frappe.db.get_value("Transport Job", {"transport_order": doc.name}, "name")
if existing:
    return {"name": existing, "created": False, "already_exists": True}
```

**Prevents:** Creating multiple Transport Jobs from the same Transport Order. If one already exists, returns the existing job name.

#### 3. Create New Transport Job Document

```python
job = frappe.new_doc("Transport Job")
job_meta = frappe.get_meta(job.doctype)
```

#### 4. Header Field Mapping

Maps fields from Transport Order to Transport Job header:

```python
header_map = {
    "transport_order": doc.name,
    "transport_template": getattr(doc, "transport_template", None),
    "transport_job_type": getattr(doc, "transport_job_type", None),
    "customer": getattr(doc, "customer", None),
    "booking_date": getattr(doc, "booking_date", None),
    "customer_ref_no": getattr(doc, "customer_ref_no", None),
    "hazardous": getattr(doc, "hazardous", None),
    "refrigeration": getattr(doc, "reefer", None),  # Note: TO.reefer -> TJ.refrigeration
    "vehicle_type": getattr(doc, "vehicle_type", None),
    "load_type": getattr(doc, "load_type", None),
    "container_type": getattr(doc, "container_type", None),
    "container_no": getattr(doc, "container_no", None),
    "consolidate": getattr(doc, "consolidate", None),
    "pick_address": getattr(doc, "pick_address", None),
    "drop_address": getattr(doc, "drop_address", None),
    "company": getattr(doc, "company", None),
    "branch": getattr(doc, "branch", None),
    "cost_center": getattr(doc, "cost_center", None),
    "profit_center": getattr(doc, "profit_center", None),
}
```

**Field Mapping Notes:**
- Only maps fields that exist on the Transport Job doctype (checked via `job_meta.has_field()`)
- Uses `getattr()` with `None` default to safely handle missing fields
- Special mapping: `reefer` (Transport Order) → `refrigeration` (Transport Job)

#### 5. Copy Child Tables

##### Packages

```python
_copy_child_rows_by_common_fields(
    src_doc=doc, src_table_field="packages", 
    dst_doc=job, dst_table_field="packages"
)
```

##### Charges

```python
_copy_child_rows_by_common_fields(
    src_doc=doc, src_table_field="charges", 
    dst_doc=job, dst_table_field="charges"
)
```

**Helper Function:** `_copy_child_rows_by_common_fields()` (lines 1698-1734)
- Copies child table rows by matching common field names
- Excludes system fields (name, owner, creation, modified, etc.)
- Only copies fields that exist on both source and destination child doctypes

#### 6. Insert Transport Job (Temporary)

```python
# Temporarily ignore mandatory and validation checks
job.flags.ignore_mandatory = True
job.flags.ignore_validate = True
job.insert(ignore_permissions=False)
```

**Why temporary insert?**
- Transport Job needs a name before creating Transport Legs
- Transport Legs need to reference the Transport Job name
- Validation is bypassed temporarily to allow leg creation

#### 7. Create Transport Legs

```python
_create_and_attach_job_legs_from_order_legs(
    order_doc=doc,
    job_doc=job,
    order_legs_field=order_legs_field,
    job_legs_field=job_legs_field,
)
```

**Process:**
1. Iterates through each Transport Order Leg
2. Creates a top-level Transport Leg document for each order leg
3. Links the Transport Leg to the Transport Job
4. Copies leg fields (facilities, addresses, vehicle type, etc.)
5. Inserts the Transport Leg
6. Adds a denormalized snapshot row to Transport Job Legs child table

**Helper Function:** `_create_and_attach_job_legs_from_order_legs()` (lines 1737-1803)

**Fields Copied from Order Leg to Transport Leg:**
- `facility_type_from`, `facility_from`
- `pick_mode`, `pick_address`
- `facility_type_to`, `facility_to`
- `drop_mode`, `drop_address`
- `vehicle_type`
- `transport_job_type`

**Validation:**
- Validates that `pick_mode` and `drop_mode` are valid Pick and Drop Mode records
- Uses `_safe_set()` helper to only set fields that exist on the destination doctype

#### 8. Final Save

```python
job.save(ignore_permissions=False)
frappe.db.commit()
return {"name": job.name, "created": True, "already_exists": False}
```

**Final save:**
- Saves the Transport Job with all legs attached
- Validation is now enforced (flags removed)
- Commits the transaction
- Returns success response

### Error Handling

#### Duplicate Entry Error

```python
except frappe.DuplicateEntryError:
    frappe.db.rollback()
    # Check again if job was created by another process
    existing = frappe.db.get_value("Transport Job", {"transport_order": docname}, "name")
    if existing:
        return {"name": existing, "created": False, "already_exists": True}
    # If we still can't find it, log and re-raise
    frappe.log_error(...)
    frappe.throw(_("Failed to create Transport Job due to a duplicate entry..."))
```

**Handles:** Race conditions where multiple requests try to create the same Transport Job simultaneously.

#### General Exception Handling

```python
except Exception as e:
    frappe.log_error(f"Error creating transport job: {str(e)}")
    frappe.throw(_("Failed to create Transport Job: {0}").format(str(e)))
```

## Response Format

The function returns a dictionary with the following structure:

```python
{
    "name": "TJ-00001",           # Transport Job name
    "created": True,              # Whether job was newly created
    "already_exists": False      # Whether job already existed
}
```

**Possible Return Values:**

1. **New Job Created:**
   ```python
   {"name": "TJ-00001", "created": True, "already_exists": False}
   ```

2. **Job Already Exists:**
   ```python
   {"name": "TJ-00001", "created": False, "already_exists": True}
   ```

## Frontend Response Handling

The JavaScript callback handles the response:

```javascript
callback: function(response) {
    if (response.message) {
        if (response.message.already_exists) {
            // Show message and navigate to existing job
            frappe.msgprint({
                title: __("Transport Job Already Exists"),
                message: __("Transport Job {0} already exists...", [response.message.name]),
                indicator: 'blue'
            });
            frappe.set_route("Form", "Transport Job", response.message.name);
            frm.reload_doc();
        } else if (response.message.created) {
            // Show success message and navigate to new job
            frappe.msgprint({
                title: __("Transport Job Created"),
                message: __("Transport Job {0} created successfully.", [response.message.name]),
                indicator: 'green'
            });
            frappe.set_route("Form", "Transport Job", response.message.name);
            frm.reload_doc();
        }
    }
}
```

## Data Flow Diagram

```
Transport Order (Submitted)
    │
    ├─> Header Fields ──────────────> Transport Job Header
    │
    ├─> Packages Child Table ───────> Transport Job Packages
    │
    ├─> Charges Child Table ─────────> Transport Job Charges
    │
    └─> Transport Order Legs ───────> Transport Legs (Top-level)
            │                              │
            │                              └─> Transport Job Legs (Child table snapshot)
```

## Key Design Decisions

### 1. Why Create Top-Level Transport Legs?

Transport Legs are created as separate documents (not just child table rows) because:
- They can be referenced independently
- They can be linked to Run Sheets
- They maintain their own lifecycle and status
- They can be queried and filtered separately

### 2. Why Denormalized Snapshot in Transport Job Legs?

The Transport Job Legs child table provides:
- Quick view of all legs without querying Transport Leg doctype
- Filtering and sorting capabilities in the Transport Job form
- Performance optimization for displaying leg information

### 3. Why Temporary Insert with Flags?

The Transport Job is inserted with `ignore_mandatory` and `ignore_validate` flags because:
- Transport Legs need the Transport Job name to reference it
- Some validations may fail before all legs are created
- Final save ensures all validations pass

### 4. Why Check for Existing Jobs?

Prevents:
- Duplicate Transport Jobs from the same Transport Order
- Data inconsistency
- Confusion about which job to use

## Related Functions

### Helper Functions

1. **`_copy_child_rows_by_common_fields()`** (lines 1698-1734)
   - Copies child table rows between documents
   - Only copies fields that exist on both doctypes

2. **`_create_and_attach_job_legs_from_order_legs()`** (lines 1737-1803)
   - Creates Transport Leg documents from Transport Order Legs
   - Links legs to Transport Job

3. **`_safe_set()`** (lines 1806-1812)
   - Safely sets field values only if field exists on doctype
   - Prevents errors from schema mismatches

4. **`_find_child_table_fieldname()`** (lines 874-893)
   - Finds the field name of a child table on a parent doctype
   - Handles schema variations

## Testing Considerations

When testing this feature:

1. **Prerequisites:**
   - Transport Order must be submitted
   - Transport Order should have at least one leg
   - Transport Order should have packages

2. **Test Cases:**
   - Create job from valid Transport Order
   - Attempt to create duplicate job (should return existing)
   - Create job with multiple legs
   - Create job with packages and charges
   - Handle missing fields gracefully

3. **Edge Cases:**
   - Transport Order with no legs (should fail validation)
   - Transport Order with missing required fields
   - Concurrent creation attempts (race condition)

## Dependencies

- **Transport Order** doctype must be submitted
- **Transport Job** doctype must exist
- **Transport Leg** doctype must exist
- **Transport Order Legs** child table must have data
- Related doctypes: Vehicle Type, Load Type, Facilities, Addresses

## Future Enhancements

Potential improvements:
1. Batch creation of multiple Transport Jobs
2. Preview before creation
3. Partial creation (create job with only some legs)
4. Undo/delete Transport Job creation
5. Automatic job creation on Transport Order submission
