// Copyright (c) 2025, Logistics Team and contributors
// For license information, please see license.txt

frappe.query_reports["Container Status Report"] = {
	"filters": [
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nIn Transit\nAt Port (Origin)\nGate-In\nLoaded\nAt Sea\nDischarged\nAt Port (Destination)\nCustoms Hold\nAvailable for Pick-Up\nOut for Delivery\nDelivered\nEmpty Returned\nAt Depot\nDamaged\nLost\nClosed"
		},
		{
			"fieldname": "container_type",
			"label": __("Container Type"),
			"fieldtype": "Link",
			"options": "Container Type"
		},
		{
			"fieldname": "return_status",
			"label": __("Return Status"),
			"fieldtype": "Select",
			"options": "\nNot Returned\nReturned\nOverdue"
		}
	]
};
