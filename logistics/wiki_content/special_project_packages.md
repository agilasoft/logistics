# Special Project — Fulfillment (Packages & Deliveries)

The **Fulfillment** tab on a [Special Project](welcome/special-projects-module) is the single place to:

1. List every **Package** (item / part) the programme needs delivered.
2. Record **Deliveries** as they arrive at each step of the project's life cycle.
3. Watch the **Delivery Funnel by Lifecycle Stage** summary update in real time.

It replaces the older "Site Materials + Receipts" model: the same data is still there, but the summary is now a per-stage funnel instead of a single on-site/short bar.

To open the tab: **Special Project** form → **Fulfillment**.

## 1. Prerequisites

- **Customer** on the Special Project (required for site address lookup and customer-scoped warehouse items).
- At least one material identifier per package row: **Warehouse Item**, **Commodity**, or **Description**.
- One or more **Lifecycle Stages** with **For Special Project** ticked. The default seed creates: `Pre-Show → Logistics → On-Site → Post-Show → Closed`.
- For seeding from a quote: a linked [Sales Quote](welcome/sales-quote) with **Project Products** lines.
- Optional masters: [Commodity](welcome/commodity), **Warehouse Item** (customer item catalogue), customer **Address** records for **Site**.

## 2. What you see on the tab

| Section | Purpose |
| --- | --- |
| **Summary — Delivery Funnel by Lifecycle Stage** | One row per package, one column per Lifecycle Stage (in stage order). Each cell shows the qty delivered in that stage with a small fill bar (width = qty / required). Updates when you save or change the grids. |
| **Packages** | One row per item / part to deliver. Tick **Include on Create** to mark a row as an always-along package (auto-rides every booking, off the delivery funnel). |
| **Deliveries** | The receipt ledger. Each row records a quantity delivered at a specific **Lifecycle Stage**, optionally linked to the booking/order that produced it. |

**Delivered** and **Remaining** on package rows are calculated — do not type them. The system sets:

- **Delivered** = sum of **Posted** delivery rows matched to that package.
- **Remaining** = `required − delivered` (never below zero).
- Always-along rows (Include on Create ticked) stay at `Delivered = 0` and `Remaining = 0` by design — they are off the delivery ledger.

If delivered exceeds required on a tracked package, you get an orange warning on save; fix packages or deliveries if that is not intentional.

### 2.1 Reading the funnel

The funnel is monotonically non-increasing across stages: a package can never appear in a later stage without first appearing in an earlier one (the workflow enforces this — a delivery is tagged with exactly one stage when posted).

Example, for a package with `Required = 10`:

| Package      | Required | Pre-Show | Logistics | On-Site | Post-Show | Closed |
| ------------ | -------- | -------- | --------- | ------- | --------- | ------ |
| Crate A      | 10       | 0        | 10        | 8       | 0         | 0      |
| Banner Stand | 20       | 0        | 20        | 15      | 0         | 0      |

Read as: 10 Crate A units cleared the **Logistics** stage, 8 of those have reached **On-Site**, 2 are still in Logistics or otherwise outstanding.

## 3. Packages grid

Add one row per item / part you are tracking, plus optional rows for always-along packages (tool kits, dunnage) that ride every booking.

| Field | What to enter |
| --- | --- |
| **Site** | Customer address for this requirement (optional but useful when the same programme has multiple venues). |
| **Commodity** | Active commodity from the master list. |
| **Warehouse Item** | Customer warehouse item (filtered by **Customer** on the programme). |
| **Description** | Free-text line when you are not using commodity or warehouse item. |
| **Include on Create** | Untick (default) for a tracked package. Tick to mark this row as an always-along package. |
| **Qty Required** | Programme need for tracked packages. For always-along rows just put `1` (any value > 0 — the field is required by validation but not used for delivery balances). |
| **UOM** | Unit of measure. |
| **HS Code / Reference No / No of Packs** | Optional shipping metadata — auto-populated on the booking when this row is shipped. |
| **Length / Width / Height / Dimension UOM** | Per-pack dimensions (optional). |
| **Weight / Weight UOM** | Per-pack weight (optional). |
| **Volume / Volume UOM** | Per-pack volume (optional). |
| **Contains Dangerous Goods** | DG flag (optional). |
| **Delivered** / **Remaining** | Read-only balances (see above). Always-along rows display 0 / 0. |

**Rules**

