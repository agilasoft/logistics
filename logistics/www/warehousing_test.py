# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Test warehousing portal context"""
    context.update({
        "title": "Warehousing Portal Test",
        "message": "Warehousing portal is working!"
    })
    
    return context
