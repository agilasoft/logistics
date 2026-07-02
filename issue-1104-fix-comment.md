## Fix: Services grid — new rows editable without saving first

### Problem
On **Sales Quote** (and **Special Project**), the **Services** section uses a **virtual grid**. Frappe treats virtual table fields as read-only on first render, so after clicking **Add row** the new line appeared but fields were not editable until the document was saved.

### What we changed
Client-side fix in the form scripts (`sales_quote.js` and `special_project.js`):

1. **Force the grid into edit mode** on draft documents so **Add row** stays visible and the grid is writable.
2. **Refresh grid rows** after that so field controls re-render as editable (virtual fields initially show as read-only).
3. **Auto-open the new row** for editing when a row is added.
4. **Re-apply edit mode after every grid refresh** so the grid does not flip back to read-only.

No server-side change: **Linked Service** / **Special Project Service** records are still created on **save**, as before. This fix only improves the desk UX so users can fill in the row before saving.

### Affected forms
| Form | Services field |
|------|----------------|
| Sales Quote | `linked_services` |
| Special Project | `special_project_services` |

Other modules (Air Freight, Sea Freight, Customs, MICE) do not use this virtual Services grid pattern and are not affected by this issue.

---

### Expected behaviour (after fix)

**Sales Quote & Special Project (draft documents):**

1. Open the form — the Services grid shows existing rows and the **Add row** button.
2. Click **Add row** — a new blank line appears and opens for editing right away.
3. Fill in **Service Type** and related fields (ports, load type, airline, lifecycle stage, etc.) **before** saving.
4. Add more rows — each new row should be editable immediately.
5. **Save** — backing service records are created/updated from what was entered in the grid.
6. After save, rows reload with their service link populated; existing rows remain editable on draft documents.

**Submitted / cancelled documents:** Services grid stays read-only (no add/edit).

### What should no longer happen
- Adding a row and finding fields greyed out or unclickable until the whole document is saved.

### Deploy note
After pulling the change, run asset build / clear cache on the site so the updated JavaScript is loaded:
```bash
bench build --app logistics
bench --site <site> clear-cache
```
