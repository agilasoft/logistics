# Consolidation Suggestion Dialog - Job Filtering Explanation

## Overview
This document explains why some jobs don't appear in the consolidation suggestion dialog and the triggers for each consolidation type.

## Common Reasons Jobs Are Excluded

### 1. **Basic Exclusions (Applied to ALL consolidation types)**

Jobs are excluded if they meet ANY of these conditions:

- ❌ **Not Submitted**: Job `docstatus != 1` (must be submitted)
- ❌ **Wrong Company**: Job doesn't match the consolidation's `company` filter (if provided)
- ❌ **No Transport Legs**: Job has no Transport Legs
- ❌ **Missing Addresses**: Legs don't have `pick_address` or `drop_address`
- ❌ **Load Type Restriction**: Job's Load Type has `can_be_consolidated = False` or `NULL`
- ❌ **Already in Consolidation**: Job is already linked to another Transport Consolidation
- ❌ **Has Run Sheet**: ANY leg of the job has a `run_sheet` assigned
- ❌ **All Legs Consolidated**: All legs are already consolidated (have `pick_consolidated=1`, `drop_consolidated=1`, or `transport_consolidation` link)

### 2. **Consolidation Type Specific Exclusions**

The dialog filters jobs differently based on the selected `consolidation_type`:

---

## Consolidation Type: **Pick**

### When Jobs Are Shown:
✅ Jobs that share the **same Pick Address** with other jobs  
✅ Jobs have **different Drop Addresses** (multiple unique drop addresses)  
✅ Job's `group_legs_in_one_runsheet != 1`

### When Jobs Are Excluded:
❌ Jobs with multiple legs (`legs_count > 1`) (these are Route type only)  
❌ Jobs that don't share a Pick Address with any other job  
❌ Jobs where all jobs in the Pick Address group have identical Drop Addresses (would be "Both" type)

### Example:
- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address1, Drop=Address3
- **Result**: Both jobs shown (same pick, different drops)

- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address1, Drop=Address2
- **Result**: Neither job shown (would be "Both" type, not "Pick")

---

## Consolidation Type: **Drop**

### When Jobs Are Shown:
✅ Jobs that share the **same Drop Address** with other jobs  
✅ Jobs have **different Pick Addresses** (multiple unique pick addresses)  
✅ Job's `group_legs_in_one_runsheet != 1`

### When Jobs Are Excluded:
❌ Jobs with multiple legs (`legs_count > 1`) (these are Route type only)  
❌ Jobs that don't share a Drop Address with any other job  
❌ Jobs where all jobs in the Drop Address group have identical Pick Addresses (would be "Both" type)

### Example:
- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address3, Drop=Address2
- **Result**: Both jobs shown (same drop, different picks)

- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address1, Drop=Address2
- **Result**: Neither job shown (would be "Both" type, not "Drop")

---

## Consolidation Type: **Both**

### When Jobs Are Shown:
✅ Jobs that have **identical Pick AND Drop Address** with other jobs  
✅ Job's `group_legs_in_one_runsheet != 1`  
✅ Job's dynamically determined `consolidation_type == "Both"`

### When Jobs Are Excluded:
❌ Jobs with multiple legs (`legs_count > 1`) (these are Route type only)  
❌ Jobs that don't have identical Pick/Drop combination with other jobs  
❌ Jobs where Pick or Drop addresses differ

### Example:
- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address1, Drop=Address2
- **Result**: Both jobs shown (identical pick and drop)

- Job A: Pick=Address1, Drop=Address2
- Job B: Pick=Address1, Drop=Address3
- **Result**: Neither job shown (different drops, would be "Pick" type)

---

## Consolidation Type: **Route**

### When Jobs Are Shown:
✅ **ALL** consolidatable jobs (same behavior as blank/empty filter)  
✅ Jobs with any number of Transport Legs (1 or more)  
✅ Jobs are included even if they don't have pick/drop addresses  
✅ Multiple Route jobs will all be shown (not limited to 1)

