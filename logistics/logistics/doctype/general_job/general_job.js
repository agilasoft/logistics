// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("General Job", {
	document_list_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_documents_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				}
			});
		});
	},
	refresh(frm) {
		// Load documents summary HTML in Documents tab
		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, "General Job");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				if (window.logistics_load_documents_html) {
					window.logistics_load_documents_html(frm, "General Job");
				}
			});
		}

		// Populate Documents from Template
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__("Get Documents"), function() {
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
			}, __("Actions"));
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
			}, __("Create"));
		}
	},
});
