import frappe

def execute():
    """Add helpful indexes for Warehouse Stock Ledger lookups."""
    doctype = "Warehouse Stock Ledger"

    # one-field indexes (works well with your report filters)
    indexes = [
        ["posting_date"],
        ["item"],
        ["storage_location"],
        ["handling_unit"],
    ]

    for fields in indexes:
        try:
            # add_index is idempotent across Frappe versions that check “IF NOT EXISTS”;
            # this try/except also guards older MariaDBs that might throw duplicate errors.
            frappe.db.add_index(doctype, fields)
        except Exception as e:
            msg = str(e).lower()
            if "duplicate" in msg or "already exists" in msg:
                pass
            else:
                raise
