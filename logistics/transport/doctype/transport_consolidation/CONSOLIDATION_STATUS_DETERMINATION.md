# How the System Determines if a Job is Already Consolidated

## Overview

The system uses **multiple checks** at both the **Job level** and **Leg level** to determine if a Transport Job is already consolidated. A job is considered "already consolidated" if it meets ANY of the following conditions.

---

## Check 1: Job-Level Check - Transport Consolidation Job Table

**Location:** `get_consolidatable_jobs()` function, lines 1084-1115

### What it checks:
- Whether the job exists in the `Transport Consolidation Job` child table of ANY Transport Consolidation

### Logic:
```python
# Get all jobs that are in ANY consolidation
existing_consolidations = frappe.get_all(
    "Transport Consolidation Job",
    fields=["transport_job"],
    distinct=True
)
existing_consolidation_jobs = {row["transport_job"] for row in existing_consolidations}
```

### Special Case - Current Consolidation:
If `current_consolidation` parameter is provided:
- Jobs in the **current consolidation** are **ALLOWED** (can be shown again)
- Jobs in **OTHER consolidations** are **EXCLUDED**

```python
if current_consolidation:
    # Get jobs in OTHER consolidations (exclude these)
    existing_consolidations = frappe.get_all(
        "Transport Consolidation Job",
        filters={"parent": ["!=", current_consolidation]},
        fields=["transport_job"],
        distinct=True
    )
```

### Result:
- ✅ **Job is NOT consolidated** if it's not in any consolidation's child table
- ❌ **Job IS consolidated** if it exists in another consolidation's child table
- ✅ **Job is ALLOWED** if it's only in the current consolidation (can be re-added)

---

## Check 2: Leg-Level Check - Consolidation Flags

**Location:** `get_consolidatable_jobs()` function, lines 1134-1171

### What it checks:
For each Transport Leg of the job, the system checks three fields:

1. **`pick_consolidated`** - Checkbox field (0 or 1)
2. **`drop_consolidated`** - Checkbox field (0 or 1)  
3. **`transport_consolidation`** - Link field to Transport Consolidation

### Logic:
```python
for leg in legs:
    leg_consolidation = leg.get("transport_consolidation")
    has_consolidation_flag = (
        leg.get("pick_consolidated") == 1 or 
        leg.get("drop_consolidated") == 1 or
        leg_consolidation  # Any value means consolidated
    )
```

### Special Case - Current Consolidation:
If `current_consolidation` is provided:
- Legs consolidated to the **current consolidation** are **NOT counted** as "already consolidated"
- Legs consolidated to **OTHER consolidations** are **counted** as "already consolidated"

```python
if has_consolidation_flag:
    if current_consolidation and leg_consolidation == current_consolidation:
        # Leg is consolidated to current consolidation - don't count it
        pass
    else:
        # Leg is consolidated to another consolidation - count it
        already_consolidated_legs.append(leg.get("name"))
```

### Result:
- ✅ **Job is NOT consolidated** if it has at least one leg without consolidation flags
- ❌ **Job IS consolidated** if ALL legs have consolidation flags set
- ✅ **Job is ALLOWED** if legs are only consolidated to the current consolidation

---

## Check 3: Run Sheet Assignment

**Location:** `get_consolidatable_jobs()` function, lines 1139-1166

### What it checks:
- Whether ANY Transport Leg has a `run_sheet` field assigned

### Logic:
```python
for leg in legs:
    if leg.get("run_sheet"):
        has_runsheet = True
        break

if has_runsheet:
    # Skip this job - it's already assigned to a run sheet
    continue
```

### Result:
- ❌ **Job IS excluded** if ANY leg has a run_sheet assigned
- ✅ **Job is NOT excluded** if no legs have run_sheet assigned

**Note:** This is a hard exclusion - jobs with run sheets cannot be consolidated.

---

## Summary: Complete Decision Flow

