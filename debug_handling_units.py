#!/usr/bin/env python3

import frappe

def debug_handling_units():
    """Debug handling unit counting for WJ-00000220"""
    
    # Get the warehouse job
    job = frappe.get_doc("Warehouse Job", "WJ-00000220")
    
    print(f"Job: {job.name}")
    print(f"Customer: {job.customer}")
    print(f"Job Type: {job.type}")
    print(f"Items count: {len(job.items)}")
    
    # Count unique handling units
    handling_units = set()
    for item in job.items:
        hu = getattr(item, 'handling_unit', None)
        if hu:
            handling_units.add(hu)
        print(f"Item: {item.item}, Handling Unit: {hu}, Quantity: {item.quantity}")
    
    print(f"\nUnique handling units: {len(handling_units)}")
    print(f"Handling units: {sorted(handling_units)}")
    
    # Check contract items
    contracts = frappe.get_all("Warehouse Contract", 
                              filters={"customer": job.customer, "docstatus": 1},
                              fields=["name"])
    
    for contract in contracts:
        contract_items = frappe.get_all("Warehouse Contract Item",
                                      filters={"parent": contract.name, "unit_type": "Handling Unit"},
                                      fields=["item_charge", "rate", "uom", "unit_type"])
        if contract_items:
            print(f"\nContract {contract.name} has {len(contract_items)} handling unit items:")
            for ci in contract_items:
                print(f"  - {ci.item_charge}: {ci.rate} {ci.uom} ({ci.unit_type})")

if __name__ == "__main__":
    frappe.init(site="logistics.agilasoft.com")
    frappe.connect()
    debug_handling_units()
