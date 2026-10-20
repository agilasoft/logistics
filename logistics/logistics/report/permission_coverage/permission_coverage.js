// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.query_reports["Permission Coverage"] = {
	filters: [
		{
			fieldname: "role",
			label: __("Role"),
			fieldtype: "Link",
			options: "Role",
		},
		{
			fieldname: "coverage",
			label: __("Coverage"),
			fieldtype: "Select",
			options: ["", "In a group", "Not in a group", "Has manual permissions"].join("\n"),
		},
		{
			fieldname: "enabled_only",
			label: __("Enabled only"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
