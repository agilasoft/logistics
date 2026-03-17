# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Bench Command: Create Default Volume UOM Conversion Records
================================================================

This command creates default Dimension Volume UOM Conversion records for
common UOM combinations.

Usage:
    bench --site your-site execute logistics.warehousing.commands.create_default_volume_uom_conversions.create_default_conversions
"""

import frappe

# Aliases to try when resolving UOM names (first existing wins)
DIMENSION_UOM_ALIASES = {
    "CM": ["CM", "Centimeter", "Centimetre"],
    "M": ["M", "Meter", "Metre"],
    "MM": ["MM", "Millimeter", "Millimetre"],
    "IN": ["IN", "Inch"],
    "FT": ["FT", "Foot", "Feet"],
}
VOLUME_UOM_ALIASES = {
    "CBM": ["CBM", "Cubic Meter", "Cubic Metre", "M3", "M³"],
    "CFT": ["CFT", "Cubic Foot", "FT³"],
    "CM3": ["CM3", "CM³", "Cubic Centimeter", "Cubic Centimetre"],
}


def _resolve_uom(preferred: str, aliases: list) -> str | None:
    """Return first UOM name from aliases that exists in the database."""
    for name in aliases:
        if frappe.db.exists("UOM", name):
            return name
    return None


def create_default_conversions():
    """Create default Dimension Volume UOM Conversion records.
    Tries common UOM name variants (e.g. CM vs Centimeter) so it works across sites.
    """
    if not frappe.db.table_exists("Dimension Volume UOM Conversion"):
        return

    # Default conversions: (dimension_key, volume_key) -> factor and description
    default_conversions = [
        ("CM", "CBM", 0.000001, "Convert cubic centimeters to cubic meters (1 cm³ = 0.000001 m³)"),
        ("M", "CBM", 1.0, "Convert cubic meters to cubic meters (1 m³ = 1 m³)"),
        ("MM", "CBM", 0.000000001, "Convert cubic millimeters to cubic meters (1 mm³ = 0.000000001 m³)"),
        ("IN", "CFT", 0.000578704, "Convert cubic inches to cubic feet (1 in³ ≈ 0.000578704 ft³)"),
        ("FT", "CFT", 1.0, "Convert cubic feet to cubic feet (1 ft³ = 1 ft³)"),
        ("CM", "CM3", 1.0, "Convert cubic centimeters to cubic centimeters (1 cm³ = 1 cm³)"),
    ]

    created_count = 0
    skipped_count = 0
    error_count = 0
    silent = not frappe.conf.get("developer_mode", False)

    def log(msg):
        if not silent:
            print(msg)

    for dim_key, vol_key, factor, description in default_conversions:
        try:
            dimension_uom = _resolve_uom(dim_key, DIMENSION_UOM_ALIASES.get(dim_key, [dim_key]))
            volume_uom = _resolve_uom(vol_key, VOLUME_UOM_ALIASES.get(vol_key, [vol_key]))

            if not dimension_uom:
                log(f"  ⚠️  No dimension UOM found for {dim_key}, skipping")
                error_count += 1
                continue
            if not volume_uom:
                log(f"  ⚠️  No volume UOM found for {vol_key}, skipping")
                error_count += 1
                continue

            existing = frappe.db.exists(
                "Dimension Volume UOM Conversion",
                {"dimension_uom": dimension_uom, "volume_uom": volume_uom},
            )
            if existing:
                skipped_count += 1
                continue

            try:
                frappe.get_doc({
                    "doctype": "Dimension Volume UOM Conversion",
                    "dimension_uom": dimension_uom,
                    "volume_uom": volume_uom,
                    "conversion_factor": factor,
                    "description": description,
                    "is_standard": 1,
                    "enabled": 1,
                }).insert(ignore_permissions=True)
                created_count += 1
                log(f"  ✅ Created conversion: {dimension_uom} → {volume_uom} (factor: {factor})")
            except frappe.DuplicateEntryError:
                skipped_count += 1
        except Exception as e:
            error_count += 1
            log(f"  ❌ Error creating conversion {dim_key} → {vol_key}: {str(e)}")
            frappe.log_error(
                f"Error creating Dimension Volume UOM Conversion: {str(e)}",
                "Create Default Conversions Error",
            )

    frappe.db.commit()
    if not silent:
        print(f"\n✅ Default conversions: created={created_count}, skipped={skipped_count}, errors={error_count}")


if __name__ == "__main__":
    create_default_conversions()