```
For each Transport Job:
│
├─> Check 1: Is job in Transport Consolidation Job table?
│   ├─> YES (in another consolidation) → ❌ EXCLUDE
│   └─> NO or (YES but in current consolidation) → Continue
│
├─> Check 2: Do ALL legs have consolidation flags?
│   ├─> YES (to other consolidation) → ❌ EXCLUDE
│   ├─> YES (to current consolidation) → ✅ ALLOW (can be re-added)
│   └─> NO (at least one leg without flags) → Continue
│
├─> Check 3: Does ANY leg have run_sheet?
│   ├─> YES → ❌ EXCLUDE (hard exclusion)
│   └─> NO → Continue
│
└─> ✅ JOB IS AVAILABLE FOR CONSOLIDATION
```

---

## When Consolidation Flags Are Set

### During Job Addition:
When a job is added to a consolidation, the system sets flags on Transport Legs:

1. **Pick Consolidation:**
   - `pick_consolidated = 1`
   - `drop_consolidated = 0`
   - `transport_consolidation = <consolidation_name>`

2. **Drop Consolidation:**
   - `pick_consolidated = 0`
   - `drop_consolidated = 1`
   - `transport_consolidation = <consolidation_name>`

3. **Both Consolidation:**
   - `pick_consolidated = 1`
   - `drop_consolidated = 1`
   - `transport_consolidation = <consolidation_name>`

4. **Route Consolidation:**
   - `pick_consolidated = 0` (or unchanged)
   - `drop_consolidated = 0` (or unchanged)
   - `transport_consolidation = <consolidation_name>`

### During Job Removal:
When a job is removed from a consolidation:
- Flags are **cleared** by `clear_consolidation_flags_for_removed_jobs()`
- `pick_consolidated = 0`
- `drop_consolidated = 0`
- `transport_consolidation = None`

**Exception:** Flags are NOT cleared if the job is in another consolidation.

---

## Key Code Locations

1. **Job-level check:** `transport_consolidation.py` lines 1084-1132
2. **Leg-level check:** `transport_consolidation.py` lines 1134-1171
3. **Run sheet check:** `transport_consolidation.py` lines 1139-1166
4. **Flag clearing:** `transport_consolidation.py` lines 25-103 (`clear_consolidation_flags_for_removed_jobs()`)
5. **Flag setting:** `transport_consolidation.py` lines 1729-1826 (`_apply_consolidation_automation()`)

---

## Examples

### Example 1: Job Not Consolidated
- Job: TRJ00000190
- In Transport Consolidation Job table: ❌ NO
- Legs with consolidation flags: ❌ NONE
- Legs with run_sheet: ❌ NONE
- **Result:** ✅ **AVAILABLE** for consolidation

### Example 2: Job Consolidated to Another Consolidation
- Job: TRJ00000191
- In Transport Consolidation Job table: ✅ YES (Consolidation TC-00001)
- Legs with consolidation flags: ✅ YES (all legs)
- Legs with run_sheet: ❌ NONE
- **Result:** ❌ **EXCLUDED** (in another consolidation)

### Example 3: Job Removed from Current Consolidation
- Job: TRJ00000233
- In Transport Consolidation Job table: ✅ YES (but only in current consolidation)
- Legs with consolidation flags: ✅ YES (but only to current consolidation)
- Legs with run_sheet: ❌ NONE
- **Result:** ✅ **AVAILABLE** (can be re-added to current consolidation)

### Example 4: Job with Run Sheet
- Job: TRJ00000234
- In Transport Consolidation Job table: ❌ NO
- Legs with consolidation flags: ❌ NONE
- Legs with run_sheet: ✅ YES (at least one leg)
- **Result:** ❌ **EXCLUDED** (has run sheet - hard exclusion)

---

## Important Notes

1. **Run Sheet takes priority:** If ANY leg has a run_sheet, the job is excluded regardless of other checks.

2. **All legs must be consolidated:** A job is only excluded if ALL legs have consolidation flags. If at least one leg is available, the job can be consolidated.

3. **Current consolidation exception:** When viewing jobs for a specific consolidation, jobs that are only in that consolidation are allowed (to support re-adding removed jobs).

4. **Flag clearing is automatic:** When a job is removed from a consolidation and saved, flags are automatically cleared (unless the job is in another consolidation).

5. **Partial consolidation:** Jobs can have some legs consolidated and others not - these jobs will still appear in the list with a "Partial" badge.
