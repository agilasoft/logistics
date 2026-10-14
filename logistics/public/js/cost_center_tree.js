// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Loaded after ERPNext's Cost Center tree script. The tree filter already
// chooses the company, and the New dialog would otherwise ask for it because
// ERPNext marks Company as required.
const logistics_cost_center_tree = frappe.treeview_settings["Cost Center"];
if (logistics_cost_center_tree) {
	logistics_cost_center_tree.ignore_fields = logistics_cost_center_tree.ignore_fields || [];
	if (!logistics_cost_center_tree.ignore_fields.includes("company")) {
		logistics_cost_center_tree.ignore_fields.push("company");
	}
}
