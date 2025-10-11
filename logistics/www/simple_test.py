# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Simple test context"""
    context.update({
        "title": "Simple Test",
        "message": "This is a simple test page!"
    })
    return context
