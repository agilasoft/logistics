from __future__ import unicode_literals
from frappe import _

def get_data():

        return [
            {
                    "label": _("Bookings"),
                    "icon": "icon-file",
                    "items": [
                    {
                            "type": "doctype",
                            "name": "Transport Booking",
                            "label": _("Transport Booking"),
                    },
                    {
                            "type": "doctype",
                            "name": "Transport Job",
                            "label": _("Transport Job"),
                    },
                ]
            },
                        {
                    "label": _("Trip and Run Sheet"),
                    "icon": "icon-file",
                    "items": [
                    {
                            "type": "doctype",
                            "name": "Trip",
                            "label": _("Trip"),
                    },
                    {
                            "type": "doctype",
                            "name": "Dispatch",
                            "label": _("Dispatch"),
                    },
                    {
                            "type": "report",
                            "name": "Outsource Job",
                            "label": _("Outsource Job"),
                    }, 
                    {
                            "type": "report",
                            "name": "Run Sheet",
                            "label": _("Run Sheet"),
                    },      
                ]
            },
            {
                    "label": _("Billing"),
                    "icon": "icon-file",
                    "items": [
                    {
                            "type": "doctype",
                            "name": "Sales Invoice",
                            "label": _("Billing"),
                    },
                    {
                            "type": "doctype",
                            "name": "Proof of Delivery",
                            "label": _("Proof of Delivery"),
                    },
                ]
            },
            {
                "label": _("Master Files"),
                "icon": "icon-file",
                "items": [
                    {
                        "type": "doctype",
                        "name": "Vehicle",
                        "label": _("Vehicle"),
                    },
                    {
                        "type": "doctype",
                        "name": "Driver",
                        "label": _("Driver"),
                    },
                    {
                        "type": "doctype",
                        "name": "Dispatcher",
                        "label": _("Dispatcher"),
                    },
                    {
                        "type": "doctype",
                        "name": "Transport Company",
                        "label": _("Transport Company"),
                    },
                    {
                        "type": "doctype",
                        "name": "Service Level",
                        "label": _("Service Level"),
                    },
                ]
            },
            {
                "label": _("Settings"),
                "icon": "icon-file",
                "items": [
                    {
                        "type": "doctype",
                        "name": "Transport Settings",
                        "label": _("Transport Settings"),
                    },
                    {
                            "type": "doctype",
                            "name": "Terminal",
                            "label": _("Terminal"),
                    },
                    {
                            "type": "doctype",
                            "name": "Zone",
                            "label": _("Zone"),
                    },
                ]
            }
		]
