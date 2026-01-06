from __future__ import annotations
from .common import *  # shared helpers

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

@frappe.whitelist()
def get_contract_charge(contract: str, item_code: str, context: str):
    """Return first matching Warehouse Contract Item row for contract+item+context."""
    if not contract or not item_code:
        return {}
    ctx = (context or "").strip().lower()
    base = {"parent": contract, "parenttype": "Warehouse Contract", "item_charge": item_code}
    filters = dict(base)
    flag = CTX_FLAG.get(ctx)
    if flag:
        filters[flag] = 1
    fields = ["rate", "currency", "uom"]
    rows = frappe.get_all("Warehouse Contract Item", filters=filters, fields=fields, limit=1, ignore_permissions=True)
    if not rows and flag:
        rows = frappe.get_all("Warehouse Contract Item", filters=base, fields=fields, limit=1, ignore_permissions=True)
    return rows[0] if rows else {}

