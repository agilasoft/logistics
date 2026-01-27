# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Transport API endpoints
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_run_sheet_bundle(name: str):
    """Return a Run Sheet header + its legs (safe fields only)."""
    if not name:
        frappe.throw(_("Run Sheet name required."))

    doc = frappe.get_doc("Run Sheet", name)
    doc.check_permission("read")

    # Fields that exist on Transport Leg DocType
    # Note: signature/signed_by are mapped from drop_signature/drop_signed_by for ePOD
    fields = [
        "name", "date", "transport_job", "vehicle_type",
        "facility_type_from", "facility_from", "pick_address",
        "facility_type_to", "facility_to", "drop_address",
        "start_date", "end_date", "distance_km", "duration_min",
        "drop_signature", "drop_signed_by", "date_signed", "status",
        "actual_distance_km", "actual_duration_min",
    ]

    legs = frappe.get_all(
        "Transport Leg",
        filters={"run_sheet": name, "docstatus": ["<", 2]},
        fields=fields,
        order_by="date asc, modified asc",
        limit_page_length=1000,
    )

    # Map drop_signature/drop_signed_by to signature/signed_by for JS compatibility
    # Also add route_distance_km/route_duration_min as aliases (fallback to distance_km/duration_min)
    for leg in legs:
        leg["signature"] = leg.get("drop_signature")
        leg["signed_by"] = leg.get("drop_signed_by")
        # JS uses route_distance_km/route_duration_min with fallback to distance_km/duration_min
        leg["route_distance_km"] = leg.get("actual_distance_km") or leg.get("distance_km")
        leg["route_duration_min"] = leg.get("actual_duration_min") or leg.get("duration_min")

    return {"doc": doc.as_dict(no_nulls=True), "legs": legs}

