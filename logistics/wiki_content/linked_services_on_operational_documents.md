# Linked Services on Operational Documents

**Linked Services** are subsidiary service legs (Internal Jobs) defined on a [Sales Quote](welcome/sales-quote) and carried through to operational documents — Sea/Air bookings and shipments, Transport orders and jobs. This page describes **what users should expect** for linked-service behaviour across Sea, Air, and Transport.

**Navigation:** Home > Pricing Center > Linked Services on Operational Documents

## Prerequisites

- A [Sales Quote](welcome/sales-quote) with one or more **Linked Services** on the quote (Internal Jobs tab / Linked Services grid).
- Familiarity with quote conversion and charge scope: [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job).

---

## 1. Quote → Booking / Order conversion

When you convert a **full** Sales Quote to operational documents (Regular, One-off, or Project quote types):

| What you should see |
|---------------------|
| **Quote** keeps its `IJ-…` rows on the Services grid (still the owner) |
| **Booking / Order** **reuses** the same `IJ-…` IDs (no new clone numbers) |
| Booking charges keep pointing at those quote-owned `IJ-…` IDs |
| Each Linked Service records a **Usage** row for the booking (Parent Booking) |

Multiple legs of the same service type (e.g. three Transport Linked Services) are all tagged on the booking.

### Blanket call-off

**Blanket call-off** conversions tag only the linked services tied to the **selected charge rows**. The quote keeps all originals for future call-offs.

---

## 2. Linked Service Usage (tracking)

Open a Linked Service (`IJ-…`) to see the **Usage** table: every booking, order, or job that reused that ID, with **Planned/Actual Cost & Revenue per line**.

| Column | Meaning |
|--------|---------|
| Used On Doctype / Name | Consumer document (Air Booking, Transport Order, …) |
| Usage Role | Parent Booking / Satellite Job / Shipment |
| Planned/Actual Cost & Revenue | Totals for **that** consumer only |

The Linked Service header **Rollup** section is the **sum** of all Usage lines.

---

## 3. Services tab (read-only view)

Operational documents expose a **Services** tab with a **read-only** linked services grid:

| Document | Services tab |
|----------|----------------|
| Sea Booking / Sea Shipment | Yes |
| Air Booking / Air Shipment | Yes |
| Transport Order / Transport Job | Yes |

The grid lists Linked Services owned by the document **or** tagged via Usage for that document. **You cannot add or edit rows** on operational Services tabs.

---

## 4. Saving and editing — rows must stay visible

Linked services **remain visible** on the Services tab after save and reload on quote, booking, shipment, and job forms.

---

## 5. Booking → Shipment / Create Internal Job

When you convert booking → shipment, or **Create → Internal Job** (satellite Transport Order, Declaration Order, VAS Order, …):

- The same `IJ-…` ID is **reused** (no clone).
- A new **Usage** row is added (Shipment or Satellite Job).
- Job Type / Job No are shown from the **Usage** table (latest satellite job); they are no longer stored on the Linked Service document itself.

---

## 6. Happy-path example (Air + multi Transport)

1. Create quote **SQU…** with three Transport Linked Services `IJ-A`, `IJ-B`, `IJ-C` and matching Linked charges.
2. Convert quote → **Air Booking** **ABK…**  
   → Quote still owns `IJ-A/B/C`; booking charges still point at them; each IJ has a Usage row for ABK….
3. Create Internal Job → **Transport Order** for `IJ-A`  
   → Same `IJ-A`; Usage gains a Satellite Job line with that order’s Planned/Actual amounts.

---

## Related Topics

- [How Linked Services Are Managed (Proposal)](welcome/how-linked-services-are-managed-proposal) — Time Sensitive dialog as the default manage UX (e.g. Sales Quote)
- [Sales Quote](welcome/sales-quote)
- [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job)
- [Sea Booking](welcome/sea-booking) | [Sea Shipment](welcome/sea-shipment)
- [Air Booking](welcome/air-booking) | [Air Shipment](welcome/air-shipment)
- [Transport Order](welcome/transport-order) | [Transport Job](welcome/transport-job)
- [Recent Platform Updates](welcome/recent-platform-updates)
