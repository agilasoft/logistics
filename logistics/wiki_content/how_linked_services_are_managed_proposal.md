# How Linked Services Are Managed (Proposal)

**Proposal:** adopt the **Time Sensitive Case** linked-services UX as the **operational default** for every DocType that must **manage** (add / remove) Linked Services — starting with [Sales Quote](welcome/sales-quote).

This page is a **product / UX proposal**. It is not yet the live behaviour for Sales Quote. Current conversion and usage rules remain described in [Linked Services on Operational Documents](welcome/linked-services-on-operational-documents).

**Navigation:** Home > Pricing Center > How Linked Services Are Managed (Proposal)

## Goal

One consistent way for users to manage Linked Services wherever the document **owns** them and must allow create / remove:

| Pattern | Meaning |
|---------|---------|
| **Manage** | User can add and remove Linked Services for this document |
| **View** | User only sees Linked Services (owned or via Usage); no add / remove on the form |

**Time Sensitive Case** already implements the **Manage** pattern via a dedicated **Services** dialog. This proposal makes that the default for other manage-capable DocTypes (especially Sales Quote), instead of an editable child grid.

---

## 1. Current state (how it works today)

| Document | Role | How linked services are managed |
|----------|------|----------------------------------|
| **Time Sensitive Case** | Owner / manage | Toolbar **Services** → **Manage Linked Services** dialog (add / remove). Services tab is a **read-only** mirror. |
| **Sales Quote** | Owner / manage | Editable **Linked Services** grid (Add Row / delete on the form). |
| **Sea / Air Booking & Shipment**, **Transport Order & Job**, etc. | Consumer / view | **Services** tab is **read-only**. Rows appear from quote conversion or Linked Service **Usage**. |

So today users learn two different “manage” UIs (dialog vs grid), while “view” documents already share a read-only Services tab.

---

## 2. Proposed default (Time Sensitive pattern)

### Manage DocTypes (example: Sales Quote)

For DocTypes that need to **manage** Linked Services:

1. Form toolbar exposes a single **Services** action.
2. **Services** opens the **Manage Linked Services** dialog (same composition as Time Sensitive Case):
   - Card / list of linked services (module icon, document link, job pill, remove).
   - **Add Linked Service** row: service type dropdown + **Add Service**.
   - Footer: **Close** + linked-service count.
3. The form **Services** tab (or Linked Services grid) stays **read-only** — a mirror of what the dialog manages, not a second editor.
4. Mutations go through document-specific APIs (add / remove), not through editing virtual grid rows and saving.

**Sales Quote** is the primary rollout target after Time Sensitive Case.

### View DocTypes (bookings, shipments, jobs)

No change to the ownership / Usage model:

- Services tab remains **read-only**.
- Optionally, the same dialog can open in **view-only** mode (list + Close, no Add / Remove) for visual consistency — optional, not required for this proposal.

---

## 3. User flows (proposed)

### Add a linked service

1. Open the manage document (e.g. Time Sensitive Case or, after rollout, Sales Quote).
2. Click **Services** on the toolbar.
3. Under **Add Linked Service**, choose a **Service Type**.
4. Click **Add Service**.
5. Confirm the new `IJ-…` appears in the list and on the Services tab after reload.

Document-specific rules still apply (for example: Time Sensitive Case allows **one service per type**; Sales Quote may continue to allow multiple legs of the same type if product rules require it).

### Remove a linked service

1. Open **Services**.
2. Click the remove (trash) control on the row.
3. Confirm.
4. Owned Linked Services are deleted (or unlinked per Usage rules); the list and Services tab refresh.

Status and dependency guards (e.g. cannot remove the last service on an activated Time Sensitive Case) remain on the server.

---

## 4. Why standardise on this pattern

- **One mental model** for every DocType that manages Linked Services.
- **Clearer hierarchy**: dialog for actions; tab for scan / audit.
- **Safer mutations**: explicit add / remove APIs instead of syncing an editable virtual grid on save.
- **Better fit for short lists** (typically a few service legs) than a spreadsheet-style child table.
- Aligns Sales Quote and Time Sensitive Case with the same enterprise dialog quality (module icons, list cards, footer count).

---

## 5. Rollout proposal

| Phase | Scope | Outcome |
|-------|--------|---------|
| **Done** | Time Sensitive Case | Reference implementation (dialog + read-only Services tab). |
| **Next** | Sales Quote | Replace editable grid manage UX with the same **Services** dialog; keep quote ownership and conversion behaviour. |
| **Later** | Other manage DocTypes (if any) | Reuse shared dialog module; DocType-specific add / remove rules via options / APIs. |
| **Optional** | View DocTypes | Shared view-only dialog shell, or keep tab-only. |

### Implementation notes (engineering)

- Extract the dialog from `logistics.time_sensitive` into a shared helper (e.g. `logistics.show_linked_services_dialog(frm, options)`).
- Keep DocType rules in options / whitelist methods: one-per-type, owned delete vs Usage unlink, status guards.
- Update [Linked Services on Operational Documents](welcome/linked-services-on-operational-documents) once Sales Quote ships the new UX (this proposal page can then move from “proposal” to “standard”).

---

## 6. Out of scope (for this proposal)

- Changing quote → booking **ownership / reuse / Usage** semantics (covered elsewhere).
- Making operational bookings add arbitrary Linked Services by default (they remain **view** unless a separate product decision says otherwise).
- Redesigning charge-line scope or Separate Billings rules.

---

## Related Topics

- [Linked Services on Operational Documents](welcome/linked-services-on-operational-documents)
- [Sales Quote](welcome/sales-quote)
- [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job)
- [Recent Platform Updates](welcome/recent-platform-updates)
