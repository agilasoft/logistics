// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Special Project", {
	refresh: function (frm) {
		// Load dashboard HTML in Dashboard tab (only when doc is saved)
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frappe.call({
					method: "logistics.special_projects.doctype.special_project.special_project.get_dashboard_html",
					args: { special_project: frm.doc.name },
					callback: function (r) {
						if (r.message && frm.fields_dict.dashboard_html) {
							frm.fields_dict.dashboard_html.$wrapper.html(r.message);
						}
					}
				});
				setTimeout(function () { frm._dashboard_html_called = false; }, 2000);
			}
		}
		if (frm.doc.project && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Open Project"), function () {
				frappe.set_route("Form", "Project", frm.doc.project);
			});
		}
		if (frm.doc.status && ["Booked", "Approved", "Planning", "In Progress", "Completed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Charge Scoping Costs"), function () {
				frappe.call({
					method: "logistics.special_projects.doctype.special_project.special_project.charge_scoping_costs",
					args: { special_project: frm.doc.name },
					callback: function () {
						frm.reload_doc();
					},
				});
			});
		}
		_refresh_cost_revenue_summary(frm);
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__("Populate from Template"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Special Project", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frappe.show_alert({
								message: __("Added {0} document(s) from template.", [r.message.added]),
								indicator: "green",
							});
							frm.reload_doc();
						} else if (r.message && r.message.message) {
							frappe.msgprint(r.message.message);
						}
					},
				});
			});
		}
	},
});

function _refresh_cost_revenue_summary(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.cost_revenue_html) return;
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_cost_revenue_summary",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.cost_revenue_html) {
				frm.fields_dict.cost_revenue_html.$wrapper.html(r.message);
			}
		},
	});
}

frappe.ui.form.on("Special Project Job", {
	jobs_add: function (frm) {
		_refresh_cost_revenue_summary(frm);
	},
	jobs_remove: function (frm) {
		_refresh_cost_revenue_summary(frm);
	},
});
