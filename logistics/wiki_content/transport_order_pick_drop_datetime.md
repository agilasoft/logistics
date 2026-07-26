# Transport Order — Pick and Drop Date and Time

**Pick Date and Time** and **Drop Date and Time** are required appointment timestamps on each **Transport Order Leg**. They record when cargo should be picked up and when it should be delivered for that leg.

To access: **Home > Transport > Transport Order** → open or create a leg in the **Legs** table → fields appear under **Pick Address** and **Drop Address**.

## 1. Prerequisites

- [Transport Order](welcome/transport-order)
- At least one leg with pick and drop facilities/addresses

## 2. Where the fields are

| Field | Field name | Location on the leg row |
| --- | --- | --- |
| Pick Date and Time | `pick_datetime` | Pick column, after **Pick Address** |
| Drop Date and Time | `drop_datetime` | Drop column, after **Drop Address** |

These are **Datetime** fields (date + time together). They are per leg, not on the Transport Order header. The header **Scheduled Date** (`scheduled_date`) remains a separate calendar date for the order overall.

## 3. When they are required

- Drafts can be **saved** without pick/drop date-time (same pattern as Pick Mode / Drop Mode).
- On **Submit**, every leg must have both **Pick Date and Time** and **Drop Date and Time**.
- Drop Date and Time must not be earlier than Pick Date and Time on the same leg.

Client and server both validate this before submit.

## 4. How to enter

1. Open the [Transport Order](welcome/transport-order).
2. Go to the **Legs** child table and open a leg row (or add one).
3. Fill pick and drop facility, mode, and address as usual.
4. Set **Pick Date and Time** for the pickup appointment.
5. Set **Drop Date and Time** for the delivery appointment.
6. Save the order; fill any remaining required leg fields before submit.

Use the site’s expected time zone (usually local site time).

## 5. Copy to Transport Job / Transport Leg

When you create a [Transport Job](welcome/transport-job) from the Transport Order:

- Values copy onto each [Transport Leg](welcome/transport-leg) as `pick_datetime` / `drop_datetime`.
- [Transport Job Legs](welcome/transport-job) child rows show the same values (fetched from the Transport Leg).

They are separate from:

- **Pick / Drop Window Start–End** on Transport Leg (facility time windows from Address)
- **Pick Signed At / Drop Signed At** (actual POD timestamps)

## 6. Related Topics

- [Transport Order](welcome/transport-order)
- [Transport Job](welcome/transport-job)
- [Transport Leg](welcome/transport-leg)
- [Transport Order — Inter-module Field Copy](welcome/transport-order-intermodule-field-copy)
