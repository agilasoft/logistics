# Shipper and Consignee Fields Feature

## Overview

This document describes the implementation of the **Shipper** and **Consignee** fields feature that enables automatic data flow from **Sales Quote** → **Warehouse Contract** → **Warehouse Orders** → **Warehouse Jobs**. This feature ensures that shipper and consignee information is consistently propagated through the entire warehouse management workflow, providing complete traceability from quote to execution.

## Feature Description

The shipper and consignee fields have been added to the warehouse management workflow to track the parties involved in warehouse operations. These fields automatically populate when documents are linked, reducing manual data entry and ensuring data consistency.

## Document Flow

```
Sales Quote
    ↓ (Create Warehouse Contract)
Warehouse Contract
    ↓ (Create Orders)
    ├── Inbound Order → Warehouse Job (Putaway)
    ├── Release Order → Warehouse Job (Pick)
    ├── VAS Order → Warehouse Job (VAS)
    ├── Transfer Order (Customer type only) → Warehouse Job (Move)
    └── Stocktake Order → Warehouse Job (Stocktake)
```

## Implementation Details

### 1. Sales Quote

**Location**: `logistics/pricing_center/doctype/sales_quote/`

**Fields Added**:
- `shipper` (Link to Shipper)
- `consignee` (Link to Consignee)

**Field Configuration**:
- Both fields are visible in list view
- Located in the main form section alongside customer and date fields
- Field type: Link
- Options: Shipper / Consignee respectively

**File**: `sales_quote.json` (lines 190-201)

```json
{
  "fieldname": "shipper",
  "fieldtype": "Link",
  "in_list_view": 1,
  "label": "Shipper",
  "options": "Shipper"
},
{
  "fieldname": "consignee",
  "fieldtype": "Link",
  "in_list_view": 1,
  "label": "Consignee",
  "options": "Consignee"
}
```

### 2. Warehouse Contract

**Location**: `logistics/warehousing/doctype/warehouse_contract/`

**Fields Added**:
- `shipper` (Link to Shipper)
- `consignee` (Link to Consignee)

**Auto-Population Logic**:
When a Sales Quote is selected in the Warehouse Contract form, the shipper and consignee fields are automatically populated from the selected Sales Quote.

**Implementation**: `warehouse_contract.js` (lines 29-47)

```javascript
sales_quote(frm) {
    // Populate shipper and consignee from Sales Quote
    if (frm.doc.sales_quote) {
        frappe.db.get_value("Sales Quote", frm.doc.sales_quote, ["shipper", "consignee"], function(r) {
            if (r) {
                if (r.shipper) {
                    frm.set_value("shipper", r.shipper);
                }
                if (r.consignee) {
                    frm.set_value("consignee", r.consignee);
                }
            }
        });
    } else {
        // Clear shipper and consignee if sales_quote is cleared
        frm.set_value("shipper", "");
        frm.set_value("consignee", "");
    }
}
```

**Field Configuration**:
- Located in the Connections tab
- Field type: Link
- Options: Shipper / Consignee respectively

**File**: `warehouse_contract.json` (lines 99-108)

### 3. Warehouse Inbound Order

**Location**: `logistics/warehousing/doctype/inbound_order/`

**Fields Added**:
- `shipper` (Link to Shipper)
- `consignee` (Link to Consignee)

**Auto-Population Logic**:
When a Warehouse Contract is selected in the Inbound Order form, the shipper and consignee fields are automatically populated from the selected Warehouse Contract.

**Implementation**: `inbound_order.js` (lines 64-82)

```javascript
contract(frm) {
    // Populate shipper and consignee from Warehouse Contract
    if (frm.doc.contract) {
        frappe.db.get_value("Warehouse Contract", frm.doc.contract, ["shipper", "consignee"], function(r) {
            if (r) {
                if (r.shipper) {
                    frm.set_value("shipper", r.shipper);
                }
                if (r.consignee) {
                    frm.set_value("consignee", r.consignee);
                }
            }
        });
    } else {
        // Clear shipper and consignee if contract is cleared
        frm.set_value("shipper", "");
        frm.set_value("consignee", "");
    }
}
```

