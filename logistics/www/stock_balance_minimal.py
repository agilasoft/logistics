# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def get_context(context):
    """Get context for minimal stock balance web page"""
    
    # Minimal context with only essential variables
    context.update({
        "customer_name": "Test Customer",
        "total_items": 0,
        "title": "Stock Balance",
        "page_title": "Stock Balance"
    })
    
    return context
