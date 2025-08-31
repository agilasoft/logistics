import frappe

CTX_FLAG = {
    "inbound": "inbound_charge",
    "outbound": "outbound_charge",
    "transfer": "transfer_charge",
    "vas": "vas_charge",
    "storage": "storage_charge",
    "stocktake": "stocktake_charge",
}

@frappe.whitelist()
def get_contract_charge(contract: str, item_code: str, context: str):
    """Return first matching Warehouse Contract Item row for a given contract+item+context."""
    if not contract or not item_code:
        return {}

    base = {"parent": contract, "parenttype": "Warehouse Contract", "item_charge": item_code}
    filters = base.copy()
    flag = CTX_FLAG.get(context)
    if flag:
        filters[flag] = 1

    fields = ["rate", "currency", "handling_uom", "time_uom", "storage_uom", "storage_charge"]
    rows = frappe.get_all("Warehouse Contract Item", filters=filters, fields=fields, limit=1, ignore_permissions=True)
    if not rows and flag:
        # fallback: match by contract+item only if no flagged row found
        rows = frappe.get_all("Warehouse Contract Item", filters=base, fields=fields, limit=1, ignore_permissions=True)
    return rows[0] if rows else {}
