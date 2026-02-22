// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("General Job", {
	refresh(frm) {
		// Populate Documents from Template
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__("Populate from Template"), function() {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "General Job", docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					}
				});
			}, __("Documents"));
		}

		if (!frm.is_new() && !frm.doc.job_costing_number) {
			frm.add_custom_button(__("Create Job Costing Number"), function() {
				frappe.call({
					method: "logistics.logistics.doctype.general_job.general_job.create_job_costing_number",
					args: {
						docname: frm.doc.name
					},
					callback: function(r) {
						if (r.message) {
							frm.reload_doc();
							frappe.msgprint(__("Job Costing Number {0} created successfully", [r.message]));
						}
					}
				});
			}, __("Actions"));
		}
	},
});
