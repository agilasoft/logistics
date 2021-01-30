# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
            "module_name": "Transport",
            "category": "Modules",
            "label": _("Transport"),
            "color": "#FFF5A7",
            "reverse": 1,
            "icon": "fa fa-truck",
            "type": "module",
            "description": "Transport Management"
		},
		{
            "module_name": "Forwarding",
            "category": "Modules",
            "label": _("Forwarding"),
            "color": "#FFF5A7",
            "reverse": 1,
            "icon": "fa fa-share-square",
            "type": "module",
            "description": "Freight Forwarding Management"
		},
	]
