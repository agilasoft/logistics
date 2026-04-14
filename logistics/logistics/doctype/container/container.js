// Copyright (c) 2025, Logistics Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Container", {
	is_active(frm) {
		if (frm.doc.is_active) {
			frm.set_value("assignment_inactive_reason", null);
		}
	},
	refresh: function (frm) {
		// Skip for new/unsaved docs - name is temporary and doc doesn't exist in DB
		if (frm.doc.__islocal || !frm.doc.name) return;
		frappe.call({
			method: "logistics.logistics.doctype.container.container.get_linked_shipments_html",
			args: { container: frm.doc.name },
			callback: function (r) {
				if (r.message && frm.fields_dict.linked_shipments) {
					frm.fields_dict.linked_shipments.$wrapper.html(r.message);
				}
			}
		});
		frappe.call({
			method: "logistics.logistics.doctype.container.container.get_linked_transport_jobs_html",
			args: { container: frm.doc.name },
			callback: function (r) {
				if (r.message && frm.fields_dict.linked_transport_jobs) {
					frm.fields_dict.linked_transport_jobs.$wrapper.html(r.message);
				}
			}
		});
	}
});
