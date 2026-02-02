#!/usr/bin/env python3
"""
Quick script to get current stock for an item
Usage: bench --site <site> execute logistics.get_item_stock.get_current_stock --args "['EPH-ACC-002-ELCTWRLDPH']"
"""
import frappe

@frappe.whitelist()
def get_current_stock(item_code):
    """
    Get current stock availability for an item by summing the latest end_qty 
    for each location/handling_unit/batch/serial combination
    """
    
    # Get the latest end_qty for each unique combination
    sql = """
        SELECT
            l.storage_location,
            l.handling_unit,
            l.batch_no,
            l.serial_no,
            l.end_qty AS available_qty,
            l.posting_date AS last_transaction_date,
            wi.item_name
        FROM `tabWarehouse Stock Ledger` l
        INNER JOIN (
            SELECT
                l1.storage_location,
                l1.handling_unit,
                l1.batch_no,
                l1.serial_no,
                l1.end_qty,
                l1.posting_date,
                l1.creation,
                l1.name
            FROM `tabWarehouse Stock Ledger` l1
            INNER JOIN (
                SELECT
                    storage_location,
                    handling_unit,
                    batch_no,
                    serial_no,
                    MAX(posting_date) AS max_date,
                    MAX(creation) AS max_creation
                FROM `tabWarehouse Stock Ledger`
                WHERE item = %s
                GROUP BY storage_location, handling_unit, batch_no, serial_no
            ) max_dates ON l1.storage_location = max_dates.storage_location
                AND IFNULL(l1.handling_unit, '') = IFNULL(max_dates.handling_unit, '')
                AND IFNULL(l1.batch_no, '') = IFNULL(max_dates.batch_no, '')
                AND IFNULL(l1.serial_no, '') = IFNULL(max_dates.serial_no, '')
                AND l1.posting_date = max_dates.max_date
                AND l1.creation = max_dates.max_creation
                AND l1.item = %s
        ) latest ON l.storage_location = latest.storage_location
            AND IFNULL(l.handling_unit, '') = IFNULL(latest.handling_unit, '')
            AND IFNULL(l.batch_no, '') = IFNULL(latest.batch_no, '')
            AND IFNULL(l.serial_no, '') = IFNULL(latest.serial_no, '')
            AND l.posting_date = latest.posting_date
            AND l.creation = latest.creation
            AND l.name = latest.name
            AND l.item = %s
        LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        WHERE l.item = %s
          AND IFNULL(sl.staging_area, 0) = 0
          AND l.end_qty > 0
        ORDER BY l.storage_location, l.handling_unit
    """
    
    results = frappe.db.sql(sql, (item_code, item_code, item_code, item_code), as_dict=True)
    
    total_available = sum(row.get('available_qty', 0) for row in results)
    
    print(f"\n{'='*80}")
    print(f"Stock Availability for Item: {item_code}")
    if results:
        print(f"Item Name: {results[0].get('item_name', 'N/A')}")
    print(f"{'='*80}")
    print(f"\nTotal Available Quantity: {total_available}")
    
    if results:
        print(f"\nBreakdown by Location/Handling Unit:")
        print(f"{'-'*80}")
        print(f"{'Location':<35} {'Handling Unit':<20} {'Batch':<15} {'Serial':<15} {'Qty':<10} {'Last Transaction':<20}")
        print(f"{'-'*80}")
        
        for row in results:
            location = row.get('storage_location', '') or ''
            hu = row.get('handling_unit', '') or ''
            batch = row.get('batch_no', '') or ''
            serial = row.get('serial_no', '') or ''
            qty = row.get('available_qty', 0)
            last_date = str(row.get('last_transaction_date', ''))[:19] if row.get('last_transaction_date') else ''
            
            print(f"{location:<35} {hu:<20} {batch:<15} {serial:<15} {qty:<10.3f} {last_date:<20}")
    else:
        print("\nNo stock available for this item.")
    
    print(f"{'-'*80}")
    print(f"\nTotal Available: {total_available}")
    print(f"{'='*80}\n")
    
    return {
        'item_code': item_code,
        'total_available': total_available,
        'breakdown': results
    }
