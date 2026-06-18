// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("MICE Organizer", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
	},
});
