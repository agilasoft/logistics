// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Management Settings", {
	refresh(frm) {
		frm.set_intro(
			__(
				"Allow Legacy Jobs shows the Legacy Job checkbox on Air Shipment, Sea Shipment, Transport Job, Declaration, and Warehouse Job. Leave it unchecked to hide that checkbox."
			)
		);
	},
	after_save(frm) {
		if (window.logistics && logistics.legacy_job && logistics.legacy_job.set_allowed) {
			logistics.legacy_job.set_allowed(frm.doc.allow_legacy_jobs);
		} else if (frappe.boot) {
			frappe.boot.logistics_job_management_settings = {
				allow_legacy_jobs: cint(frm.doc.allow_legacy_jobs),
			};
		}
	},
});
