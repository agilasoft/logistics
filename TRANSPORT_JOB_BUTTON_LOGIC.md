# How Frappe Determines "Submit" vs "Save" Button Status

## Overview

Frappe uses the `get_action_status()` method in the form toolbar to determine which button to show. The decision follows a priority order.

## Decision Flow

The `get_action_status()` method checks conditions in this order:

1. **"Edit"** - If form is in print view or hidden
2. **"Submit"** - If `can_submit()` returns `true`
3. **"Save"** - If `can_save()` returns `true` (and other conditions)
4. **"Update"** - If `can_update()` returns `true`
5. **"Cancel"** - If `can_cancel()` returns `true`
6. **"Amend"** - If `can_amend()` returns `true`

## Key Methods

### `can_submit()` - Returns `true` when ALL conditions are met:

```javascript
can_submit() {
    return (
        this.get_docstatus() === 0 &&        // Document is in draft (not submitted)
        !this.frm.doc.__islocal &&           // Document is saved (not new/unsaved)
        !this.frm.doc.__unsaved &&           // No unsaved changes
        this.frm.perm[0].submit &&            // User has submit permission
        !this.has_workflow()                 // NO workflow exists
    );
}
```

**Important**: If a workflow exists, `can_submit()` always returns `false`, so the status becomes "Save" instead of "Submit".

### `can_save()` - Returns `true` when:

```javascript
can_save() {
    return this.get_docstatus() === 0;  // Document is in draft
}
```

### `can_update()` - Returns `true` when:

```javascript
can_update() {
    return (
        this.get_docstatus() === 1 &&        // Document is submitted
        !this.frm.doc.__islocal &&           // Document is saved
        this.frm.perm[0].submit &&           // User has submit permission
        this.frm.doc.__unsaved               // Has unsaved changes
    );
}
```

## Status Determination Examples

### Example 1: New Document (Not Saved)
- `docstatus = 0`
- `__islocal = true` (document is new)
- Result: Status = **"Save"** (because `can_submit()` is false due to `__islocal`)

### Example 2: Saved Draft Document (No Workflow)
- `docstatus = 0`
- `__islocal = false` (document is saved)
- `__unsaved = false` (no changes)
- `has_workflow() = false`
- User has submit permission
- Result: Status = **"Submit"** (because `can_submit()` returns true)

### Example 3: Saved Draft Document (With Workflow)
- `docstatus = 0`
- `__islocal = false` (document is saved)
- `__unsaved = false` (no changes)
- `has_workflow() = true` ⚠️
- User has submit permission
- Result: Status = **"Save"** (because `can_submit()` returns false due to workflow)

### Example 4: Saved Draft Document (With Unsaved Changes)
- `docstatus = 0`
- `__islocal = false` (document is saved)
- `__unsaved = true` (has changes) ⚠️
- Result: Status = **"Save"** (because `can_submit()` returns false due to `__unsaved`)

### Example 5: Submitted Document (With Changes)
- `docstatus = 1` (submitted)
- `__unsaved = true` (has changes)
- Result: Status = **"Update"** (because `can_update()` returns true)

## Transport Job Custom Implementation

In Transport Job, we've customized the behavior to:

1. **Show Submit button even when workflow exists**: We check if the document can be submitted (ignoring the workflow check) and show Submit as a secondary button when status is "Save".

2. **Show both Save and Submit**: When status is "Save" but the document can be submitted, we show:
   - **Save** as primary button
   - **Submit** as secondary button

3. **Override logic**:
   ```javascript
   // Check if document can be submitted (regardless of workflow)
   var can_submit_doc = this.get_docstatus() === 0 && 
       !this.frm.doc.__islocal && 
       this.frm.perm[0] && 
       this.frm.perm[0].submit;
   
   // If status is "Save" and document can be submitted, show both buttons
   if (status === "Save" && can_save && can_submit_doc) {
       // Show Save as primary
       this.page.set_primary_action(__("Save"), ...);
       // Show Submit as secondary
       this.page.set_secondary_action(__("Submit"), ...);
   }
   ```

## Summary

The system determines "Submit" vs "Save" based on:
- Document status (draft/submitted/cancelled)
- Whether document is saved (`__islocal`)
- Whether document has unsaved changes (`__unsaved`)
- User permissions
- **Whether a workflow exists** (this is the key factor that prevents "Submit" in standard Frappe)

In Transport Job, we bypass the workflow check to always show the Submit button when the document can be submitted, regardless of workflow existence.
