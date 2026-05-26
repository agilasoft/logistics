# Warehousing CSV Import — DIMI Rack System (All Transport Network)

This folder contains the CSVs (and a tiny generator) that turn the DIMI Rack
System floor plan into your `Storage Location Configurator` +
`Storage Location` records.

## What's in this folder

| File | Status | Purpose |
|---|---|---|
| `storage_location_configurator.csv` | **READY** (94 rows) | Site + Building + Zone + 13 Aisles + 72 Bays + 5 Levels |
| `generate_storage_locations.py` | **READY** | 1-line generator that emits the 3,824-row Storage Location CSV |
| `storage_location_A-D.csv` | header only — ignore / delete | (leftover from a failed inline-write attempt) |

## Why no pre-built `storage_location.csv`?

The Storage Location CSV is **3,824 rows**. Inlining them into this chat
session would require ~130k output tokens, so I couldn't ship the file
directly. The generator below produces an **identical** CSV in <1 second —
it's literally a one-liner.

## Totals

- 1 Site (`ATN`), 1 Building (`DIMI`), 1 Zone (`MAIN`)
- 13 Aisles (A–M), Bays 01–72, Levels 1–5
- **3,824 Storage Locations** (pallet positions, exactly matching the floor plan)

| Rack | Levels | Bays | Pallet Positions |
|---:|---:|---:|---:|
| A | 4 | 68 | 272 |
| B | 5 | 68 | 340 |
| C | 5 | 68 | 340 |
| D | 5 | 68 | 340 |
| E | 5 | 68 | 340 |
| F | 4 | 60 | 240 |
| G | 4 | 32 | 128 |
| H | 4 | 64 | 256 |
| I | 5 | 64 | 320 |
| J | 5 | 64 | 320 |
| K | 5 | 64 | 320 |
| L | 5 | 64 | 320 |
| M | 4 | 72 | 288 |
| **Total** | | | **3,824** |

## Defaults applied in `storage_location.csv`

| Field | Value |
|---|---|
| `storage_type` | `RACK` |
| `company` | `Test Air Freight Company` |
| `branch` | `Test-Air-Freight-Company-Test-Branch` |
| `status` | `Available` |
| `location_code` | `PP01` (one pallet per bay/level slot) |

To change any of these, open `generate_storage_locations.py` and edit the
`DEFAULTS` dict at the top, then re-run.

## End-to-end workflow

```bash
# 1) Generate the 3,824-row CSV (one command, <1 second)
cd /home/frappe/frappe-bench/apps/logistics/warehousing_import
python3 generate_storage_locations.py > storage_location.csv
wc -l storage_location.csv          # → 3825 (1 header + 3824 rows)

# 2) (optional) clean up the half-baked file
rm storage_location_A-D.csv
```

Then in Frappe (**Data Import → New**, Insert New Records):

1. Upload `storage_location_configurator.csv` → DocType **Storage Location Configurator** → Save → Start Import
2. Upload `storage_location.csv` → DocType **Storage Location** → Save → Start Import

The second import will run as a background job (3,824 rows). When it's done
you'll have every pallet position as a real `Storage Location` ready for
inbound/putaway/picking.

## Naming pattern produced

- Configurator name: `{level}-{code}` → e.g. `Aisle-A`, `Bay-01`, `Level-1`
- Storage Location name: `{site_code}-{building_code}-{zone_code}-{aisle_code}-{bay_code}-{level_code}-{location_code}`
  → e.g. `ATN-DIMI-MAIN-B-05-3-PP01`

## Caveats / open decisions

- **DOUBLE RACK** in the title block is currently modelled as 1 PP per
  bay/level slot (matches the 3,824 total). If you want **2 PP per slot**
  (front/back), I'll add `PP02` rows — the file becomes 7,648 rows.
- **Rooms** from the floor plan are not modelled as Zones (single `MAIN`
  zone). If you want Room 1–5 → Zones, tell me which racks belong in each
  room and I'll regenerate.
- **Branch/Company** default to the only existing branch on the site. Swap
  them in `DEFAULTS` before generating if needed.
