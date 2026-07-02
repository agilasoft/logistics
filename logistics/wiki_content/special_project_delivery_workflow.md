# Special Project — Delivery Workflow

**Step-by-step user guide** for recording cargo deliveries on a [Special Project](welcome/special-projects-module). When a leg is executed correctly, the **Fulfillment** tab updates automatically — **Delivered**, **Remaining**, and **Deliveries** reflect what moved on that programme.

For field-level detail on **Packages** and **Deliveries**, see [Special Project — Fulfillment (Packages & Deliveries)](welcome/special-project-packages).

To open: **Home > Special Projects > Project** (DocType **Special Project**).

---

## Planning vs execution (read this first)

| Document type | Role | Updates Fulfillment on submit? |
| --- | --- | --- |
| **Air Booking**, **Sea Booking**, **Transport Order**, **Project Order**, **Inbound Order** | Planning — captures requirements and charges | **No** |
| **Air Shipment** (series `ASP-…`), **Sea Shipment**, **Transport Job**, **Project Job** | Execution — cargo actually moves | **Yes** |

Submitting a **booking** or **order** alone does **not** post a delivery. You must create and **submit** the matching **execution** document.

---

## Step 1 — Set up packages

1. Open the **Special Project** (e.g. `PROJ-0130`).
2. On **Details**, set **Customer**.
3. Open the **Fulfillment** tab.
4. In **Packages**, add one row per item or part you are tracking (or seed from a linked [Sales Quote](welcome/sales-quote) **Project Products**).
5. Enter **Qty Required** on each tracked row. Leave **Include on Create** unticked for tracked stock; tick it only for always-along rows (tool kits, dunnage) that ride every booking but are not counted in the delivery ledger.
6. **Save**.

---

## Step 2 — Add a service leg

1. Open the **Services** tab.
2. In **Services**, add a row:
   - **Lifecycle Stage** — e.g. Logistics, On-Site
   - **Service Type** — Air, Sea, Transport, Customs, Warehousing, or Special Project
   - **Activity Code** / **Activity Name** — as needed for your programme
3. **Save**.

Each **Services** row is one programme leg. After you create bookings from it, **Order No** and **Job No** on that row link to the planning and execution documents.

---

## Step 3 — Create a booking or order

1. On the Special Project, click **Create → Booking / Order**.
2. In the dialog, each card represents one **Services** row. Expand the card for the leg you need, set any required parameters, then click **Create** when enabled.
3. For Transport, Air, Sea, Inbound, or Project Order legs, the **Shipment lines** dialog opens. Enter the quantity to ship for each tracked package (leave **0** to skip a line). Always-along packages are not listed — they are appended automatically.
4. For **Project Order**, enter **Order Title** when prompted.
5. The system creates the planning document (**Air Booking**, **Sea Booking**, **Transport Order**, **Project Order**, etc.) and links **Order No** on the **Services** row.

When created from the Special Project, **Project** on the new document is set to the programme's ERPNext **Project** (same name as the Special Project when auto-created).

---

## Step 4 — Create and submit the execution document

Complete the leg on the **execution** document, not the planning document.

### Air leg

1. Open the **Air Booking** created in Step 3 and **Submit** it if still draft.
2. Click **Create → Shipment** on the Air Booking (or **View Air Shipment** if one already exists).
3. Open the **Air Shipment** (e.g. `ASP-000325`). Confirm **Project** points to the programme and **Packages** have quantity > 0.
4. **Submit** the Air Shipment.

### Sea leg

1. **Submit** the **Sea Booking**.
2. Create the **Sea Shipment** from the booking (same pattern as air).
3. **Submit** the **Sea Shipment**.

### Transport leg

1. **Submit** the **Transport Order**.
2. Click **Create → Transport Job** on the Transport Order.
3. **Submit** the **Transport Job**.

### Programme task (site work, installation, etc.)

1. From the **Project Order**, create a **Project Job** (or create a **Project Job** linked to the Special Project).
2. Fill **Materials Received** with **Warehouse Item**, **Qty Received**, and optionally **Package Row**.
3. **Submit** the **Project Job**.

---

## Step 5 — Verify Fulfillment

1. Re-open the **Special Project → Fulfillment** tab.
2. Confirm:
   - **Deliveries** — new **Posted** row(s) with **Source Job No** pointing to the execution document (e.g. `ASP-000000325`, `SF000000391`).
   - **Packages** — **Delivered** and **Remaining** updated on the affected lines.
   - Summary at the top of the tab — stage throughput and package table refreshed.
3. If totals look stale after bulk edits, use **Packages → Refresh Delivery Funnel**.

### Regression check (issue #1107)

Use this after deploying a fix or when a submitted Shipment still shows no delivery on the programme:

| Document | Expected on `PROJ-0130` |
| --- | --- |
| **Air Shipment** `ASP-000000325` | **Posted** delivery for `Materials-HCPI`, qty **15**, **Source Job No** = `ASP-000000325` |
| **Sea Shipment** `SF000000391` | **Posted** delivery for `Hllwblck-HCPI`, qty **1000**, **Source Job No** = `SF000000391` |

**Desk:** open **Special Project** `PROJ-0130` → **Fulfillment** → confirm the rows above and updated **Delivered** / **Remaining** on the matching package lines.

**Backfill** (only if the Shipment was submitted before the fix and Deliveries are still empty):

```bash
bench --site <site> execute logistics.special_projects.special_project_packages.repost_freight_shipment_deliveries --args '["ASP-000000325"]'
bench --site <site> execute logistics.special_projects.special_project_packages.repost_freight_shipment_deliveries --args '["SF000000391"]'
```

Re-running is safe: existing **Posted** rows for the same shipment package line are skipped.

---

## Step 6 — Repeat for further legs

For each additional wave, truck, flight, or site delivery:

1. Add or reuse a **Services** row at the correct **Lifecycle Stage**.
2. **Create → Booking / Order** → **Shipment lines** → planning document.
3. Create and **submit** the execution document (Shipment / Transport Job / Project Job).
4. Check **Fulfillment** again.

---

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| **Deliveries** empty after submit | Did you submit the **execution** doc (Shipment / Transport Job / Project Job), not just the booking or order? |
| No **Shipment lines** dialog | Add **Packages** on the Special Project first (or seed from Sales Quote). |
| Delivery still missing on a submitted Shipment | On the execution doc: **Project** = programme; **Packages** qty > 0; lines match **Packages** on the Special Project (same **Warehouse Item** / **Commodity** / **Description**, or **Package Row** set). If those checks pass but **Deliveries** stayed empty, check **Error Log** for `package delivery post` — a failed Special Project save (e.g. Services grid label sync) blocks posting; use the **Regression check** backfill commands after the fix is deployed. |
| **Services** row has **Order No** but no **Job No** | Execution document not created or not submitted yet. |
| **Inbound Order** leg | Receipt auto-posting from inbound/warehouse execution is not fully wired — coordinate with ops or use supported legs (Air/Sea/Transport/Project Job) until extended. |

---

## Related topics

- [Special Project — Fulfillment (Packages & Deliveries)](welcome/special-project-packages)
- [Special Projects Module](welcome/special-projects-module)
- [Air Booking](welcome/air-booking) / [Air Shipment](welcome/air-shipment)
- [Transport Order](welcome/transport-order) / [Transport Job](welcome/transport-job)
- [Sea Booking](welcome/sea-booking) / [Sea Shipment](welcome/sea-shipment)
