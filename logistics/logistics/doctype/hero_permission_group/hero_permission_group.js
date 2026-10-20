// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hero Permission Group", {
	setup(frm) {
		frm.set_query("user", "members", () => ({
			filters: {
				name: ["not in", ["Administrator", "Guest"]],
				enabled: 1,
			},
		}));
		frm.set_query("reference_doctype", "rules", () => ({
			query: "logistics.permission_studio.api.permitted_doctype_query",
		}));
		frm.set_query("applicable_for", "rules", (doc, cdt, cdn) => ({
			query: "frappe.core.doctype.user_permission.user_permission.get_applicable_for_doctype_list",
			doctype: locals[cdt][cdn].reference_doctype,
		}));
	},
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Open Permission Studio"), () => {
			frappe.set_route("permission-studio", frm.doc.name);
		});
	},
});

frappe.ui.form.on("Hero Permission Rule", {
	reference_doctype(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.for_value) {
			frappe.model.set_value(cdt, cdn, "for_value", "");
		}
		const nested = ((frappe.boot && frappe.boot.nested_set_doctypes) || []).includes(row.reference_doctype);
		if (!nested && row.hide_descendants) {
			frappe.model.set_value(cdt, cdn, "hide_descendants", 0);
		}
	},
	apply_to_all_doctypes(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.apply_to_all_doctypes && row.applicable_for) {
			frappe.model.set_value(cdt, cdn, "applicable_for", "");
		}
	},
});
