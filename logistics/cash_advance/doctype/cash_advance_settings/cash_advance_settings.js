// Copyright (c) 2026, www.agilasoft.com and contributors

frappe.ui.form.on("Cash Advance Settings", {
	refresh(frm) {
		frm.set_query("ar_employee_account", () => ({
			filters: { company: frm.doc.company },
		}));
	},
});
