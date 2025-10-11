# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta


def get_context(context):
    """Get context for stock balance test web page"""
    
    # Simple test context
    context.update({
        "customer_name": "Test Customer",
        "total_items": 0,
        "stock_balance": [],
        "available_items": [],
        "available_branches": [],
        "title": "Stock Balance Test",
        "page_title": "Stock Balance Test"
    })
    
    return context