**Field Configuration**:
- Located in the main form section
- Field type: Link
- Options: Shipper / Consignee respectively

**File**: `inbound_order.json` (lines 184-194)

### 4. Release Order

**Location**: `logistics/warehousing/doctype/release_order/`

**Fields Added**:
- `shipper` (Link to Shipper)
- `consignee` (Link to Consignee)

**Auto-Population Logic**:
When a Warehouse Contract is selected in the Release Order form, the shipper and consignee fields are automatically populated from the selected Warehouse Contract.

**Implementation**: `release_order.js`

```javascript
contract(frm) {
    // Populate shipper and consignee from Warehouse Contract
    if (frm.doc.contract) {
        frappe.db.get_value("Warehouse Contract", frm.doc.contract, ["shipper", "consignee"], function(r) {
            if (r) {
                if (r.shipper) {
                    frm.set_value("shipper", r.shipper);
                }
                if (r.consignee) {
                    frm.set_value("consignee", r.consignee);
                }
            }
        });
    } else {
        // Clear shipper and consignee if contract is cleared
        frm.set_value("shipper", "");
        frm.set_value("consignee", "");
    }
}
```

**Field Configuration**:
- Located in the main form section (after Order Date)
- Field type: Link
- Options: Shipper / Consignee respectively

**File**: `release_order.json`

### 5. VAS Order

**Location**: `logistics/warehousing/doctype/vas_order/`

**Fields Added**:
- `shipper` (Link to Shipper)
- `consignee` (Link to Consignee)

**Auto-Population Logic**:
When a Warehouse Contract is selected in the VAS Order form, the shipper and consignee fields are automatically populated from the selected Warehouse Contract.

**Implementation**: `vas_order.js`

```javascript
contract(frm) {
    // Populate shipper and consignee from Warehouse Contract
    if (frm.doc.contract) {
        frappe.db.get_value("Warehouse Contract", frm.doc.contract, ["shipper", "consignee"], function(r) {
            if (r) {
                if (r.shipper) {
                    frm.set_value("shipper", r.shipper);
                }
                if (r.consignee) {
                    frm.set_value("consignee", r.consignee);
                }
            }
        });
    } else {
        // Clear shipper and consignee if contract is cleared
        frm.set_value("shipper", "");
        frm.set_value("consignee", "");
    }
}
```

**Field Configuration**:
- Located in the main form section (after Order Date)
- Field type: Link
- Options: Shipper / Consignee respectively

**File**: `vas_order.json`

### 6. Transfer Order

**Location**: `logistics/warehousing/doctype/transfer_order/`

**Fields Added**:
- `shipper` (Link to Shipper) - **Only visible when Transfer Type is "Customer"**
- `consignee` (Link to Consignee) - **Only visible when Transfer Type is "Customer"**

**Auto-Population Logic**:
When a Warehouse Contract is selected in the Transfer Order form (and Transfer Type is "Customer"), the shipper and consignee fields are automatically populated from the selected Warehouse Contract.

**Implementation**: `transfer_order.js`

```javascript
contract(frm) {
    // Populate shipper and consignee from Warehouse Contract (only for Customer transfer type)
    if (frm.doc.transfer_type === "Customer" && frm.doc.contract) {
        frappe.db.get_value("Warehouse Contract", frm.doc.contract, ["shipper", "consignee"], function(r) {
            if (r) {
                if (r.shipper) {
                    frm.set_value("shipper", r.shipper);
                }
                if (r.consignee) {
                    frm.set_value("consignee", r.consignee);
                }
            }
        });
    } else {
        // Clear shipper and consignee if contract is cleared or transfer type is not Customer
        if (frm.doc.transfer_type !== "Customer") {
            frm.set_value("shipper", "");
            frm.set_value("consignee", "");
        } else if (!frm.doc.contract) {
            frm.set_value("shipper", "");
            frm.set_value("consignee", "");
        }
    }
},

transfer_type(frm) {
    // Clear shipper and consignee when switching away from Customer type
    if (frm.doc.transfer_type !== "Customer") {
        frm.set_value("shipper", "");
        frm.set_value("consignee", "");
    }
}
```

