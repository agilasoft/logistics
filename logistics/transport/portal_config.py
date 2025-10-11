# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_portal_menu_items():
    """Get portal menu items for transport jobs"""
    return [
        {
            "title": "Transport Jobs",
            "route": "/transport-portal",
            "reference_doctype": "Transport Job",
            "role": "Customer",
            "icon": "fa fa-truck"
        }
    ]


def get_portal_page_context(context):
    """Add transport portal context to portal pages"""
    if context.get('route') == '/transport-portal':
        # Add transport-specific context
        context.update({
            "show_sidebar": True,
            "show_breadcrumbs": True,
            "title": "Transport Jobs Portal"
        })
    
    return context


def get_portal_settings():
    """Get portal settings for transport jobs"""
    return {
        "enable_customer_portal": True,
        "portal_title": "Transport Jobs Portal",
        "show_vehicle_tracking": True,
        "show_route_map": True,
        "map_renderer": "OpenStreetMap"
    }

