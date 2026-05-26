# Special Project — Site Materials

**Site Materials** tracks what the programme needs on site versus what has actually arrived. Use it on a [Special Project](welcome/special-projects-module) when you run multi-leg moves (trucks, bookings, inbound) and need to know **required**, **on site**, and **short** quantities per item or commodity before planning the next shipment.

To open the tab: **Special Project** form → **Site Materials**.

## 1. Prerequisites

- **Customer** on the Special Project (required for site address lookup and customer-scoped warehouse items).
- At least one material identifier per requirement row: **Warehouse Item**, **Commodity**, or **Description**.
- For seeding from a quote: a linked [Sales Quote](welcome/sales-quote) with **Project Products** lines.
- Optional masters: [Commodity](welcome/commodity), **Warehouse Item** (customer item catalogue), customer **Address** records for **Site**.

## 2. What you see on the tab

| Section | Purpose |
| --- | --- |
| **Summary** | Totals and a table of required / on site / short per line (updates when you save or change grids). |
| **Requirements** | One grid per material with **Include on Create** flag. Untick → tracked requirement (counts toward On Site / Short, appears in the booking dialog). Tick → always-along package (hidden from the dialog, auto-appended to every booking, excluded from receipts). |
| **Receipts** | Movements that increase on-site quantity (manual or posted from jobs). |

**On Site** and **Short** on requirement rows are calculated — do not type them. The system sets:

- **On site** = sum of **posted** receipt quantities matched to that material line.
- **Short** = required − on site (never below zero).
- Always-along rows (Include on Create ticked) stay at `On Site = 0` and `Short = 0` by design — they are off the requirement ledger.

If on site exceeds required on a tracked requirement, you get an orange warning on save; fix requirements or receipts if that is not intentional.

## 3. Requirements (Site Materials grid)

Add one row per material you are tracking, plus optional rows for always-along packages (tool kits, dunnage) that ride every booking.

| Field | What to enter |
| --- | --- |
| **Site** | Customer address for this requirement (optional but useful when the same programme has multiple venues). |
| **Commodity** | Active commodity from the master list. |
| **Warehouse Item** | Customer warehouse item (filtered by **Customer** on the programme). |
| **Description** | Free-text line when you are not using commodity or warehouse item. |
| **Include on Create** | Untick (default) for a tracked requirement. Tick to mark this row as an always-along package. |
| **Qty Required** | Programme need for tracked requirements. For always-along rows just put `1` (any value > 0 — the field is required by validation but not used for balances). |
| **UOM** | Unit of measure. |
| **HS Code / Reference No / No of Packs** | Optional shipping metadata — auto-populated on the booking when this row is shipped. |
| **Length / Width / Height / Dimension UOM** | Per-pack dimensions (optional). |
| **Weight / Weight UOM** | Per-pack weight (optional). |
| **Volume / Volume UOM** | Per-pack volume (optional). |
| **Contains Dangerous Goods** | DG flag (optional). |
| **On Site** / **Short** | Read-only balances (see above). Always-along rows display 0 / 0. |

**Rules**

- Each row must have **Warehouse Item**, **Commodity**, or **Description**.
- **Qty Required** must be greater than zero on every row (always-along rows simply put `1`).
- You can mix warehouse items, commodities, and always-along packages on one programme.

### Always-along rows

Tick **Include on Create** when the row is a package that travels on every booking but is not tracked as on-site stock — e.g. a pre-shipment tool kit, a DG kit, dunnage. The row is then:

- **Hidden** from the **Shipment Lines** dialog.
- **Auto-appended** to every new Transport Order, Air Booking, Sea Booking, and Inbound Order created from **Create → Booking / Order**, with all its dimensions, weight, HS code, DG flag, and `no_of_packs` carried over.
- **Excluded** from receipt posting on Transport Order submit, so it never inflates `qty_on_site`.

Untick it to revert the row to a tracked requirement.

### Seed from Sales Quote

When you create or update a Special Project from a Sales Quote (programme link / copy action), **Project Products** on the quote are copied into **Requirements**:

- ERPNext **Item** on the quote is matched to a **Warehouse Item** for the programme customer where possible.
- **Quantity** on the product line becomes **Qty Required**.
- Existing requirement rows with the same warehouse item are not duplicated.

Review and adjust sites and quantities after seeding.

## 4. Receipts (Site Receipts grid)

Receipts record quantity that has arrived on site.

| Field | What to enter |
| --- | --- |
| **Material Row** | Row number from **Requirements** (1 = first row). Helps tie the receipt to one requirement line. |
| **Commodity** / **Warehouse Item** / **Description** | Copied or entered to match the material; used if material row is blank. |
| **Qty Received** | Quantity for this receipt (must be greater than zero to count). |
| **UOM** | Unit of measure. |
| **Receipt Date** | Date of receipt (defaults to today). |
| **Status** | **Posted** counts toward on site; **Draft** does not; **Cancelled** is excluded. |
| **Source Job Type** / **Source Job No** | Optional link to Transport Order, Air Booking, Sea Booking, Inbound Order, Project Order, Project Job, etc. |
| **Container No** | Optional container reference for this movement. |

Use **Receipts** when stock is already on site before any system job exists, or to correct history manually. For transport legs, receipts are usually created automatically on **Transport Order** submit (see below). Non-freight execution work uses **Project Order** / **Project Job** with a **Materials Received** grid (described in 5.4 below).

## 5. Typical workflows