**Field Configuration**:
- Located in the main form section (after Order Date)
- Field type: Link
- Options: Shipper / Consignee respectively
- **Visibility**: Only shown when `transfer_type == "Customer"` (using `depends_on`)

**File**: `transfer_order.json`

### 7. Stocktake Order

**Location**: `logistics/warehousing/doctype/stocktake_order/`

**Fields Added**:
- `shipper` (Link to Shipper)
- `consignee` (Link to Consignee)

**Auto-Population Logic**:
When a Warehouse Contract is selected in the Stocktake Order form, the shipper and consignee fields are automatically populated from the selected Warehouse Contract.

**Implementation**: `stocktake_order.js`

```javascript
contract(frm) {
    // Populate shipper and consignee from Warehouse Contract
    if (frm.doc.contract) {
        frappe.db.get_value("Warehouse Contract", frm.doc.contract, ["shipper", "consignee"], function(r) {
            if (r) {
                if (r.shipper) {
                    frm.set_value("shipper", r.shipper);
                }
                if (r.consignee) {
                    frm.set_value("consignee", r.consignee);
                }
            }
        });
    } else {
        // Clear shipper and consignee if contract is cleared
        frm.set_value("shipper", "");
        frm.set_value("consignee", "");
    }
}
```

**Field Configuration**:
- Located in the main form section (after Date)
- Field type: Link
- Options: Shipper / Consignee respectively

**File**: `stocktake_order.json`

### 8. Warehouse Job

**Location**: `logistics/warehousing/doctype/warehouse_job/`

**Fields Added**:
- `shipper` (Link to Shipper)
- `consignee` (Link to Consignee)

**Auto-Population Logic**:
When a Warehouse Contract is selected in the Warehouse Job form, the shipper and consignee fields are automatically populated from the selected Warehouse Contract.

**Implementation**: `warehouse_job.js`

```javascript
warehouse_contract: function(frm) {
    // ... existing charge refresh logic ...
    
    // Populate shipper and consignee from Warehouse Contract
    if (frm.doc.warehouse_contract) {
        frappe.db.get_value("Warehouse Contract", frm.doc.warehouse_contract, ["shipper", "consignee"], function(r) {
            if (r) {
                if (r.shipper) {
                    frm.set_value("shipper", r.shipper);
                }
                if (r.consignee) {
                    frm.set_value("consignee", r.consignee);
                }
            }
        });
    } else {
        // Clear shipper and consignee if contract is cleared
        frm.set_value("shipper", "");
        frm.set_value("consignee", "");
    }
}
```

**Data Mapping from Orders**:
When Warehouse Jobs are created from orders, shipper and consignee are automatically mapped from the source order:
- **Inbound Order** → Putaway Job: Maps `shipper` and `consignee` from Inbound Order
- **Release Order** → Pick Job: Maps `shipper` and `consignee` from Release Order
- **VAS Order** → VAS Job: Maps `shipper` and `consignee` from VAS Order
- **Transfer Order** → Move Job: Maps `shipper` and `consignee` from Transfer Order (Customer type only)
- **Stocktake Order** → Stocktake Job: Maps `shipper` and `consignee` from Stocktake Order

**Field Configuration**:
- Located in the main form section (after Customer)
- Field type: Link
- Options: Shipper / Consignee respectively
- Fields are editable (not read-only) to allow manual override if needed

**File**: `warehouse_job.json`

**Python Mapping Functions Updated**:
- `inbound_order.py` - `make_warehouse_job()`: Maps shipper/consignee from Inbound Order
- `release_order.py` - `make_warehouse_job()`: Maps shipper/consignee from Release Order
- `vas_order.py` - `make_warehouse_job()`: Maps shipper/consignee from VAS Order
- `transfer_order.py` - `make_warehouse_job()`: Maps shipper/consignee from Transfer Order
- `stocktake_order.py` - `make_warehouse_job()`: Maps shipper/consignee from Stocktake Order

## User Workflow

### Scenario 1: Creating Warehouse Contract from Sales Quote

