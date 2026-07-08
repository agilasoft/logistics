// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Outlook Calendar Settings", {
	refresh(frm) {
		if (!frappe.user.has_role("System Manager")) {
			return;
		}
		frm.add_custom_button(__("Open Connected App"), () => {
			const app = frm.doc.connected_app || "Microsoft Outlook";
			frappe.set_route("Form", "Connected App", app);
		});
	},
});
