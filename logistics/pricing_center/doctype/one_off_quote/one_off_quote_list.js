// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.listview_settings["One-Off Quote"] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		const status_colors = {
			"Draft": "gray",
			"Converted": "green"
		};
		const status = doc.status || "Draft";
		const color = status_colors[status] || "blue";

		return [__(status), color, `status,=,${status}`];
	}
};