1. **Create/Open Sales Quote**
   - Fill in customer, date, and other required fields
   - **Enter Shipper and Consignee** (if applicable)
   - Submit the Sales Quote

2. **Create Warehouse Contract**
   - Click "Create Warehouse Contract" button on the submitted Sales Quote
   - The Warehouse Contract is created with basic information
   - **Manually select the Sales Quote** in the Warehouse Contract form (if not auto-linked)
   - **Shipper and Consignee are automatically populated** from the Sales Quote

3. **Submit Warehouse Contract**

### Scenario 2: Creating Inbound Order from Warehouse Contract

1. **Create/Open Inbound Order**
   - Select Customer
   - **Select Warehouse Contract** from the Contract field
   - **Shipper and Consignee are automatically populated** from the Warehouse Contract
   - Fill in other required fields (items, dates, etc.)
   - Submit the Inbound Order

### Scenario 3: Creating Release Order from Warehouse Contract

1. **Create/Open Release Order**
   - Select Customer
   - **Select Warehouse Contract** from the Contract field
   - **Shipper and Consignee are automatically populated** from the Warehouse Contract
   - Fill in other required fields (items, dates, etc.)
   - Submit the Release Order

### Scenario 4: Creating VAS Order from Warehouse Contract

1. **Create/Open VAS Order**
   - Select Customer and VAS Order Type
   - **Select Warehouse Contract** from the Contract field
   - **Shipper and Consignee are automatically populated** from the Warehouse Contract
   - Fill in other required fields (items, VAS inputs, etc.)
   - Submit the VAS Order

### Scenario 5: Creating Transfer Order (Customer Type) from Warehouse Contract

1. **Create/Open Transfer Order**
   - Set Transfer Type to **"Customer"**
   - Select Customer
   - **Select Warehouse Contract** from the Contract field
   - **Shipper and Consignee fields become visible and are automatically populated** from the Warehouse Contract
   - Fill in other required fields (items, reason, etc.)
   - Submit the Transfer Order

**Note**: Shipper and Consignee fields are only available when Transfer Type is "Customer". They are hidden for "Internal" and "Others" transfer types.

### Scenario 6: Creating Stocktake Order from Warehouse Contract

1. **Create/Open Stocktake Order**
   - Select Customer, Type, and Scope
   - **Select Warehouse Contract** from the Contract field
   - **Shipper and Consignee are automatically populated** from the Warehouse Contract
   - Fill in other required fields (items, dates, etc.)
   - Submit the Stocktake Order

### Scenario 7: Creating Warehouse Job from Orders

1. **Create Warehouse Job from any Order**
   - From Inbound/Release/VAS/Transfer/Stocktake Order, click "Create Warehouse Job"
   - **Shipper and Consignee are automatically mapped** from the source order
   - The Warehouse Job is created with all relevant information including shipper/consignee

2. **Manual Warehouse Job Creation**
   - Create Warehouse Job manually
   - Select Customer
   - **Select Warehouse Contract** from the Warehouse Contract field
   - **Shipper and Consignee are automatically populated** from the Warehouse Contract

### Scenario 8: Manual Entry

- Users can manually enter or modify shipper and consignee fields at any stage
- If a linked document (Sales Quote or Contract) is cleared, the shipper and consignee fields are automatically cleared

## Technical Details

### Data Flow

1. **Sales Quote → Warehouse Contract**
   - Trigger: User selects Sales Quote in Warehouse Contract form
   - Action: JavaScript event handler `sales_quote()` fetches shipper/consignee from Sales Quote
   - Result: Fields are auto-populated

2. **Warehouse Contract → All Order Types**
   - Trigger: User selects Warehouse Contract in any order form (Inbound, Release, VAS, Transfer, Stocktake)
   - Action: JavaScript event handler `contract()` fetches shipper/consignee from Warehouse Contract
   - Result: Fields are auto-populated

3. **Orders → Warehouse Jobs**
   - Trigger: User creates Warehouse Job from an order (via `make_warehouse_job` function)
   - Action: Python mapping function copies shipper/consignee from source order to Warehouse Job
   - Result: Fields are automatically mapped during job creation

