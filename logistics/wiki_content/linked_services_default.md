# Linked Services — Default Behaviour

**Default rule:** manage Linked Services on the [Sales Quote](welcome/sales-quote); view them on bookings, orders, shipments, and jobs.

**Navigation:** Home > Pricing Center > Linked Services — Default Behaviour

This is the standard model for Sea, Air, Transport, and Customs. Operational documents do **not** add or remove Linked Services on their own forms.

---

## The default in one line

| Where | What the user does |
|-------|--------------------|
| **Sales Quote** | **Manage** — add and remove Linked Services (`IJ-…`) |
| **Booking / Order / Shipment / Job** | **View** — read-only **Services** tab; create the satellite job when needed |

---

## What users should expect

1. On the **Sales Quote**, define subsidiary legs as **Linked Services** (and matching charge lines where required).
2. Convert the quote to the main operational document (e.g. Sea Booking, Air Booking, Transport Order, Declaration Order).
3. On that document, open the **Services** tab to **see** the same `IJ-…` legs (owned by the quote and/or tagged via **Usage**). You cannot edit the grid there.
4. Use **Create** (Linked Job / Booking / Order) to start a satellite job for a leg (e.g. Transport Order, Declaration Order). The same `IJ-…` is reused; **Usage** records the new consumer.

---

## Documents that follow this default today

| Role | Documents |
|------|-----------|
| **Manage** | [Sales Quote](welcome/sales-quote) (also Time Sensitive Case via Manage Linked Services) |
| **View** | Sea Booking / Sea Shipment, Air Booking / Air Shipment, Transport Order / Transport Job, [Declaration Order](welcome/declaration-order) / [Declaration](welcome/declaration) |

---

## Related Topics

- [Linked Services on Operational Documents](welcome/linked-services-on-operational-documents) — conversion, Usage, and Services-tab detail
- [How Linked Services Are Managed (Proposal)](welcome/how-linked-services-are-managed-proposal) — proposed Manage dialog UX for Sales Quote
- [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job) — charge scope and billing
- [Sales Quote](welcome/sales-quote)