- Each row must have **Warehouse Item**, **Commodity**, or **Description**.
- **Qty Required** must be greater than zero on every row (always-along rows simply put `1`).
- You can mix warehouse items, commodities, and always-along packages on one programme.

### Always-along rows

Tick **Include on Create** when the row is a package that travels on every booking but is not tracked as on-site stock — e.g. a pre-shipment tool kit, a DG kit, dunnage. The row is then:

- **Hidden** from the **Shipment Lines** dialog.
- **Auto-appended** to every new Transport Order, Air Booking, Sea Booking, and Inbound Order created from **Create → Booking / Order**, with all its dimensions, weight, HS code, DG flag, and `no_of_packs` carried over.
- **Excluded** from delivery posting on Transport Order submit, so it never inflates the funnel.
- Marked with an **AA** badge in the summary's Required column; its stage cells show `—`.

### Seed from Sales Quote

When you create or update a Special Project from a Sales Quote (programme link / copy action), **Project Products** on the quote are copied into **Packages**:

- ERPNext **Item** on the quote is matched to a **Warehouse Item** for the programme customer where possible.
- **Quantity** on the product line becomes **Qty Required**.
- Existing package rows with the same warehouse item are not duplicated.

Review and adjust sites and quantities after seeding.

## 4. Deliveries grid

Each Delivery row credits a quantity to a package **in a specific lifecycle stage**.