4. **Warehouse Contract → Warehouse Job**
   - Trigger: User selects Warehouse Contract in Warehouse Job form
   - Action: JavaScript event handler `warehouse_contract()` fetches shipper/consignee from Warehouse Contract
   - Result: Fields are auto-populated

5. **Transfer Order Special Case**
   - Additional trigger: When Transfer Type changes
   - Action: If Transfer Type is not "Customer", shipper/consignee fields are cleared and hidden
   - Result: Fields are only visible and populated when Transfer Type is "Customer"

### Field Clearing Logic

All implementations include logic to clear the shipper and consignee fields when the parent link is cleared:
- If Sales Quote is cleared in Warehouse Contract → shipper/consignee are cleared
- If Warehouse Contract is cleared in any Order → shipper/consignee are cleared
- If Warehouse Contract is cleared in Warehouse Job → shipper/consignee are cleared
- If Transfer Type changes from "Customer" to another type → shipper/consignee are cleared

## Benefits

1. **Data Consistency**: Ensures shipper and consignee information flows consistently through the warehouse workflow
2. **Reduced Manual Entry**: Automatic population reduces data entry errors and saves time
3. **Traceability**: Maintains link between parties across the entire warehouse process
4. **User-Friendly**: Seamless experience with automatic field population

## Files Modified

1. `logistics/pricing_center/doctype/sales_quote/sales_quote.json`
   - Added shipper and consignee fields

2. `logistics/warehousing/doctype/warehouse_contract/warehouse_contract.json`
   - Added shipper and consignee fields

3. `logistics/warehousing/doctype/warehouse_contract/warehouse_contract.js`
   - Added auto-population logic when Sales Quote is selected

4. `logistics/warehousing/doctype/inbound_order/inbound_order.json`
   - Added shipper and consignee fields

5. `logistics/warehousing/doctype/inbound_order/inbound_order.js`
   - Added auto-population logic when Warehouse Contract is selected

6. `logistics/warehousing/doctype/release_order/release_order.json`
   - Added shipper and consignee fields

7. `logistics/warehousing/doctype/release_order/release_order.js`
   - Added auto-population logic when Warehouse Contract is selected

8. `logistics/warehousing/doctype/vas_order/vas_order.json`
   - Added shipper and consignee fields

9. `logistics/warehousing/doctype/vas_order/vas_order.js`
   - Added auto-population logic when Warehouse Contract is selected

10. `logistics/warehousing/doctype/transfer_order/transfer_order.json`
    - Added shipper and consignee fields (with depends_on for Customer transfer type)

11. `logistics/warehousing/doctype/transfer_order/transfer_order.js`
    - Added auto-population logic when Warehouse Contract is selected (Customer type only)
    - Added transfer_type handler to clear fields when switching away from Customer type

12. `logistics/warehousing/doctype/stocktake_order/stocktake_order.json`
    - Added shipper and consignee fields

13. `logistics/warehousing/doctype/stocktake_order/stocktake_order.js`
    - Added auto-population logic when Warehouse Contract is selected

14. `logistics/warehousing/doctype/warehouse_job/warehouse_job.json`
    - Added shipper and consignee fields

15. `logistics/warehousing/doctype/warehouse_job/warehouse_job.js`
    - Added auto-population logic when Warehouse Contract is selected

16. `logistics/warehousing/doctype/inbound_order/inbound_order.py`
    - Updated `make_warehouse_job()` to map shipper/consignee from Inbound Order

17. `logistics/warehousing/doctype/release_order/release_order.py`
    - Updated `make_warehouse_job()` to map shipper/consignee from Release Order

18. `logistics/warehousing/doctype/vas_order/vas_order.py`
    - Updated `make_warehouse_job()` to map shipper/consignee from VAS Order

19. `logistics/warehousing/doctype/transfer_order/transfer_order.py`
    - Updated `make_warehouse_job()` to map shipper/consignee from Transfer Order

20. `logistics/warehousing/doctype/stocktake_order/stocktake_order.py`
    - Updated `make_warehouse_job()` to map shipper/consignee from Stocktake Order

