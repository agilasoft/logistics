# Milestone Tracking Integration Design

## Overview

Milestone Tracking provides a visual timeline of key operational stages for Jobs, Shipments, and Declarations. It complements the Documents tab by surfacing execution progress in the Dashboard, with document alerts rendered alongside the milestone flow.

---

## 1. Target Doctypes

| Module | DocType | Milestone Model | Current State |
|--------|---------|-----------------|---------------|
| Air Freight | Air Shipment | Job Milestone (Logistics Milestone) | ✅ Implemented – `milestone_html`, `get_milestone_html` |
| Sea Freight | Sea Shipment | Job Milestone (Logistics Milestone) | ✅ Implemented – `milestone_html`, `get_milestone_html` |
| Transport | Transport Job | Job Milestone (Logistics Milestone) | ⚠️ Supported by link filter – needs `milestone_html` + `get_milestone_html` |
| Warehousing | Warehouse Job | Custom (from job item postings) | ✅ Implemented – operation-based flow (Start → Received → Putaway → Pick → Release → End) |
| Customs | Declaration | Job Milestone (Logistics Milestone) | ❌ Not implemented – needs milestones_tab, milestone_html, get_milestone_html |
| Logistics | General Job | Job Milestone (Logistics Milestone) | ❌ Not implemented – optional for multi-leg jobs |

---

## 2. Data Model

### 2.1 Job Milestone (child table / standalone doctype)

| Field | Type | Description |
|-------|------|-------------|
| `job_type` | Link → DocType | Air Shipment, Sea Shipment, Transport Job, Declaration |
| `job_number` | Dynamic Link | Reference to parent document |
| `milestone` | Link → Logistics Milestone | Master milestone (e.g., SF-GATE-IN, SF-LOADED) |
| `status` | Select | Planned, Started, Completed |
| `planned_start` | Datetime | Planned start |
| `planned_end` | Datetime | Planned end |
| `actual_start` | Datetime | Actual start (captured via `capture_actual_start`) |
| `actual_end` | Datetime | Actual end (captured via `capture_actual_end`) |

### 2.2 Logistics Milestone (master)

| Field | Type | Description |
|-------|------|-------------|
| `code` | Data | Short code (e.g., SF-GATE-IN, AF-DEPARTED) |
| `description` | Data | Display name |
| `air_freight` | Check | Applicable to Air Freight |
| `sea_freight` | Check | Applicable to Sea Freight |
| `transport` | Check | Applicable to Transport |

---

## 3. Milestone Flow by Product

**Sea Freight (Logistics Milestone):**
- Booking Received → Booking Confirmed → Cargo Not Ready → Pick-Up Scheduled → Gate-In at Port → Customs Clearance (Export) → Loaded on Vessel → Departed → In-Transit → Arrived → Discharged → Customs Clearance (Import) → Available for Pick-Up → Out for Delivery → Delivered → Closed

**Air Freight:** Same conceptual flow; milestones filtered by `air_freight=1`.

**Transport:** Pick-Up → In-Transit → Delivered; milestones filtered by `transport=1`.

**Declaration (Customs):** Declaration-specific flow:
- Submitted → Under Review → Customs Clearance (Approved) → Released / Rejected

---

## 4. UI Integration

1. **Milestones Tab** – Add `milestones_tab` (label: "Milestones") with `milestone_html` (HTML field) on each target doctype.
2. **get_milestone_html()** – Server method that:
   - Fetches document alerts (missing, overdue, expiring) and renders them at top
   - Loads Job Milestone rows for the parent
   - Builds visual flow (origin → destination with milestone cards)
   - Renders map/timeline with status indicators (Planned / Started / Completed)
3. **Client Script** – On form load and when origin/destination or key dates change, call `get_milestone_html` and refresh `milestone_html` wrapper.

---

## 5. Implementation Phases

| Phase | Task | Doctypes | Status |
|-------|------|----------|--------|
| 1 | Add `milestones_tab`, `milestone_html`, `get_milestone_html` | Transport Job | [x] |
| 2 | Add `milestones_tab`, `milestone_html`, `get_milestone_html` | Declaration | [x] |
| 3 | Extend Logistics Milestone with `customs` flag; add Declaration milestones | Logistics Milestone | [x] |
| 4 | Extend Job Milestone link filter to include Declaration | Job Milestone | [x] |
| 5 | Add milestone view to General Job (optional) | General Job | [ ] |

---

## 6. Declaration-Specific Milestones

Declaration has a different lifecycle (submission → review → clearance). Options:

- **(A)** Use Logistics Milestone with new `customs` flag and codes (e.g., DEC-SUBMITTED, DEC-UNDER-REVIEW, DEC-CLEARED).
- **(B)** Derive milestone status from Declaration fields (`submission_date`, `approval_date`, `actual_clearance_date`, `rejection_date`) and render a simplified flow without Job Milestone rows.

**Recommendation:** **(A)** for consistency; Declaration can optionally create Job Milestone rows for audit trail and manual overrides.

---

## 7. Warehouse Job (Operation-Based)

Warehouse Job uses a different model: milestones are derived from posted operations on job items (staging_posted, receiving_posted, putaway_posted, pick_posted, release_posted). No Job Milestone rows; flow is Start → Received → Putaway → Pick → Release → End (or variants by job type). This remains as-is; no Job Milestone integration needed.

---

*Document Version: 1.0*  
*Last Updated: 2025-02-22*
