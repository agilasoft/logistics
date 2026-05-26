"""
Generate Data Import CSVs for the DIMI Rack System / All Transport Network warehouse.

Run from the apps/logistics root (or anywhere; paths are relative to this file):
    python logistics/warehousing/data_import/atn_dimi/generate_csvs.py

Outputs (in the same folder):
    01_storage_location_configurator.csv  -> import first
    02_storage_location.csv                -> import second

Tweak SITE / BUILDING / ZONE / BRANCH / COMPANY / STORAGE_TYPE / RACKS below if needed.
"""

import csv
import os

# ---------------------------------------------------------------------------
# Configuration -- edit these to match your environment
# ---------------------------------------------------------------------------

SITE_CODE = "ATN"
SITE_DESC = "All Transport Network"

BUILDING_CODE = "DIMI"
BUILDING_DESC = "DIMI Rack System Building"

ZONE_CODE = "MAIN"
ZONE_DESC = "Main Storage Zone"

# Defaults applied to every Storage Location row
DEFAULT_BRANCH = "Test-Air-Freight-Company-Test-Branch"
DEFAULT_COMPANY = "Test Air Freight Company"
DEFAULT_STORAGE_TYPE = "RACK"
DEFAULT_STATUS = "Available"
DEFAULT_LOCATION_CODE = "01"  # single pallet position per (aisle, bay, level) slot

# Rack layout from the floor plan -- (aisle_code, bays, levels, pallet_positions)
RACKS = [
    ("A", 68, 4, 272),
    ("B", 68, 5, 340),
    ("C", 68, 5, 340),
    ("D", 68, 5, 340),
    ("E", 68, 5, 340),
    ("F", 60, 4, 240),
    ("G", 32, 4, 128),
    ("H", 64, 4, 256),
    ("I", 64, 5, 320),
    ("J", 64, 5, 320),
    ("K", 64, 5, 320),
    ("L", 64, 5, 320),
    ("M", 72, 4, 288),
]

# Optional: zone per rack if you later want one Zone per Room.
# Leave as None to put every rack into the single ZONE_CODE above.
RACK_ZONE = None  # e.g. {"A": "ROOM1", "B": "ROOM1", ...}

# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))


def configurator_rows():
    """Return rows for the Storage Location Configurator CSV."""
    rows = []

    # Site / Building / Zone (single)
    rows.append(("Site", SITE_CODE, SITE_DESC))
    rows.append(("Building", BUILDING_CODE, BUILDING_DESC))
    rows.append(("Zone", ZONE_CODE, ZONE_DESC))

    # Optional extra zones (one per rack) if RACK_ZONE is provided
    if RACK_ZONE:
        seen = set()
        for z in RACK_ZONE.values():
            if z and z not in seen and z != ZONE_CODE:
                seen.add(z)
                rows.append(("Zone", z, f"Zone {z}"))

    # Aisles (one per rack)
    for aisle, bays, levels, pp in RACKS:
        rows.append(("Aisle", aisle, f"Rack {aisle} (LVL{levels}, {pp} PP)"))

    # Bays -- need max bay count across all racks
    max_bays = max(b for _, b, _, _ in RACKS)
    for b in range(1, max_bays + 1):
        code = f"{b:02d}"
        rows.append(("Bay", code, f"Bay {code}"))

    # Levels -- need max levels across all racks
    max_levels = max(l for _, _, l, _ in RACKS)
    for lv in range(1, max_levels + 1):
        rows.append(("Level", str(lv), f"Level {lv}"))

    return rows


def storage_location_rows():
    """Return rows for the Storage Location CSV."""
    rows = []
    for aisle, bays, levels, _ in RACKS:
        zone = (RACK_ZONE or {}).get(aisle, ZONE_CODE)
        for b in range(1, bays + 1):
            bay_code = f"{b:02d}"
            for lv in range(1, levels + 1):
                rows.append({
                    "Site": f"Site-{SITE_CODE}",
                    "Building": f"Building-{BUILDING_CODE}",
                    "Zone": f"Zone-{zone}",
                    "Aisle": f"Aisle-{aisle}",
                    "Bay": f"Bay-{bay_code}",
                    "Level": f"Level-{lv}",
                    "Location Code": DEFAULT_LOCATION_CODE,
                    "Storage Type": DEFAULT_STORAGE_TYPE,
                    "Status": DEFAULT_STATUS,
                    "Branch": DEFAULT_BRANCH,
                    "Company": DEFAULT_COMPANY,
                })
    return rows


def write_configurator_csv():
    path = os.path.join(HERE, "01_storage_location_configurator.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Level", "Code", "Description"])
        for level, code, desc in configurator_rows():
            w.writerow([level, code, desc])
    return path


def write_storage_location_csv():
    path = os.path.join(HERE, "02_storage_location.csv")
    fieldnames = [
        "Site", "Building", "Zone", "Aisle", "Bay", "Level",
        "Location Code", "Storage Type", "Status", "Branch", "Company",
    ]
    rows = storage_location_rows()
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path, len(rows)


if __name__ == "__main__":
    cfg_path = write_configurator_csv()
    loc_path, n = write_storage_location_csv()
    total_pp = sum(pp for _, _, _, pp in RACKS)
    print(f"Wrote {cfg_path}")
    print(f"Wrote {loc_path} ({n} rows)")
    assert n == total_pp, f"Generated {n} locations but rack PP totals = {total_pp}"
    print(f"OK: {n} storage locations match the floor plan total of {total_pp} PP.")
