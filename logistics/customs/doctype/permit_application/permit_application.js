// Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Permit Application", {
	refresh(frm) {
		// Frappe submit happens only on Workflow "Approve" (to Approved)
		frm.set_df_property("status", "read_only", !frm.is_new());
		if (cint(frm.doc.docstatus) === 0) {
			frm.set_intro(
				__("Use Workflow: File, review, then Approve. Frappe’s Submit in the system runs on Approve, not when filing with the authority.")
			);
		} else {
			frm.set_intro();
		}
	},
});
