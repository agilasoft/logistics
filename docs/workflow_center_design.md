# Workflow Center — Design Document

**Status:** Draft  
**Target platform:** Frappe / ERPNext  
**Purpose:** Extend workflow monitoring with SLA-style due windows, configurable alert thresholds, and a unified cockpit for operators and managers.

---

## 1. Vision & Goals

**Workflow Center** is a companion app that makes **who is waiting on what** visible, **how long** each state is allowed to last explicit, and **when to escalate** predictable—without replacing Frappe’s built-in Workflow engine.

### Primary goals

- Attach **time budgets** (hours or days) to **Workflow States** so documents can be classified as **On track**, **At risk**, or **Overdue** relative to when they entered the current state.
- Centralize **global alert semantics** (information / warning / critical) in **Workflow Center Settings** so notifications stay consistent across doctypes.
- Provide a **Workflow Center** workspace (desk page) that acts as a **control tower**: one place to see actionable workflow items for the current user and their teams.

### Non-goals (initial release)

- Replacing or reimplementing the core `Workflow` / `Workflow State` transition engine.
- Guaranteed real-time updates without refresh (polling or socket hooks can be a later enhancement).

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Workflow Center (Desk Page)                  │
│  My queue · Team queues · Overdue · At risk · Filters · KPIs    │
└────────────────────────────┬────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ SLA engine  │    │ Alert / notify   │    │ Query / index layer │
│ (computed)  │    │ (Email / ToDo /  │    │ (reports, list API) │
│             │    │  in-app)         │    │                     │
└──────┬──────┘    └────────┬─────────┘    └──────────┬──────────┘
       │                    │                       │
       └────────────────────┼───────────────────────┘
                            ▼
              ┌─────────────────────────┐
              │ Frappe Workflow + docs   │
              │ (workflow_state, modified)│
              └─────────────────────────┘
