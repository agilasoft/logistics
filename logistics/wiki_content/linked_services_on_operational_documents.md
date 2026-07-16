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
| **Quote** keeps its `IJ-…` rows on the Services grid |
| **Booking / Order** gets **new** cloned `IJ-…` rows (new numbers) for subsidiary legs |
| Booking charges point at the **booking-owned** clones (remapped automatically) |

The system **clones** linked services onto the booking — the same pattern as **charge rows**. The quote does **not** lose its legs.

### Blanket call-off

**Blanket call-off** conversions clone only the linked services tied to the **selected charge rows**. The quote keeps all originals for future call-offs.

---

## 2. Services tab (read-only view)

Operational documents expose a **Services** tab with a **read-only** linked services grid:

| Document | Services tab |
|----------|----------------|
| Sea Booking / Sea Shipment | Yes |
| Air Booking / Air Shipment | Yes |
| Transport Order / Transport Job | Yes |

The grid shows subsidiary legs parented to that document. **You cannot add or edit rows** on operational Services tabs.

---

## 3. Saving and editing — rows must stay visible

Linked services **remain visible** on the Services tab after save and reload on quote, booking, shipment, and job forms.

---

## 4. Booking → Shipment / Order → Job

When you convert:

- **Sea Booking → Sea Shipment**
- **Air Booking → Air Shipment**
- **Transport Order → Transport Job**

Linked services are **cloned** onto the child document; the **parent keeps its rows** (like charges). Shipment/job charges are remapped to the child-owned `IJ-…` clones.

---

## 5. Happy-path example (Sea)

1. Create quote **SQU…** with subsidiary Transport linked service `IJ-…-A`.
2. Convert quote → **Sea Booking** **SBK…**  
   → Quote still shows `IJ-…-A`; booking shows new clone `IJ-…-B`.
3. Convert booking → **Sea Shipment**  
   → Booking still shows `IJ-…-B`; shipment shows new clone `IJ-…-C`.

---

## Related Topics

- [Sales Quote](welcome/sales-quote)
- [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job)
- [Sea Booking](welcome/sea-booking) | [Sea Shipment](welcome/sea-shipment)
- [Air Booking](welcome/air-booking) | [Air Shipment](welcome/air-shipment)
- [Transport Order](welcome/transport-order) | [Transport Job](welcome/transport-job)
- [Recent Platform Updates](welcome/recent-platform-updates)
