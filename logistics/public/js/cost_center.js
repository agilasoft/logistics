// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Company stays on the record for ERPNext, and is not shown on the form.
frappe.ui.form.on("Cost Center", {
	onload(frm) {
		logistics_cost_center_hide_company(frm);
		logistics_cost_center_ensure_company(frm);
	},
	refresh(frm) {
		logistics_cost_center_hide_company(frm);
		logistics_cost_center_ensure_company(frm);
	},
});

function logistics_cost_center_hide_company(frm) {
	if (!frm.get_field("company")) {
		return;
	}
	frm.set_df_property("company", "hidden", 1);
	frm.set_df_property("company", "reqd", 0);
	frm.toggle_display("company", false);
}

function logistics_cost_center_ensure_company(frm) {
	if (frm.doc.company) {
		return;
	}
	const company =
		frappe.defaults.get_user_default("Company") || frappe.defaults.get_default("company");
	if (!company) {
		return;
	}
	// set_value keeps the parent-cost-center query, which filters on company.
	frm.set_value("company", company);
}
