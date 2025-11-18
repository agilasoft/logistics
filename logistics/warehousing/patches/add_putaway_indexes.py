import frappe

def execute():
    """Add indexes to support allocate_putaway in warehouse_job.
    
    This patch adds indexes for:
    1. Storage Location - for putaway candidate location queries
    2. Warehouse Stock Ledger - for consolidation and HU location queries
    """
    
    # =============================================================================
    # Storage Location Indexes
    # =============================================================================
    # These indexes support _putaway_candidate_locations queries that filter by:
    # - company, branch, staging_area, storage_type, status
    storage_location_indexes = [
        ["company", "branch", "staging_area", "storage_type"],
        ["company", "branch", "status"],
        ["storage_type", "staging_area", "status"],
    ]
    
    for fields in storage_location_indexes:
        try:
            frappe.db.add_index("Storage Location", fields)
        except Exception as e:
            msg = str(e).lower()
            if "duplicate" in msg or "already exists" in msg:
                pass
            else:
                raise
    
    # =============================================================================
    # Warehouse Stock Ledger Composite Indexes
    # =============================================================================
    # These indexes support allocate_putaway queries:
    # 1. (item, storage_location) - for consolidation bin queries
    # 2. (handling_unit, storage_location) - for HU location queries
    # 3. (handling_unit, item) - for checking if HU contains item
    wsl_indexes = [
        ["item", "storage_location"],
        ["handling_unit", "storage_location"],
        ["handling_unit", "item"],
    ]
    
    for fields in wsl_indexes:
        try:
            frappe.db.add_index("Warehouse Stock Ledger", fields)
        except Exception as e:
            msg = str(e).lower()
            if "duplicate" in msg or "already exists" in msg:
                pass
            else:
                raise

