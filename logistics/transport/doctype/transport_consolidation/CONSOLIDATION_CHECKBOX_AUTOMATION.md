# How the System Automatically Sets Pick Consolidated and Drop Consolidated Checkboxes

## Overview

The system automatically sets the `pick_consolidated` and `drop_consolidated` checkboxes on Transport Legs based on the **Consolidation Type** and the **address patterns** of the legs. This happens automatically when jobs are added to a consolidation.

---

## When Automation Triggers

The automation is triggered in **two scenarios**:

### 1. When Jobs are Added to Consolidation
**Function:** `_apply_consolidation_automation()`  
**Location:** `transport_consolidation.py` lines 1793-1904  
**Called from:** `add_jobs_to_consolidation()` after jobs are saved

### 2. When Creating Run Sheet from Consolidation
**Function:** `create_run_sheet_from_consolidation()`  
**Location:** `transport_consolidation.py` lines 447-641  
**Called from:** "Create Run Sheet" button

---

## How It Works

### Step 1: Determine Consolidation Type

First, the system determines the consolidation type by analyzing address patterns:

**Function:** `determine_consolidation_type()`  
**Location:** `transport_consolidation.py` lines 112-162

```python
# Collect all unique pick and drop addresses from transport legs
pick_addresses = set()
drop_addresses = set()

for job_row in self.transport_jobs:
    job_legs = frappe.get_all("Transport Leg", filters={"transport_job": job_row.transport_job})
    for leg in job_legs:
        if leg.get("pick_address"):
            pick_addresses.add(leg.get("pick_address"))
        if leg.get("drop_address"):
            drop_addresses.add(leg.get("drop_address"))

# Determine consolidation type
num_pick = len(pick_addresses)
num_drop = len(drop_addresses)

if num_pick == 1 and num_drop == 1:
    self.consolidation_type = "Both"
elif num_pick == 1 and num_drop > 1:
    self.consolidation_type = "Pick"
elif num_pick > 1 and num_drop == 1:
    self.consolidation_type = "Drop"
elif num_pick > 1 and num_drop > 1:
    self.consolidation_type = "Route"
```

### Step 2: Apply Automation Based on Consolidation Type

**Function:** `_apply_consolidation_automation()`  
**Location:** `transport_consolidation.py` lines 1793-1904

The function:
1. Gets all legs from the selected jobs
2. Filters out legs that have run_sheets or are in other consolidations
3. Collects unique pick and drop addresses
4. Sets checkboxes based on consolidation type

---

## Consolidation Type: **Pick**

### When It Triggers:
- Consolidation Type = "Pick"
- All legs have the **same Pick Address**
- Legs have **different Drop Addresses**

### What It Does:
```python
if consolidation_type == "Pick":
    if len(pick_addresses) == 1:  # All legs share same pick address
        for leg in available_legs:
            leg_doc.pick_consolidated = 1      # ✅ CHECK Pick
            leg_doc.drop_consolidated = 0      # ❌ CLEAR Drop
            leg_doc.transport_consolidation = consolidation_name
            leg_doc.save()
```

### Example:
- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address1, Drop=Address3
- **Result:** 
  - `pick_consolidated = 1` ✅
  - `drop_consolidated = 0` ❌

---

## Consolidation Type: **Drop**

### When It Triggers:
- Consolidation Type = "Drop"
- All legs have the **same Drop Address**
- Legs have **different Pick Addresses**

### What It Does:
```python
elif consolidation_type == "Drop":
    if len(drop_addresses) == 1:  # All legs share same drop address
        for leg in available_legs:
            leg_doc.drop_consolidated = 1      # ✅ CHECK Drop
            leg_doc.pick_consolidated = 0      # ❌ CLEAR Pick
            leg_doc.transport_consolidation = consolidation_name
            leg_doc.save()
```

### Example:
- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address3, Drop=Address2
- **Result:**
  - `pick_consolidated = 0` ❌
  - `drop_consolidated = 1` ✅

---

## Consolidation Type: **Both**

### When It Triggers:
- Consolidation Type = "Both"
- All legs have the **same Pick Address AND same Drop Address**

### What It Does:
```python
elif consolidation_type == "Both":
    if len(pick_addresses) == 1 and len(drop_addresses) == 1:
        for leg in available_legs:
            leg_doc.pick_consolidated = 1      # ✅ CHECK Pick
            leg_doc.drop_consolidated = 1      # ✅ CHECK Drop
            leg_doc.transport_consolidation = consolidation_name
            leg_doc.save()
```

### Example:
- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address1, Drop=Address2
- **Result:**
  - `pick_consolidated = 1` ✅
  - `drop_consolidated = 1` ✅

---

## Consolidation Type: **Route**

### When It Triggers:
- Consolidation Type = "Route"
- Multiple Pick Addresses AND Multiple Drop Addresses (milk run)

### What It Does:
```python
elif consolidation_type == "Route":
    for leg in available_legs:
        leg_doc.transport_consolidation = consolidation_name
        # NO checkbox setting - only link to consolidation
        leg_doc.save()
```

### Example:
- Job A: Pick=[Addr1, Addr2], Drop=[Addr3, Addr4]
- Job B: Pick=[Addr5], Drop=[Addr6]
- **Result:**
  - `pick_consolidated = 0` (unchanged)
  - `drop_consolidated = 0` (unchanged)
  - `transport_consolidation = <consolidation_name>` ✅

---

## Complete Flow Diagram