### 5.1 Plan the programme

1. Open **Special Project** and set **Customer**.
2. On **Site Materials → Requirements**, add lines (or seed from Sales Quote). Tick **Include on Create** on rows that should auto-ride every booking (tool kits, dunnage).
3. Optionally add **Receipts** for stock already delivered outside the system.
4. Add **Lifecycle** rows for Transport, Air, Sea, or Inbound as needed.
5. **Save** — check **Summary** for shortfalls.

### 5.2 Ship part of a requirement on one leg

Example: Item A **900 required**, **200** already on site from past jobs; this truck carries **200** only.

1. On **Lifecycle**, ensure a row exists (e.g. **Transport Order**).
2. Click **Create → Booking / Order**, open the card for that row, click **Create**.
3. In **Shipment lines**, enter quantity per material (e.g. Item A = **200**; leave others **0** to skip). Always-along rows are not listed here — they ride along automatically.
4. Continue — the system creates the job with **Packages** for the picked quantities (dimensions/weight/HS code prefilled from the matching requirement row) plus one **Packages** row per always-along site material.
5. Set the job’s **Project** to the programme (same name as the Special Project / ERPNext Project).
6. **Submit** the Transport Order — posted **Receipts** are added on the Special Project (+200 for that material, with source job and container if present). Always-along packages are skipped.
7. Re-open the programme: Item A shows **on site 400**, **short 500** (200 prior + 200 this truck).

Repeat for further trucks; each submit adds another receipt line with its own **Source Job No**.

### 5.3 Refresh balances

After bulk edits or imports, use **Site Materials → Refresh Balances** on the Special Project form to recalculate **On Site** and **Short** and refresh the summary.

### 5.4 Record receipts from a Project Order / Project Job

Use this when materials are delivered or consumed against non-freight execution work (e.g. site setup, installation, exhibits handling).

1. Open the **Project Order** (`SPOR-`) or **Project Job** (`SPJ-`) and confirm **Special Project** is set.
2. Fill the **Materials Received** grid: pick **Warehouse Item**, enter **Qty Received**, optionally set **UOM**, **Container No**, and a direct **Site Material Row** (1-based index of the requirement row to credit).
3. **Submit** the order/job.
4. The system appends one **Posted** receipt to the parent Special Project per row (`Source Job Type` = `Project Order` or `Project Job`, `Source Job No` = the order/job name). On-site balances refresh automatically.
5. **Cancel** the order/job to flip the matching receipts to **Cancelled** and back out the balances.

Rows with `Qty Received = 0` are skipped, and rows that match an always-along requirement (Include on Create) are also skipped to avoid double-counting consumables.

## 6. What happens automatically

| Action | Result |
| --- | --- |
| Save Special Project | Validates rows; recalculates on site / short; updates summary. Always-along rows stay at 0/0. |
| Sales Quote → Special Project update | Appends new requirement rows from **Project Products** (does not clear existing rows). |
| **Create → Booking / Order** (Transport / Air / Sea / Inbound) | **Shipment lines** dialog lists tracked requirements with current **short**; chosen quantities become target **Packages** with dimensions prefilled. Always-along site material rows (Include on Create ticked) are appended to **Packages** automatically. |
| **Transport Order** submit | If **Project** points to the programme, each package line posts one **Posted** receipt (once per package row; duplicates are skipped). Packages sourced from always-along rows are skipped. |
| **Transport Order** cancel | Receipts sourced from that order are set to **Cancelled** and balances update. |
| **Project Order** / **Project Job** submit | If **Special Project** is set, each row of **Materials Received** posts one **Posted** receipt on the parent programme (once per row; zero-qty rows skipped). |
| **Project Order** / **Project Job** cancel | Receipts sourced from that order/job are set to **Cancelled** and balances update. |

**Note:** Auto-receipt on submit applies to **Transport Order** (freight) and **Project Order / Project Job** (non-freight execution work). Sea/Air shipment submit and inbound receipt posting are not wired yet — use manual **Receipts** for those legs until extended.

## 7. Tips and troubleshooting

- **Shipment lines dialog does not appear** — No requirement rows yet; add **Requirements** or seed from the Sales Quote first.
- **Site dropdown empty** — Set **Customer** on the Special Project; sites are customer addresses.
- **Warehouse Item list empty** — Warehouse items are filtered by customer; create or link items for that customer.
- **On site too high** — Check duplicate **Posted** receipts or manual receipts plus auto-posted transport receipts; cancel incorrect receipt rows or fix **Qty Required**.
- **Duplicate receipt error on save** — Two receipt rows share the same hidden source document and package index; remove or cancel the duplicate.
- **Dashboard** — The programme **Dashboard** tab can show site material counts and shortfall for a quick health check.
- **Always-along row appears in the Shipment Lines dialog** — Untick **Include on Create**; ticked rows are intentionally hidden from the picker. Re-tick once the row should auto-ride bookings again.
- **Always-along row keeps showing positive On Site / Short** — Make sure **Include on Create** is ticked so the row is excluded from balance calculation, then save the Special Project to refresh.

## 8. Related topics

- [Special Projects Module](welcome/special-projects-module)
- [Sales Quote](welcome/sales-quote)
- [Transport Order](welcome/transport-order)
- [Sea Booking](welcome/sea-booking) / [Air Booking](welcome/air-booking)
- [Inbound Order](welcome/inbound-order)
- [Commodity](welcome/commodity)