| Field | What to enter |
| --- | --- |
| **Package Row** | Row number from **Packages** (1 = first row). Helps tie the delivery to one package line. |
| **Commodity** / **Warehouse Item** / **Description** | Copied or entered to match the package; used if package row is blank. |
| **Qty Received** | Quantity for this delivery (must be greater than zero to count). |
| **UOM** | Unit of measure. |
| **Receipt Date** | Date of delivery (defaults to today). |
| **Lifecycle Stage** | Which stage of the project this delivery happened in. Auto-filled from the originating Lifecycle Job (or the Special Project's current stage for manual rows). |
| **Status** | **Posted** counts toward the funnel; **Draft** does not; **Cancelled** is excluded. |
| **Source Job Type** / **Source Job No** | Optional link to Transport Order, Air Booking, Sea Booking, Inbound Order, Project Order, Project Job, etc. |
| **Container No** | Optional container reference for this movement. |

Use **Deliveries** when stock is already on site before any system job exists, or to correct history manually. For transport legs, deliveries are usually created automatically on **Transport Order** submit (see below). Non-freight execution work uses **Project Order** / **Project Job** with a **Materials Received** grid.

## 5. Typical workflows

### 5.1 Plan the programme

1. Open **Special Project** and set **Customer**.
2. On **Fulfillment → Packages**, add lines (or seed from Sales Quote). Tick **Include on Create** on rows that should auto-ride every booking (tool kits, dunnage).
3. Optionally add **Deliveries** for stock already delivered outside the system.
4. Add **Lifecycle** rows for Transport, Air, Sea, or Inbound as needed.
5. **Save** — check the **Delivery Funnel by Lifecycle Stage** summary for any stalled stages.

### 5.2 Ship part of a package on one leg

Example: Package A **900 required**, **200** already delivered in earlier Logistics moves; this truck carries **200** more under the **Logistics** stage.

1. On **Lifecycle**, ensure a row exists at the **Logistics** stage (e.g. **Transport Order**).
2. Click **Create → Booking / Order**, open the card for that row, click **Create**.
3. In **Shipment lines**, enter quantity per package (e.g. Package A = **200**; leave others **0** to skip). Always-along rows are not listed here — they ride along automatically.
4. Continue — the system creates the job with **Packages** for the picked quantities (dimensions/weight/HS code prefilled from the matching package row) plus one **Packages** row per always-along site material.
5. Set the job's **Project** to the programme (same name as the Special Project / ERPNext Project).
6. **Submit** the Transport Order — posted **Deliveries** are added on the Special Project (+200 for that package, **tagged with the Logistics stage** because that's the source Lifecycle Job's stage). Always-along packages are skipped.
7. Re-open the programme: the funnel column **Logistics** for Package A now shows **400** (200 prior + 200 this truck).

Repeat for further legs; later stages (On-Site, Post-Show, Closed) light up as you create bookings from Lifecycle Jobs at those stages.

### 5.3 Refresh the funnel

After bulk edits or imports, use **Packages → Refresh Delivery Funnel** on the Special Project form to recalculate the per-stage delivered quantities and re-render the summary.

### 5.4 Record deliveries from a Project Order / Project Job

Use this when materials are delivered or consumed against non-freight execution work (e.g. site setup, installation, exhibits handling).

1. Open the **Project Order** (`SPOR-`) or **Project Job** (`SPJ-`) and confirm **Special Project** is set.
2. Fill the **Materials Received** grid: pick **Warehouse Item**, enter **Qty Received**, optionally set **UOM**, **Container No**, and a direct **Package Row** (1-based index of the row to credit).
3. **Submit** the order/job.
4. The system appends one **Posted** delivery to the parent Special Project per row, tagged with the Lifecycle Stage of the originating Lifecycle Job row (or the Special Project's current stage). On-site balances and the funnel refresh automatically.
5. **Cancel** the order/job to flip the matching deliveries to **Cancelled** and back out the funnel.

Rows with `Qty Received = 0` are skipped, and rows that match an always-along package (Include on Create) are also skipped to avoid double-counting consumables.

## 6. What happens automatically

| Action | Result |
| --- | --- |
| Save Special Project | Validates rows; recalculates delivered / remaining and per-stage funnel; auto-fills any missing **Lifecycle Stage** on Delivery rows from the originating Lifecycle Job or the project's current stage. Always-along rows stay at 0/0. |
| Sales Quote → Special Project update | Appends new package rows from **Project Products** (does not clear existing rows). |
| **Create → Booking / Order** (Transport / Air / Sea / Inbound) | **Shipment lines** dialog lists tracked packages with current **Remaining**; chosen quantities become target **Packages** with dimensions prefilled. Always-along package rows (Include on Create ticked) are appended to **Packages** automatically. |
| **Transport Order** submit | If **Project** points to the programme, each package line posts one **Posted** delivery (once per package row; duplicates are skipped). Stage is taken from the originating Lifecycle Job. Packages sourced from always-along rows are skipped. |
| **Transport Order** cancel | Deliveries sourced from that order are set to **Cancelled** and the funnel updates. |
| **Project Order** / **Project Job** submit | If **Special Project** is set, each row of **Materials Received** posts one **Posted** delivery on the parent programme, tagged with the originating Lifecycle Job's stage. |
| **Project Order** / **Project Job** cancel | Deliveries sourced from that order/job are set to **Cancelled** and the funnel updates. |

**Note:** Auto-post on submit applies to **Transport Order** (freight) and **Project Order / Project Job** (non-freight execution work). Sea/Air shipment submit and inbound receipt posting are not wired yet — use manual **Deliveries** for those legs until extended.

## 7. Tips and troubleshooting

- **Shipment lines dialog does not appear** — No package rows yet; add **Packages** or seed from the Sales Quote first.
- **Site dropdown empty** — Set **Customer** on the Special Project; sites are customer addresses.
- **Warehouse Item list empty** — Warehouse items are filtered by customer; create or link items for that customer.
- **Funnel column "Logistics" is too high** — A delivery may be tagged with the wrong stage. Open the **Deliveries** grid, fix the **Lifecycle Stage** on the offending row, and save.
- **"No Lifecycle Stages configured for Special Projects"** appears in the summary — Open **Lifecycle Stage** master and tick **For Special Project** on at least one stage (default seed handles this).
- **Delivered too high** — Check duplicate **Posted** deliveries or manual deliveries plus auto-posted transport deliveries; cancel incorrect delivery rows or fix **Qty Required**.
- **Duplicate delivery error on save** — Two delivery rows share the same hidden source document and package index; remove or cancel the duplicate.
- **Always-along row appears in the Shipment Lines dialog** — Untick **Include on Create**; ticked rows are intentionally hidden from the picker. Re-tick once the row should auto-ride bookings again.
- **Always-along row keeps showing positive Delivered / Remaining** — Make sure **Include on Create** is ticked so the row is excluded from balance calculation, then save the Special Project to refresh.

## 8. Related topics

- [Special Projects Module](welcome/special-projects-module)
- [Sales Quote](welcome/sales-quote)
- [Transport Order](welcome/transport-order)
- [Sea Booking](welcome/sea-booking) / [Air Booking](welcome/air-booking)
- [Inbound Order](welcome/inbound-order)
- [Commodity](welcome/commodity)
