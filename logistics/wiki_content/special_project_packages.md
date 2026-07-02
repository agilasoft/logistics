# Special Project — Fulfillment (Packages & Deliveries)

The **Fulfillment** tab on a [Special Project](welcome/special-projects-module) is the single place to:

1. List every **Package** (item / part) the programme needs delivered.
2. Record **Deliveries** as they arrive at each step of the project's life cycle.
3. Watch the fulfillment summary (stage throughput and package table) update in real time.

It replaces the older "Site Materials + Receipts" model: the same data is still there, but the summary is now a per-stage funnel instead of a single on-site/short bar.

To open the tab: **Special Project** form → **Fulfillment**.

For a step-by-step walkthrough (Services → Booking/Order → execution submit → verify Fulfillment), see [Special Project — Delivery Workflow](welcome/special-project-delivery-workflow).

## 1. Prerequisites

- **Customer** on the Special Project (required for site address lookup and customer-scoped warehouse items).
- At least one material identifier per package row: **Warehouse Item**, **Commodity**, or **Description**.
- One or more **Lifecycle Stages** with **For Special Project** ticked. The default seed creates: `Pre-Show → Logistics → On-Site → Post-Show → Closed`.
- For seeding from a quote: a linked [Sales Quote](welcome/sales-quote) with **Project Products** lines.
- Optional masters: [Commodity](welcome/commodity), **Warehouse Item** (customer item catalogue), customer **Address** records for **Site**.

## 2. What you see on the tab

