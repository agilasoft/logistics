// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.listview_settings["Hero Permission Group"] = {
	get_indicator(doc) {
		if (!cint(doc.enabled)) {
			return [__("Disabled"), "gray", "enabled,=,0"];
		}
		if (doc.sync_status === "Needs Attention") {
			return [__("Needs Attention"), "orange", "sync_status,=,Needs Attention"];
		}
		if (doc.sync_status === "In Sync") {
			return [__("In Sync"), "green", "sync_status,=,In Sync"];
		}
		return [__("Pending"), "blue", "sync_status,=,Pending"];
	},
};
