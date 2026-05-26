#!/usr/bin/env python3
"""
Regenerate storage_location.csv for the DIMI Rack System floor plan.

Usage:
    python3 generate_storage_locations.py > storage_location.csv

Edit RACKS / DEFAULTS below to change configuration. Re-running produces a
3,824-row CSV ready for Frappe Data Import on the "Storage Location" DocType.
"""

# (rack_code, level_count, bay_count) -- bay_count * level_count = pallet positions
RACKS = [
    ("A", 4, 68),  # 272 PP
    ("B", 5, 68),  # 340 PP
    ("C", 5, 68),  # 340 PP
    ("D", 5, 68),  # 340 PP
    ("E", 5, 68),  # 340 PP
    ("F", 4, 60),  # 240 PP
    ("G", 4, 32),  # 128 PP
    ("H", 4, 64),  # 256 PP
    ("I", 5, 64),  # 320 PP
    ("J", 5, 64),  # 320 PP
    ("K", 5, 64),  # 320 PP
    ("L", 5, 64),  # 320 PP
    ("M", 4, 72),  # 288 PP
]

DEFAULTS = {
    "site": "Site-ATN",
    "building": "Building-DIMI",
    "zone": "Zone-MAIN",
    "location_code": "PP01",
    "storage_type": "RACK",
    "branch": "Test-Air-Freight-Company-Test-Branch",
    "company": "Test Air Freight Company",
    "status": "Available",
}

HEADER = [
    "site",
    "building",
    "zone",
    "aisle",
    "bay",
    "level",
    "location_code",
    "storage_type",
    "branch",
    "company",
    "status",
]


def main() -> None:
    print(",".join(HEADER))
    for rack, levels, bays in RACKS:
        aisle = f"Aisle-{rack}"
        for bay in range(1, bays + 1):
            bay_name = f"Bay-{bay:02d}"
            for level in range(1, levels + 1):
                row = [
                    DEFAULTS["site"],
                    DEFAULTS["building"],
                    DEFAULTS["zone"],
                    aisle,
                    bay_name,
                    f"Level-{level}",
                    DEFAULTS["location_code"],
                    DEFAULTS["storage_type"],
                    DEFAULTS["branch"],
                    DEFAULTS["company"],
                    DEFAULTS["status"],
                ]
                print(",".join(row))


if __name__ == "__main__":
    main()