```

**New app package:** `workflow_center` (installable Frappe app).

**Integration points:**

- **Custom fields** on `Workflow State` (and optionally child tables or linked config if core customization is restricted—see §4).
- **Server-side hooks** on document `on_update` / workflow actions where needed to refresh derived fields or enqueue notifications.
- **Scheduled jobs** for periodic SLA evaluation and digest emails.

---

## 3. Core Concepts

### 3.1 State dwell time

For a submitted document with an active workflow:

- **Entered current state at:** derived from workflow history or a maintained timestamp (see §6).
- **Allowed duration:** from Workflow State (`hours` or `days` per state).
- **Elapsed:** now − entered_at (business calendar optional in later phase).

### 3.2 Severity bands (global + overrides)

Using **Workflow Center Settings**:

| Band        | Typical meaning                                      |
|------------|-------------------------------------------------------|
| Information | Early awareness; no urgency                          |
| Warning     | Approaching limit; should appear in “at risk” lists  |
| Critical    | Imminent breach or breached; escalate                |

**Overdue** is defined as: elapsed **>** allowed duration for the current state.

Bands **before** overdue are computed as percentages or fixed offsets of the allowed duration (configurable in settings—see §5).

---

## 4. Data Model

### 4.1 Workflow State — custom fields

Extend **Workflow State** (DocType: `Workflow State`) with:

| Field | Type | Description |
|-------|------|-------------|
| `wc_sla_enabled` | Check | If unset, no SLA / overdue for this state. |
| `wc_sla_unit` | Select | `Hours` \| `Days` |
| `wc_sla_value` | Float | Duration allowed in current state before overdue. |
| `wc_count_business_time` | Check (optional, phase 2) | Use working hours / calendar. |
| `wc_notes` | Small Text | Operator-facing hint (“e.g. customs clearance target”). |

**Validation:** if `wc_sla_enabled`, `wc_sla_value` > 0 and unit required.

**Rationale:** SLA is tied to **state**, not global workflow, because different states have different natural durations.

### 4.2 Workflow Center Settings — single DocType

**DocType:** `Workflow Center Settings` (Single)

| Section | Fields | Description |
|---------|--------|-------------|
| General | `enabled`, `default_timezone`, `digest_time` | Master switch; scheduling. |
| Thresholds | `info_percent` or `info_days_before`, `warning_percent`, `critical_percent` | Map elapsed/allowed ratio to info/warning/critical (see §5). |
| Notifications | toggles per channel | `email`, `in_app`, `todo_task` |
| Assignment | `default_role_for_escalation`, `manager_field_pattern` (optional) | Fallback routing. |
| Digest | `daily_digest_enabled`, `recipients` (Role / User multi) | Summary emails. |

**Alternative (more explicit):** three duration fields—`info_before_due_days`, `warning_before_due_days`, `critical_before_due_days`—interpreted as “notify when remaining time ≤ X” (for day-based SLAs). The design should pick **one** model in implementation; recommended v1: **percentage of allowed duration** for simplicity across hours and days.

### 4.3 Workflow Center — per-document derived data (implementation options)

**Option A — Virtual / on-the-fly (v1 friendly):**  
Compute SLA status when loading the dashboard via SQL / document methods. No schema change on business doctypes.

**Option B — Persistent fields (scale / reporting):**  
Add a small set of custom fields on key doctypes via **Customize Form** or **Property Setter**—not ideal for a generic app.

**Option C — Generic registry DocType (recommended for a productized app):**  
**Workflow Center Item** (child of nothing; standalone table):

| Field | Type | Description |
|-------|------|-------------|
| `reference_doctype`, `reference_name` | Link / Dynamic | Document in workflow. |
| `workflow` | Link | Workflow applied. |
| `current_state` | Data | Cached state. |
| `state_entered_at` | Datetime | When current state started. |
| `allowed_seconds` | Int | Denormalized from Workflow State. |
| `severity` | Select | `ok` \| `info` \| `warning` \| `critical` \| `overdue` |
| `last_computed_at` | Datetime | For staleness checks. |
| `assigned_to` | Link User | Optional cache. |

Maintained by hooks + scheduled reconcile job. Enables fast list views and charts without scanning all business tables.

**Recommendation:** Start with **Option A** for MVP; move to **Option C** if performance or cross-doctype reporting demands it.

---

## 5. Threshold Logic (Settings)

**Inputs:** `allowed_duration`, `elapsed`, settings.

**Compute ratio:** `r = elapsed / allowed_duration` (0–1+).

**Example v1 rules (configurable):**

- `overdue` if `r > 1`
- `critical` if `r >= critical_threshold` (e.g. 0.9) and not overdue
- `warning` if `r >= warning_threshold` (e.g. 0.75)
- `info` if `r >= info_threshold` (e.g. 0.5)
- else `ok`

**Edge cases:**

- SLA disabled for state → treat as `ok` / exclude from overdue widgets.
- Missing `state_entered_at` → show as **Unknown** and optionally exclude from overdue KPIs until backfilled.

---

## 6. When did the document enter the current state?

Reliable dwell time requires a **timestamp**. Options:

1. **Parse Workflow Action Master / version history** if available and complete (can be fragile across Frappe versions).
2. **Maintain `state_entered_at`** on the **Workflow Center Item** row whenever `workflow_state` changes (hook on `on_update` comparing previous vs new state).
3. **Optional custom field** on high-volume doctypes: `workflow_state_entered_on` (single datetime), maintained by server script—highest accuracy, higher rollout cost.

**Recommendation:** Implement **(2)** in the registry table; offer **(3)** as documented optional enhancement for sites that need legal-grade audit.

---

## 7. Workflow Center Desk Page (Cockpit)

**Route:** `/app/workflow-center` (or workspace + page bundle).

### 7.1 Layout (wireframe-level)

1. **Header KPIs** (cards)  
   - My open items  
   - Overdue (mine / team)  
   - Due in 24h / 48h  
   - Critical & warning counts  

2. **Primary list** (filterable Data Table or Frappe List View)  
   Columns: Document, Title/subject, Doctype, Workflow, Current state, **Time in state**, **Allowed**, **Remaining / % consumed**, **Severity**, Assignee, Last action, Link.

3. **Saved filters & segments**  
   - My assignments  
   - My team (by role / reporting line—if data exists)  
   - By doctype / workflow  
   - Overdue only / At risk only  

4. **Detail side panel or quick view**  
   - Timeline of workflow transitions (if available)  
   - One-click open document  
   - Optional: “Add comment” / “Reassign” (if permissions allow)  

5. **Charts (phase 1.5)**  
   - Aging by state  
   - Overdue trend (7/30 days)  
   - Heatmap by doctype  

### 7.2 Permissions

- **Workflow User:** sees documents they are allowed to read that participate in workflow (respect existing `has_permission`).
- **Workflow Manager:** broader team/org view (role-based).
- **System Manager:** configure settings and thresholds.

### 7.3 Performance

- Paginated API with server-side filters.
- Debounced search; index on `(severity, reference_doctype, assigned_to)` if using registry table.

---

## 8. Alerts & Notifications

### 8.1 Event types

- Transition into **warning** / **critical** / **overdue** (edge-triggered: only on crossing boundary).
- **Daily digest** listing new overdue and still-overdue items.

### 8.2 Channels

| Channel | Behavior |
|---------|----------|
| In-app | Notification log + badge on Workflow Center |
| Email | Template with deep link to document and Workflow Center |
| ToDo | Create assigned task on critical/overdue (optional) |

### 8.3 Noise control

- **Cooldown** per document+state (e.g. don’t email every hour while still overdue).
- **Batch** multiple items into one digest.
- User-level **subscribe / unsubscribe** (phase 2) per workflow or doctype.

---

## 9. Additional Features (Recommended Roadmap)

### 9.1 Phase 1 (MVP)

- Workflow State SLA fields + Settings DocType  
- Workflow Center page with **my** and **all I can see** lists  
- Computed severity + overdue labels  
- Basic in-app notification on threshold cross  

### 9.2 Phase 2

- **Workflow Center Item** registry + reconcile job  
- Email digest + ToDo escalation  
- Team views and role-based dashboards  
- Export CSV / Excel  

### 9.3 Phase 3

- **Business calendars** (working hours, holidays)  
- **SLA pause** reasons (e.g. “Waiting on customer”) via substate or child table  
- **SLA policies** per doctype overriding state defaults  
- REST API for external monitoring (PagerDuty, Slack webhooks)  

### 9.4 Quality & ops

- **Patch** to add custom fields idempotently  
- **Test records** and fixtures for CI  
- **Documentation:** install guide, how to set hours per state, how thresholds work  
- **Permission tests** ensuring no leakage across companies in multi-tenant sites  

---

## 10. Security & Compliance

- All queries must respect **Frappe permission model** (`frappe.has_permission`).
- No exposure of document names the user cannot read.
- Settings DocType restricted to **System Manager** (or configurable role).
- Audit: log threshold changes in **Version** for `Workflow Center Settings`.

---

## 11. Open Questions

1. Should **same document** in multiple parallel workflows be supported? If yes, registry key is `(doctype, name, workflow)` not just `(doctype, name)`.
2. Do we treat **draft** documents as in-workflow for the cockpit, or only **submitted**?
3. Preferred v1 threshold model: **percent of SLA** vs **fixed days before due**?
4. Which **first-party doctypes** (besides generic) should get optimized columns in the cockpit for the logistics app?

---

## 12. Deliverables Checklist (Implementation)

- [ ] New app `workflow_center` with `hooks.py`, `modules.txt`, `workflow_center/config/desktop.py` (workspace)
- [ ] Custom fields on `Workflow State` via `fixtures` or `after_install` patch
- [ ] DocType `Workflow Center Settings` (Single)
- [ ] Desk **Page** / workspace **Workflow Center**
- [ ] Server module: SLA computation, notification triggers, (optional) registry maintenance
- [ ] Scheduled task: digest + reconciliation
- [ ] Documentation in app `README` (short) + this design in `docs/`

---

*End of design document.*
