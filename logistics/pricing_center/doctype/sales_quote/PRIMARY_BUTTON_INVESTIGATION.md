# Primary Button Investigation - Sales Quote

## Summary

Investigation of the primary button implementation in the Sales Quote doctype.

## Current State

### Primary Button Behavior
- **Sales Quote is submittable** (`is_submittable: 1` in JSON)
- The primary button is **automatically managed by Frappe's form framework**
- No explicit `frm.page.set_primary_action()` call in the current implementation
- The form uses standard Frappe behavior:
  - **New/Unsaved documents**: Shows "Save" button
  - **Saved Draft (docstatus=0)**: Shows "Submit" button
  - **Submitted documents (docstatus=1)**: Shows "Update" button (if changes made)

### Custom Buttons
The form currently uses `frm.add_custom_button()` to add custom action buttons:
- Create Transport Order
- Create Warehouse Contract
- Create Declaration
- Create Air Shipment
- Create Sea Shipment
- Create Air Booking
- Create Sea Booking
- Create Sales Invoice

These are **secondary buttons** in the Actions menu, not primary buttons.

## Primary Button Location

The primary button is located in the form toolbar and is automatically found by:
```javascript
this.layout.primary_button = this.$wrapper.find(".btn-primary");
```

This happens in `frappe/public/js/frappe/form/form.js` at line 721.

## Comparison with Other Doctypes

### Transport Job Example
Transport Job explicitly sets the primary action in its refresh function:

```javascript
function update_toolbar_buttons(frm) {
    if (frm.is_new() || frm.doc.__islocal) {
        if (frm.page && frm.page.set_primary_action) {
            frm.page.set_primary_action(__("Save"), function() {
                frm.save();
            });
        }
    } else if (frm.doc.docstatus === 0) {
        if (frm.doc.__unsaved) {
            if (frm.page && frm.page.set_primary_action) {
                frm.page.set_primary_action(__("Save"), function() {
                    frm.save();
                });
            }
        } else {
            if (frm.perm && frm.perm[0] && frm.perm[0].submit) {
                if (frm.page && frm.page.set_primary_action) {
                    frm.page.set_primary_action(__("Submit"), function() {
                        frm.savesubmit();
                    });
                }
            }
        }
    } else if (frm.doc.docstatus === 1 && frm.doc.__unsaved) {
        if (frm.perm && frm.perm[0] && frm.perm[0].submit) {
            if (frm.page && frm.page.set_primary_action) {
                frm.page.set_primary_action(__("Update"), function() {
                    frm.save("Update");
                }, "edit");
            }
        }
    }
}
```

## How to Customize Primary Button (If Needed)

If you need to customize the primary button behavior in Sales Quote, you can add this to the `refresh` function:

```javascript
refresh(frm) {
    // Customize primary button based on document state
    if (frm.is_new() || frm.doc.__islocal) {
        frm.page.set_primary_action(__("Save"), function() {
            frm.save();
        });
    } else if (frm.doc.docstatus === 0) {
        if (frm.doc.__unsaved) {
            frm.page.set_primary_action(__("Save"), function() {
                frm.save();
            });
        } else {
            // Show Submit button if user has permission
            if (frm.perm && frm.perm[0] && frm.perm[0].submit) {
                frm.page.set_primary_action(__("Submit"), function() {
                    frm.savesubmit();
                });
            }
        }
    } else if (frm.doc.docstatus === 1 && frm.doc.__unsaved) {
        if (frm.perm && frm.perm[0] && frm.perm[0].submit) {
            frm.page.set_primary_action(__("Update"), function() {
                frm.save("Update");
            }, "edit");
        }
    }
    
    // ... rest of existing refresh code
}
```

## Key Files

1. **JavaScript**: `/home/frappe/frappe-bench/apps/logistics/logistics/pricing_center/doctype/sales_quote/sales_quote.js`
2. **JSON Definition**: `/home/frappe/frappe-bench/apps/logistics/logistics/pricing_center/doctype/sales_quote/sales_quote.json`
3. **Frappe Form Framework**: `/home/frappe/frappe-bench/apps/frappe/frappe/public/js/frappe/form/form.js`
4. **Page API**: `/home/frappe/frappe-bench/apps/frappe/frappe/public/js/frappe/ui/page.js`

## API Reference

### `frm.page.set_primary_action(label, click, icon, working_label)`
- Sets the primary action button in the form toolbar
- **label**: Button text (e.g., "Save", "Submit", "Update")
- **click**: Callback function when button is clicked
- **icon**: Optional icon name
- **working_label**: Optional label to show while action is in progress

### `frm.page.clear_primary_action()`
- Clears the primary action button

## Notes

- The primary button is automatically handled by Frappe if not explicitly set
- Custom primary actions are useful when you need:
  - Custom validation before save/submit
  - Different button labels
  - Custom workflows
  - Conditional button visibility

## Issues to Check

If the primary button is not working correctly, check:
1. Form permissions (read, write, submit)
2. Document state (docstatus)
3. Whether form is dirty (`frm.is_dirty()` or `frm.doc.__unsaved`)
4. Browser console for JavaScript errors
5. Network tab for failed API calls
