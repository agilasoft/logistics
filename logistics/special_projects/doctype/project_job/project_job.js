// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_project_job(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
}

function _logistics_project_job_populate_from_template(frm, method, freeze_message) {
	if (!frm.doc.name || frm.doc.__islocal) return;
	frm.save().then(function () {
		frappe.call({
			method: method,
			args: { doctype: frm.doctype, docname: frm.doc.name },
			freeze: !!freeze_message,
			freeze_message: freeze_message,
			callback: function (r) {
				if (r.message) {
					frm.reload_doc();
					if (r.message.added) {
						frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					} else if (r.message.message) {
						frappe.show_alert({ message: __(r.message.message), indicator: "orange" }, 5);
					}
				}
			},
		});
	});
}

frappe.ui.form.on("Project Job", {
	setup(frm) {
		frm.set_query("milestone_template", function () {
			return frappe
				.call("logistics.document_management.api.get_milestone_template_filters", {
					doctype: frm.doctype,
				})
				.then(function (r) {
					return r.message || { filters: [] };
				});
		});
	},
	document_list_template(frm) {
		_logistics_project_job_populate_from_template(
			frm,
			"logistics.document_management.api.populate_documents_from_template",
			__("Applying document template...")
		);
	},
	milestone_template(frm) {
		_logistics_project_job_populate_from_template(
			frm,
			"logistics.document_management.api.populate_milestones_from_template",
			__("Applying milestone template...")
		);
	},
	refresh(frm) {
		logistics_set_site_query_project_job(frm);

		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(
				__("Get Documents"),
				function () {
					frappe.call({
						method: "logistics.document_management.api.populate_documents_from_template",
						args: { doctype: frm.doctype, docname: frm.doc.name },
						callback: function (r) {
							if (r.message && r.message.added !== undefined) {
								frm.reload_doc();
								frappe.show_alert(
									{ message: __(r.message.message), indicator: "blue" },
									3
								);
							} else if (r.message && r.message.message) {
								frappe.msgprint(r.message.message);
							}
						},
					});
				},
				__("Action")
			);
		}

		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.milestones) {
			frm.add_custom_button(
				__("Get Milestones"),
				function () {
					frappe.call({
						method: "logistics.document_management.api.populate_milestones_from_template",
						args: { doctype: frm.doctype, docname: frm.doc.name },
						callback: function (r) {
							if (r.message && r.message.added !== undefined) {
								frm.reload_doc();
								frappe.show_alert(
									{ message: __(r.message.message), indicator: "blue" },
									3
								);
							} else if (r.message && r.message.message) {
								frappe.msgprint(r.message.message);
							}
						},
					});
				},
				__("Action")
			);
		}
	},
});
