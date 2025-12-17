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
					"action": "logistics.sea_freight.create_sea_booking_from_sales_quote()",
					"label": _("Sea Booking from Sales Quote"),
				},
			]
		},
	]

