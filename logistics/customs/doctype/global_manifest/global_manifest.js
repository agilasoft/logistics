// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Global Manifest", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("File"), () => {
			frappe.call({
				method: "logistics.customs.doctype.global_manifest.global_manifest.file_manifest",
				args: { global_manifest_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Filing manifest..."),
				callback(r) {
					const message = r.message || {};
					if (message.message) {
						frappe.msgprint({
							title: message.success ? __("Filed") : __("Filing"),
							message: message.message,
							indicator: message.success ? "green" : "orange",
						});
					}
					frm.reload_doc();
					if (message.filing && message.filing.doctype && message.filing.name) {
						frappe.set_route("Form", message.filing.doctype, message.filing.name);
					}
				},
			});
		}, __("Actions"));
	},
});
