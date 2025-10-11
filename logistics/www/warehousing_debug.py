# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Debug warehousing portal to check data availability"""
    
    # Check if Warehouse Item doctype exists
    try:
        warehouse_items = frappe.get_all("Warehouse Item", limit=5)
        warehouse_items_count = frappe.db.count("Warehouse Item")
    except Exception as e:
        warehouse_items = []
        warehouse_items_count = 0
        warehouse_items_error = str(e)
    
    # Check if Warehouse Stock Ledger exists
    try:
        stock_ledger_entries = frappe.get_all("Warehouse Stock Ledger", limit=5)
        stock_ledger_count = frappe.db.count("Warehouse Stock Ledger")
    except Exception as e:
        stock_ledger_entries = []
        stock_ledger_count = 0
        stock_ledger_error = str(e)
    
    # Check if Customer doctype exists
    try:
        customers = frappe.get_all("Customer", limit=5)
        customers_count = frappe.db.count("Customer")
    except Exception as e:
        customers = []
        customers_count = 0
        customers_error = str(e)
    
    context.update({
        "title": "Warehousing Debug",
        "warehouse_items": warehouse_items,
        "warehouse_items_count": warehouse_items_count,
        "stock_ledger_entries": stock_ledger_entries,
        "stock_ledger_count": stock_ledger_count,
        "customers": customers,
        "customers_count": customers_count,
        "warehouse_items_error": locals().get('warehouse_items_error', ''),
        "stock_ledger_error": locals().get('stock_ledger_error', ''),
        "customers_error": locals().get('customers_error', '')
    })
    
    return context
