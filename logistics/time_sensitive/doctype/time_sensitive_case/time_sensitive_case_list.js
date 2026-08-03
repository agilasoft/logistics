// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.listview_settings["Time Sensitive Case"] = {
	add_fields: [
		"status",
		"sla_status",
		"critical_deadline",
		"case_type",
		"case_type_name",
		"severity",
	],
	get_indicator(doc) {
		return logistics.time_sensitive.timer.getListIndicator(doc);
	},
	formatters: {
		case_title(value, df, doc) {
			return logistics.time_sensitive.timer.titleWithTimerIcon(value, doc);
		},
	},
};
