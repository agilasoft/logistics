// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Logistics Settings", {
	refresh(frm) {
		toggle_credit_control_rules_readonly(frm);
	},
	credit_apply_hold_to_all_doctypes(frm) {
		toggle_credit_control_rules_readonly(frm);
	},
});

function toggle_credit_control_rules_readonly(frm) {
	const all = cint(frm.doc.credit_apply_hold_to_all_doctypes);
	if (!frm.fields_dict.credit_control_rules) {
		return;
	}
	frm.set_df_property("credit_control_rules", "read_only", all);
	frm.set_df_property("credit_control_rules", "cannot_add_rows", all);
	frm.refresh_field("credit_control_rules");
}
