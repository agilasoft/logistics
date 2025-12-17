from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Create"),
			"icon": "icon-plus",
			"items": [
				{
					"type": "action",
					"action": "logistics.air_freight.create_air_booking_from_sales_quote()",
					"label": _("Air Booking from Sales Quote"),
				},
			]
		},
	]

