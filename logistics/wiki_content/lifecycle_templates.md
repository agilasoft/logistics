# Lifecycle Templates

**Lifecycle Templates** are reusable sets of lifecycle activities. Apply a template to a [Special Project](welcome/special-projects-module) or a [MICE Project](welcome/mice-module) and the system seeds its **Lifecycle Jobs** grid in one click — no more typing the same Pre-Show / Logistics / On-Site / Post-Show / Closed rows on every new programme.

To open the master: **Awesome Bar** → **Lifecycle Template**.

## 1. What a template contains

| Field | Notes |
| --- | --- |
| **Template Name** | The unique name used by the picker. |
| **Enabled** | When unticked, the template is hidden from the Apply dialog. |
| **For Special Project** | Allow this template to be applied to Special Projects. |
| **For Exhibits** | Allow this template to be applied to MICE Projects. |
| **Description** | Free-text notes for whoever picks the template. |
| **Activities** | One row per Lifecycle Job to seed (see below). |

Each row in **Activities** is one Lifecycle Job that will be appended to the target doc:

| Field | What it controls |
| --- | --- |
| **Lifecycle Stage** | Pre-Show / Logistics / On-Site / Post-Show / Closed (or any custom stage flagged for the parent type). |
| **Activity Code** | Optional — narrows the row to a named activity (filtered by the stage). |
| **Activity Name** | Fetched automatically from the Activity Code. |
| **Service Type** | Air / Sea / Transport / Customs / Warehousing / Special Project / MICE. |
| **Sort Order** | Controls the order rows are inserted on the target. |
| **Job Description** | Default description copied onto the seeded Lifecycle Job row. |
| **Service Defaults (optional)** | Light defaults copied to the seeded row when present: Transport Template, Vehicle Type, Load Type, Direction, Air/Sea House Type. Per-deal values (ports, vehicle no., addresses) are deliberately left blank for the user to fill in. |

## 2. Building a template

1. Awesome Bar → **+ New Lifecycle Template**.
2. Give it a clear name (e.g. `Trade Show Standard`, `Container Inbound`, `MICE Move – 3 Day`).
3. Tick **For Special Project** and / or **For Exhibits** depending on where the template should be applicable.
4. Add **Activities** rows in the order you want them to appear. The **Sort Order** column governs the insertion order; rows with the same sort order keep their grid order.
5. **Save**.

Rules enforced on save:

- Tick at least one of **For Special Project** / **For Exhibits**.
- Add at least one **Activity** row.
- Each activity row needs a **Lifecycle Stage** and a **Service Type**.
- If you also pick an **Activity Code**, the system verifies its `lifecycle_stage` matches the row's stage.

## 3. Applying a template to a Special Project or MICE Project

1. Open the **Special Project** or **MICE Project** form (must be saved).
2. Click **Lifecycle → Apply Lifecycle Template** in the toolbar.
3. Pick a template (only templates whose applicability flag matches the parent type are listed).
4. (Optional) Tick **Replace existing lifecycle rows (without job)** to clear out rows that have not yet generated a booking/order. Rows that already have a `job_no` set are always preserved.
5. Click **Apply**.

The result alert summarises what happened:

- **N added** — number of activity rows appended.
- **K removed** — number of empty lifecycle rows removed (replace mode only).
- **L kept (linked)** — number of existing rows preserved because they already have a booking/order linked.
- **M skipped** — activity rows whose Lifecycle Stage is not flagged for the parent type and were therefore skipped.

If any activity rows were skipped, a follow-up orange banner names the offending stages so you can fix the template.

## 4. What seeded rows look like

Each seeded row is created with:

- `lifecycle_activity_status = Not Started`
- Blank `job_type` and `job_no` (so you can later click **Create → Booking / Order** to spawn the actual operational doc)
- Any optional service defaults from the template copied over.

The user fills in the per-deal fields (ports, airline, addresses, etc.) after applying.

## 5. Worked example

Template `Trade Show Standard` (for Special Project), 6 activity rows:

| Stage | Activity | Service | Sort |
| --- | --- | --- | --- |
| Pre-Show | Site survey | Special Project | 1 |
| Logistics | Outbound trucking to venue | Transport | 2 |
| On-Site | Booth set-up | Special Project | 3 |
| On-Site | Last-mile delivery | Transport | 4 |
| Post-Show | Return trucking | Transport | 5 |
| Closed | Final invoice & close | Special Project | 6 |

Applying this to a fresh **Special Project**:

- 6 rows appear in **Lifecycle Jobs** in the listed order, each with the right `Stage` and `Service Type`.
- All rows start at `Not Started`, with `Job No` blank.
- The user fills in the per-row trucking details, then clicks **Create → Booking / Order** on each row to spawn the Transport Order / Project Order, exactly as before.

## 6. Tips and troubleshooting

- **Picker is empty** — the template you want either is **disabled**, or its applicability flag does not match the parent (e.g. you opened the dialog on a MICE Project but the template is `For Special Project` only).
- **"Skipped N activity row(s)..." appears in orange** — an activity row references a Lifecycle Stage that is not flagged for the parent type. Open the stage master and tick the relevant box, or edit the template to use a stage that is flagged.
- **Replace mode wiped fewer rows than expected** — rows with a `job_no` (already linked to a booking/order) are always preserved. Cancel the booking/order first if you want the row removed.
- **Reorder rows on the target** — drag rows in the Lifecycle Jobs grid; templates only seed the initial order via **Sort Order**.

## 7. Related topics

- [Special Project — Fulfillment (Packages & Deliveries)](welcome/special-project-site-materials)
- [Special Projects Module](welcome/special-projects-module)
- [MICE Module](welcome/mice-module)
- [Lifecycle Stage](welcome/lifecycle-stage)
- [Activity Code](welcome/activity-code)
