# Linked Services on Operational Documents

**Linked Services** are subsidiary service legs (Internal Jobs) defined on a [Sales Quote](welcome/sales-quote) and carried through to operational documents — Sea/Air bookings and shipments, Transport orders and jobs. This page describes **what users should expect** after the platform update that standardizes linked-service behaviour across Sea, Air, and Transport.

**Navigation:** Home > Pricing Center > Linked Services on Operational Documents

## Prerequisites

- A [Sales Quote](welcome/sales-quote) with one or more **Linked Services** on the quote (Internal Jobs tab / Linked Services grid).
- Familiarity with quote conversion and charge scope: [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job).

---

## 1. Quote → Booking / Order conversion

When you convert a **full** Sales Quote to operational documents (Regular, One-off, or Project quote types):

| What you should see | What you should **not** see |
|---------------------|-----------------------------|
| The **same** Internal Job numbers (e.g. `IJ-2026-007819`) now parented to the booking or order | A **second** set of duplicate jobs (e.g. `IJ-2026-007820`) created only because of conversion |

The system **re-parents** (transfers) the existing **Linked Service** documents to the new booking or order. It does **not** clone them for a standard full conversion.

### Exception: Blanket call-off

**Blanket call-off** conversions still **clone** linked services. The quote must keep its own linked-service rows for future call-offs. Only the call-off booking receives copies.

---

## 2. Services tab (read-only view)

Operational documents now expose a **Services** tab with a **read-only** linked services grid:

| Document | Services tab |
|----------|----------------|
| Sea Booking / Sea Shipment | Yes |
| Air Booking / Air Shipment | Yes |
| Transport Order / Transport Job | Yes |

The grid shows subsidiary legs linked to that document — service type, job number, routes, agents, costs, and other leg parameters. Rows are loaded from **Linked Service** records in the database.

**You cannot add or edit rows on this tab.** Linked services are maintained on the Sales Quote (or via conversion / **Create Internal Job** flows). The Services tab is a **view** for operations and audit.

---

## 3. Saving and editing — rows must stay visible

**Before the update:** Opening a booking with linked services, editing a field, and saving could make the Services grid **look empty** even though records still existed in the database.

**After the update:** You can edit and save Sea/Air bookings and shipments and Transport orders and jobs as usual. Linked services **remain visible** on the Services tab after save and reload.

If the grid appears empty after a hard refresh, contact your administrator — the underlying **Linked Service** documents may not be parented to that booking/order.

---

## 4. Booking → Shipment / Order → Job

When you convert:

- **Sea Booking → Sea Shipment**
- **Air Booking → Air Shipment**
- **Transport Order → Transport Job**

Linked services **transfer (re-parent)** to the child document. You should see the same legs on the child’s **Services** tab, and they should **persist after save** on the shipment or job form.

---

## 5. What did not change

| Area | Behaviour |
|------|-----------|
| **Sales Quote** | Linked Services grid remains **editable** on the quote — this is the source of truth for leg definition. |
| **Charge scope** | **Linked** charges still reference quote linked services; **Main** charges follow main-service rules. See [Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job). |
| **Special Projects / MICE** | Programme documents use their own service models; see [Special Projects Module](welcome/special-projects-module). |
| **Manual grid editing** | Operational Services tabs are **not** for creating or deleting legs. |

---

## 6. Happy-path example (Sea)

1. Create quote **SQU…** with a main Sea leg and subsidiary Air / Transport / Customs linked services.
2. Convert quote → **Sea Booking** **SBK…**  
   → The same `IJ-…` job numbers appear under the booking (not duplicates).
3. Open **SBK…**, go to **Services** → all linked legs are listed.
4. Change a header field (e.g. customer reference), **Save** → Services tab still shows all rows.
5. Convert booking → **Sea Shipment** → open shipment **Services** tab → rows are present and remain after save.

The same flow applies to **Air Booking / Air Shipment** and **Transport Order / Transport Job**.

---

## 7. Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Duplicate `IJ-…` numbers on quote and booking after conversion | Older behaviour (clone on Regular quotes) or blanket call-off | On new conversions, expect re-parent only for full conversion. For call-offs, duplicates are intentional. |
| Services tab empty after save | Stale desk cache (fixed in current release) | Hard-refresh the form; if still empty, verify **Linked Service** parent fields in desk or ask admin. |
| Wrong service type on a booking’s charges | Charge fetch / separate billings rules | Re-fetch from quotation; see [Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job). |
| No Services tab | Site not migrated / cache | Administrator: run `bench migrate` and restart; clear browser cache. |

---

## Related Topics

- [Sales Quote](welcome/sales-quote)
- [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job)
- [Sea Booking](welcome/sea-booking) | [Sea Shipment](welcome/sea-shipment)
- [Air Booking](welcome/air-booking) | [Air Shipment](welcome/air-shipment)
- [Transport Order](welcome/transport-order) | [Transport Job](welcome/transport-job)
- [Recent Platform Updates](welcome/recent-platform-updates)