| Section | Purpose |
| --- | --- |
| **Fulfillment summary** (HTML above **Packages**) | Stage throughput, filters, and a package table (**Required**, **Delivered**, **Remaining**, **Current Stage**, **Status**). Use **Packages → Refresh Delivery Funnel** to recalculate after bulk edits. |
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
- **Excluded** from delivery posting on **Transport Job** / **Air Shipment** / **Sea Shipment** submit, so it never inflates the funnel.
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
| **Lifecycle Stage** | Which stage of the project this delivery happened in. Auto-filled from the originating **Services** row (or the Special Project's current **Lifecycle Stage**). |
| **Status** | **Posted** counts toward the funnel; **Draft** does not; **Cancelled** is excluded. |
| **Source Job Type** / **Source Job No** | Link to the execution document that posted the delivery (e.g. **Transport Job**, **Air Shipment**, **Sea Shipment**, **Project Job**). |
| **Container No** | Optional container reference for this movement. |

The **Deliveries** grid is **read-only** on the form — rows are posted by the system when execution documents submit. For transport legs, deliveries post on **Transport Job** submit; for air/sea, on **Air Shipment** / **Sea Shipment** submit; for programme tasks, on **Project Job** submit (**Materials Received**).

## 5. Typical workflows

### 5.1 Plan the programme

1. Open **Special Project** and set **Customer**.
2. On **Fulfillment → Packages**, add lines (or seed from Sales Quote). Tick **Include on Create** on rows that should auto-ride every booking (tool kits, dunnage).
3. On **Services**, add rows for Transport, Air, Sea, Inbound, or programme tasks as needed (set **Lifecycle Stage** and **Service Type** on each row).
4. **Save** — check the fulfillment summary on the **Fulfillment** tab for any stalled stages.

See [Special Project — Delivery Workflow](welcome/special-project-delivery-workflow) for the full step-by-step.

### 5.2 Ship part of a package on one transport leg

Example: Package A **900 required**, **200** already delivered in earlier Logistics moves; this truck carries **200** more under the **Logistics** stage.

1. On **Services**, ensure a row exists at the **Logistics** stage with **Service Type = Transport**.
2. Click **Create → Booking / Order**, open the card for that row, click **Create**.
3. In **Shipment lines**, enter quantity per package (e.g. Package A = **200**; leave others **0** to skip). Always-along rows are not listed here — they ride along automatically.
4. The system creates a **Transport Order** with **Packages** for the picked quantities (dimensions/weight/HS code prefilled from the matching package row) plus one **Packages** row per always-along package.
5. **Submit** the Transport Order, then **Create → Transport Job** and **Submit** the Transport Job — posted **Deliveries** are added on the Special Project (+200 for that package, tagged with the **Logistics** **Lifecycle Stage** from the **Services** row). Always-along packages are skipped.
6. Re-open the programme: **Delivered** for Package A now shows **400** (200 prior + 200 this truck).

Repeat for further legs; later stages (On-Site, Post-Show, Closed) update as you create bookings from **Services** rows at those stages.

### 5.3 Refresh the funnel

After bulk edits or imports, use **Packages → Refresh Delivery Funnel** on the Special Project form to recalculate the per-stage delivered quantities and re-render the summary.

### 5.4 Record deliveries from a Project Job

Use this when materials are delivered or consumed against non-freight execution work (e.g. site setup, installation, exhibits handling).

1. Open the **Project Job** (`SPJ-`) and confirm **Special Project** is set. **Project Order** (`SPOR-`) is planning only — it does not post deliveries.
2. Fill the **Materials Received** grid: pick **Warehouse Item**, enter **Qty Received**, optionally set **UOM**, **Container No**, and a direct **Package Row** (1-based index of the row to credit).
3. **Submit** the job.
4. The system appends one **Posted** delivery to the parent Special Project per row, tagged with the **Lifecycle Stage** of the originating **Services** row (or the Special Project's current **Lifecycle Stage**). On-site balances and the fulfillment summary refresh automatically.
5. **Cancel** the job to flip the matching deliveries to **Cancelled** and back out the funnel.

Rows with `Qty Received = 0` are skipped, and rows that match an always-along package (Include on Create) are also skipped to avoid double-counting consumables.

## 6. What happens automatically

| Action | Result |
| --- | --- |
| Save Special Project | Validates rows; recalculates **Delivered** / **Remaining** and the fulfillment summary; auto-fills any missing **Lifecycle Stage** on delivery rows from the originating **Services** row or the project's current **Lifecycle Stage**. Always-along rows stay at 0/0. |
| Sales Quote → Special Project update | Appends new package rows from **Project Products** (does not clear existing rows). |
| **Create → Booking / Order** (Transport / Air / Sea / Inbound / Project Order) | **Shipment lines** dialog lists tracked packages with current **Remaining**; chosen quantities become target **Packages** with dimensions prefilled. Always-along package rows (**Include on Create** ticked) are appended to **Packages** automatically. **Project** is set on the new document. |
| **Transport Job** submit | If **Project** points to the programme, each package line posts one **Posted** delivery (once per package row; duplicates are skipped). Stage is taken from the originating **Services** row. Always-along packages are skipped. **Transport Order** submit does not post deliveries. |
| **Transport Job** cancel | Deliveries sourced from that job are set to **Cancelled** and the summary updates. |
| **Air Shipment** / **Sea Shipment** submit | If **Project** points to the programme, each package line on the shipment posts one **Posted** delivery (once per package row; duplicates are skipped). Lifecycle stage is resolved from the shipment, then the linked **Air Booking** / **Sea Booking**. **Booking** submit does not post deliveries. |
| **Air Shipment** / **Sea Shipment** cancel | Deliveries sourced from that shipment are set to **Cancelled** and the summary updates. |
| **Project Job** submit | If **Special Project** is set, each row of **Materials Received** posts one **Posted** delivery on the parent programme, tagged with the originating **Services** row's stage. **Project Order** submit does not post deliveries. |
| **Project Job** cancel | Deliveries sourced from that job are set to **Cancelled** and the summary updates. |

**Note:** Auto-post on submit applies only to **execution** documents: **Transport Job**, **Air Shipment**, **Sea Shipment**, and **Project Job**. **Air Booking**, **Sea Booking**, **Transport Order**, and **Project Order** are planning — they do not change **Delivered** on the programme. **Inbound Order** receipt posting is not wired yet — use supported legs or coordinate with ops until extended.

## 7. Tips and troubleshooting

- **Shipment lines dialog does not appear** — No package rows yet; add **Packages** or seed from the Sales Quote first.
- **Site dropdown empty** — Set **Customer** on the Special Project; sites are customer addresses.
- **Warehouse Item list empty** — Warehouse items are filtered by customer; create or link items for that customer.
- **Funnel / stage totals look wrong** — A delivery may be tagged with the wrong **Lifecycle Stage**. Review **Deliveries** (source job link) or use **Packages → Refresh Delivery Funnel**.
- **"No Lifecycle Stages configured for Special Projects"** appears in the summary — Open **Lifecycle Stage** master and tick **For Special Project** on at least one stage (default seed handles this).
- **Delivered too high** — Check duplicate **Posted** deliveries or manual deliveries plus auto-posted transport deliveries; cancel incorrect delivery rows or fix **Qty Required**.
- **Duplicate delivery error on save** — Two delivery rows share the same hidden source document and package index; remove or cancel the duplicate.
- **Always-along row appears in the Shipment Lines dialog** — Untick **Include on Create**; ticked rows are intentionally hidden from the picker. Re-tick once the row should auto-ride bookings again.
- **Always-along row keeps showing positive Delivered / Remaining** — Make sure **Include on Create** is ticked so the row is excluded from balance calculation, then save the Special Project to refresh.

## 8. Related topics

- [Special Project — Delivery Workflow](welcome/special-project-delivery-workflow)
- [Special Projects Module](welcome/special-projects-module)
- [Sales Quote](welcome/sales-quote)
- [Transport Order](welcome/transport-order)
- [Sea Booking](welcome/sea-booking) / [Air Booking](welcome/air-booking)
- [Inbound Order](welcome/inbound-order)
- [Commodity](welcome/commodity)