## Testing Scenarios

### Test Case 1: Sales Quote to Warehouse Contract
1. Create Sales Quote with shipper and consignee
2. Create Warehouse Contract from Sales Quote
3. Select the Sales Quote in Warehouse Contract
4. **Expected**: Shipper and consignee are auto-populated

### Test Case 2: Warehouse Contract to Inbound Order
1. Create Warehouse Contract with shipper and consignee
2. Create Inbound Order
3. Select the Warehouse Contract
4. **Expected**: Shipper and consignee are auto-populated

### Test Case 3: Warehouse Contract to Release Order
1. Create Warehouse Contract with shipper and consignee
2. Create Release Order
3. Select the Warehouse Contract
4. **Expected**: Shipper and consignee are auto-populated

### Test Case 4: Warehouse Contract to VAS Order
1. Create Warehouse Contract with shipper and consignee
2. Create VAS Order
3. Select the Warehouse Contract
4. **Expected**: Shipper and consignee are auto-populated

### Test Case 5: Warehouse Contract to Transfer Order (Customer Type)
1. Create Warehouse Contract with shipper and consignee
2. Create Transfer Order
3. Set Transfer Type to "Customer"
4. Select Customer and Warehouse Contract
5. **Expected**: Shipper and consignee fields become visible and are auto-populated

### Test Case 6: Transfer Order Type Change
1. Create Transfer Order with Transfer Type "Customer"
2. Set shipper and consignee
3. Change Transfer Type to "Internal"
4. **Expected**: Shipper and consignee fields are cleared and hidden

### Test Case 7: Warehouse Contract to Stocktake Order
1. Create Warehouse Contract with shipper and consignee
2. Create Stocktake Order
3. Select the Warehouse Contract
4. **Expected**: Shipper and consignee are auto-populated

### Test Case 8: Field Clearing
1. In Warehouse Contract, select a Sales Quote (fields populate)
2. Clear the Sales Quote field
3. **Expected**: Shipper and consignee are cleared

### Test Case 9: Warehouse Job from Order
1. Create Inbound Order with shipper and consignee
2. Create Warehouse Job from Inbound Order
3. **Expected**: Shipper and consignee are automatically mapped to Warehouse Job

### Test Case 10: Warehouse Job from Contract
1. Create Warehouse Job manually
2. Select Warehouse Contract with shipper and consignee
3. **Expected**: Shipper and consignee are auto-populated from Warehouse Contract

### Test Case 11: Manual Override
1. Auto-populate shipper/consignee from linked document
2. Manually change the values
3. **Expected**: Manual values are preserved

## Future Enhancements

Potential improvements for future releases:

1. **Automatic Mapping on Creation**: When creating Warehouse Contract programmatically from Sales Quote, automatically map shipper/consignee in the Python code
2. **Validation**: Add validation to ensure shipper/consignee are consistent across linked documents
3. **Reporting**: Add shipper/consignee to warehouse reports and analytics
4. **Gate Pass Integration**: Consider adding shipper/consignee to Gate Pass documents for complete end-to-end traceability

## Notes

- The fields are optional (not required) to maintain flexibility
- The auto-population only occurs when the parent link is selected, not during programmatic creation
- Users can always manually override the auto-populated values
- The feature maintains backward compatibility with existing documents

---

**Document Version**: 2.0  
**Last Updated**: 2025  
**Author**: Development Team

## Summary

This feature has been fully implemented across all warehouse documents:
- ✅ Sales Quote
- ✅ Warehouse Contract
- ✅ Inbound Order
- ✅ Release Order
- ✅ VAS Order
- ✅ Transfer Order (Customer type only)
- ✅ Stocktake Order
- ✅ Warehouse Job

All implementations follow the same pattern: fields auto-populate from Warehouse Contract when selected, and clear when the contract link is removed or (in the case of Transfer Order) when the transfer type changes away from "Customer".

**Complete Data Flow**: Shipper and consignee information now flows seamlessly from Sales Quote → Warehouse Contract → Orders → Warehouse Jobs, providing complete traceability throughout the entire warehouse management workflow.
