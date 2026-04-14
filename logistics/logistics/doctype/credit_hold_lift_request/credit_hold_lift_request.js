// Copyright (c) 2026, Logistics Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Credit Hold Lift Request", {
	scope(frm) {
		const single = frm.doc.scope === "Single Document";
		frm.set_df_property("reference_name", "reqd", single);
		if (!single) {
			frm.set_value("reference_name", null);
		}
	},

	relieved_doctype(frm) {
		if (frm.doc.scope !== "Single Document") {
			return;
		}
		frm.set_value("reference_name", null);
	},
});
