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