```
User adds jobs to consolidation
         ↓
Consolidation.validate() runs
         ↓
determine_consolidation_type() analyzes addresses
         ↓
Sets consolidation_type = "Pick" | "Drop" | "Both" | "Route"
         ↓
add_jobs_to_consolidation() saves jobs
         ↓
_apply_consolidation_automation() is called
         ↓
Gets all legs from added jobs
         ↓
Filters out legs with run_sheets or in other consolidations
         ↓
Collects unique pick and drop addresses
         ↓
Checks consolidation_type:
    ├─> "Pick" → Check pick_consolidated, Clear drop_consolidated
    ├─> "Drop" → Check drop_consolidated, Clear pick_consolidated
    ├─> "Both" → Check both pick_consolidated and drop_consolidated
    └─> "Route" → Only set transport_consolidation link
         ↓
Saves all legs with updated flags
```

---

## Important Notes

### 1. **Address Pattern Validation**
The automation only sets checkboxes if the address pattern matches the consolidation type:
- **Pick:** Only if `len(pick_addresses) == 1`
- **Drop:** Only if `len(drop_addresses) == 1`
- **Both:** Only if `len(pick_addresses) == 1 AND len(drop_addresses) == 1`

### 2. **Leg Filtering**
Legs are filtered before automation:
- ❌ **Excluded:** Legs with `run_sheet` assigned
- ❌ **Excluded:** Legs already in another consolidation
- ✅ **Included:** Only available legs (no run_sheet, not in other consolidation)

### 3. **Checkbox Clearing**
When setting one checkbox, the other is explicitly cleared:
- **Pick:** Sets `drop_consolidated = 0`
- **Drop:** Sets `pick_consolidated = 0`
- **Both:** Sets both to `1`
- **Route:** Leaves both unchanged

### 4. **Transport Consolidation Link**
All automation sets the `transport_consolidation` field to link the leg to the consolidation, regardless of consolidation type.

### 5. **Error Handling**
If automation fails, it logs an error but doesn't prevent the job from being added to the consolidation.

---

## Code Locations

1. **Consolidation Type Determination:** `transport_consolidation.py` lines 112-162 (`determine_consolidation_type()`)
2. **Automation Function:** `transport_consolidation.py` lines 1793-1904 (`_apply_consolidation_automation()`)
3. **Called From:** `transport_consolidation.py` lines 1985-1990 (`add_jobs_to_consolidation()`)
4. **Run Sheet Creation:** `transport_consolidation.py` lines 447-641 (`create_run_sheet_from_consolidation()`)

---

## Examples

### Example 1: Pick Consolidation
**Jobs Added:**
- TRJ000001: Pick=Warehouse A, Drop=Customer X
- TRJ000002: Pick=Warehouse A, Drop=Customer Y
- TRJ000003: Pick=Warehouse A, Drop=Customer Z

**Consolidation Type:** "Pick" (1 pick, 3 drops)

**Result on Legs:**
- All legs: `pick_consolidated = 1` ✅
- All legs: `drop_consolidated = 0` ❌
- All legs: `transport_consolidation = TC-00001`

### Example 2: Drop Consolidation
**Jobs Added:**
- TRJ000004: Pick=Supplier A, Drop=Warehouse B
- TRJ000005: Pick=Supplier C, Drop=Warehouse B
- TRJ000006: Pick=Supplier D, Drop=Warehouse B

**Consolidation Type:** "Drop" (3 picks, 1 drop)

**Result on Legs:**
- All legs: `pick_consolidated = 0` ❌
- All legs: `drop_consolidated = 1` ✅
- All legs: `transport_consolidation = TC-00002`

### Example 3: Both Consolidation
**Jobs Added:**
- TRJ000007: Pick=Warehouse A, Drop=Warehouse B
- TRJ000008: Pick=Warehouse A, Drop=Warehouse B
- TRJ000009: Pick=Warehouse A, Drop=Warehouse B

**Consolidation Type:** "Both" (1 pick, 1 drop)

**Result on Legs:**
- All legs: `pick_consolidated = 1` ✅
- All legs: `drop_consolidated = 1` ✅
- All legs: `transport_consolidation = TC-00003`

### Example 4: Route Consolidation
**Jobs Added:**
- TRJ000010: Pick=[A, B], Drop=[C, D] (multiple legs)
- TRJ000011: Pick=[E], Drop=[F]

**Consolidation Type:** "Route" (multiple picks, multiple drops)

**Result on Legs:**
- All legs: `pick_consolidated = 0` (unchanged)
- All legs: `drop_consolidated = 0` (unchanged)
- All legs: `transport_consolidation = TC-00004`

---

## Manual Override

Users can manually change the checkboxes after automation runs, but the system will re-apply automation when:
- Jobs are re-added to the consolidation
- Run Sheet is created from consolidation
- Consolidation is saved and validated

---

## Troubleshooting

### Checkboxes Not Being Set?

1. **Check Consolidation Type:** Verify `consolidation_type` is set correctly
2. **Check Address Pattern:** Ensure addresses match the consolidation type pattern
3. **Check Leg Status:** Verify legs don't have run_sheets or are in other consolidations
4. **Check Logs:** Look for errors in "Consolidation Automation Error" log

### Wrong Checkboxes Set?

1. **Verify Address Pattern:** Check if addresses actually match the consolidation type
2. **Check Consolidation Type:** The type might be incorrectly determined
3. **Manual Override:** You can manually change checkboxes if needed