### When Jobs Are Excluded:
❌ Only basic exclusions apply (same as blank filter)  
❌ Jobs that fail basic exclusions (not submitted, already in consolidation, has run_sheet, etc.)

### Example:
- Job A: 3 legs, Pick=[Addr1, Addr2], Drop=[Addr3, Addr4]
- Job B: 2 legs, Pick=[Addr5], Drop=[Addr6]
- Job C: 1 leg, Pick=[Addr1], Drop=[Addr2]
- Job D: 4 legs, Pick=[], Drop=[] (no addresses)
- **Result**: All four jobs shown (all consolidatable jobs, regardless of leg count)

### Note:
Route consolidation type shows **ALL** consolidatable jobs that pass basic exclusions (same behavior as blank/empty filter). The only difference is that jobs are displayed with a "Route" consolidation type badge instead of a blank badge. There is no limit to the number of Route jobs that can be displayed.

---

## Consolidation Type: **Blank/Empty** (No Filter)

### When Jobs Are Shown:
✅ All jobs that pass basic exclusions  
✅ `consolidation_type` is set to blank/empty for all jobs

### When Jobs Are Excluded:
❌ Only basic exclusions apply (no type-specific filtering)

### Example:
- All consolidatable jobs are shown, but their `consolidation_type` badge is blank

---

## Filtering Logic Flow

```
1. Get all submitted jobs (matching company if provided)
   ↓
2. Filter out jobs without legs or addresses
   ↓
3. Filter out jobs already in consolidations
   ↓
4. Filter out jobs with run_sheet assigned
   ↓
5. Filter out jobs where all legs are consolidated
   ↓
6. Filter out jobs with Load Type that doesn't allow consolidation
   ↓
7. Group jobs by Pick/Drop addresses
   ↓
8. Determine dynamic consolidation_type for each job
   ↓
9. Apply consolidation_type filter (if provided):
   - Pick: Same pick, different drops, exclude jobs with multiple legs
   - Drop: Same drop, different picks, exclude jobs with multiple legs
   - Both: Identical pick/drop, exclude jobs with multiple legs
   - Route: Show all consolidatable jobs (same as blank filter)
   - Blank: Show all (no type filter)
   ↓
10. Return filtered jobs
```

---

## Debug Information

The dialog shows diagnostic information to help understand why jobs might be missing:

- **Total jobs found**: All submitted jobs matching company filter
- **Jobs without Transport Legs**: Jobs excluded due to no legs
- **Jobs without Load Type**: Jobs without load_type field
- **Jobs with Load Type that doesn't allow consolidation**: Load Type has `can_be_consolidated = False`
- **Jobs without pick/drop addresses**: Legs missing address information
- **Jobs already in consolidations**: Jobs already linked to another consolidation
- **Jobs with run sheets assigned**: Jobs with legs assigned to run sheets
- **Consolidatable jobs found**: Final count after all filters
- **Consolidation groups found**: Number of address-based groups

---

## Key Code Locations

- **Backend Filtering**: `get_consolidatable_jobs()` in `transport_consolidation.py` (lines 875-1502)
- **Frontend Dialog**: `show_jobs_dialog()` in `transport_consolidation.js` (lines 295-670)
- **Type-Specific Filters**: Lines 1257-1394 in `transport_consolidation.py`

---

## Troubleshooting Missing Jobs

If a job doesn't appear in the dialog, check:

1. ✅ Is the job submitted? (`docstatus = 1`)
2. ✅ Does the job have Transport Legs?
3. ✅ Do the legs have pick_address and drop_address?
4. ✅ Does the Load Type allow consolidation? (`can_be_consolidated = True`)
5. ✅ Is the job already in another consolidation?
6. ✅ Do any legs have a run_sheet assigned?
7. ✅ Are all legs already consolidated?
8. ✅ Does the job match the consolidation_type filter criteria?
9. ✅ If consolidation_type is "Pick/Drop/Both", does the job have only 1 leg (`legs_count <= 1`)?
10. ✅ If consolidation_type is "Route", note that it shows all consolidatable jobs (same as blank filter)
11. ✅ Does the job share addresses with other jobs (for Pick/Drop/Both types)?
