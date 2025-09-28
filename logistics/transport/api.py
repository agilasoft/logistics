# apps/logistics/logistics/transport/api.py
from typing import List, Dict
import frappe

def _safe_meta_fieldnames(doctype: str) -> set:
    meta = frappe.get_meta(doctype)
    fns = set()
    for df in meta.get("fields", []) or []:
        fn = getattr(df, "fieldname", None) or (df.get("fieldname") if isinstance(df, dict) else None)
        if fn: fns.add(fn)
    return fns

def _first_present(src: Dict, candidates: List[str]):
    for c in candidates:
        if c in src and src[c] not in (None, "", []):
            return src[c]
    return None

@frappe.whitelist()
def build_operations_from_template(template: str) -> List[Dict]:
    """Return rows compatible with 'Transport Order Operation' from the selected template."""
    if not template:
        return []

    tpl = frappe.get_doc("Transport Operations Template", template)

    dest_child_doctype = "Transport Order Operation"
    dest_fields = _safe_meta_fieldnames(dest_child_doctype)

    # Destination → candidate source field names (ordered)
    FIELD_MAP = {
        "operation":     ["operation", "transport_operation", "operation_code", "op", "op_code"],
        "facility_type": ["facility_type", "facilitydoctype", "facility_doctype"],
        "facility":      ["facility", "facility_name", "facility_link"],
        "address":       ["address", "address_name", "address_link"],
        "notes":         ["notes", "instruction", "instructions", "remarks", "description"],
    }

    rows: List[Dict] = []
    for src in (tpl.get("operations") or []):   # child: Transport Job Template Operations
        srcd = src.as_dict()

        # Safe intersection copy (ignores parent/name/idx)
        row = {k: v for k, v in srcd.items()
               if k in dest_fields and k not in {"parent", "parenttype", "parentfield", "name", "idx"}}

        # Fill mapped fields (handles different source fieldnames)
        for dest_key, candidates in FIELD_MAP.items():
            if dest_key in dest_fields:
                val = _first_present(srcd, candidates)
                if val is not None:
                    row[dest_key] = val

        rows.append(row)

    return rows

# apps/logistics/logistics/transport/api.py
from logistics.transport.routing import get_address_coords

@frappe.whitelist()
def get_address_latlon(addr_name: str):
    c = get_address_coords(addr_name)
    return {"lat": c[0], "lon": c[1]} if c else None

@frappe.whitelist()
def get_run_sheet_bundle(name: str):
    """Return a Run Sheet header + its legs (safe fields only)."""
    if not name:
        frappe.throw(_("Run Sheet name required."))

    doc = frappe.get_doc("Run Sheet", name)
    doc.check_permission("read")

    # Only fields that exist on your Transport Leg DocType
    fields = [
        "name", "date", "transport_job", "vehicle_type",
        "facility_type_from", "facility_from", "pick_address",
        "facility_type_to",   "facility_to",   "drop_address",
        "start_date", "end_date", "distance_km", "duration_min",
    ]

    legs = frappe.get_all(
        "Transport Leg",
        filters={"run_sheet": name, "docstatus": ["<", 2]},
        fields=fields,
        order_by="date asc, modified asc",
        limit_page_length=1000,
    )

    return {"doc": doc.as_dict(no_nulls=True), "legs": legs}
