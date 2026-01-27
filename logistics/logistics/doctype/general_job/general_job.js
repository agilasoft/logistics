// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("General Job", {
	refresh(frm) {
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
