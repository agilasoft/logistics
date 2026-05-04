// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function logistics_set_internal_job_site_query(frm) {
	frm.set_query("sp_site", "internal_job_details", function () {
		const cust = frm.doc.customer;
		if (!cust) {
			return { filters: [["name", "=", ""]] };
		}
		return {
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: {
				link_doctype: "Customer",
				link_name: cust,
			},
		};
	});
}

frappe.ui.form.on("Special Project", {
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
	refresh: function (frm) {
		logistics_set_internal_job_site_query(frm);
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
							if (window.logistics_group_and_collapse_dash_alerts) {
								setTimeout(function() {
									window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
								}, 100);
							}
							if (window.logistics_bind_document_alert_cards) {
								window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
							}
						}
					}
				});
				setTimeout(function () { frm._dashboard_html_called = false; }, 2000);
			}
		}
		// Load milestone HTML in Milestones tab (only when doc is saved)
		if (frm.fields_dict.milestone_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._milestone_html_called) {
				frm._milestone_html_called = true;
				frappe.call({
					method: "logistics.special_projects.doctype.special_project.special_project.get_milestone_html",
					args: { special_project: frm.doc.name },
					callback: function (r) {
						if (r.message && frm.fields_dict.milestone_html) {
							frm.fields_dict.milestone_html.$wrapper.html(r.message);
						}
					}
				});
				setTimeout(function () { frm._milestone_html_called = false; }, 2000);
			}
		}
		if (frm.doc.project && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Open Project"), function () {
				frappe.set_route("Form", "Project", frm.doc.project);
			}, __("Action"));
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
			}, __("Action"));
		}
		_refresh_cost_revenue_summary(frm);
		// Load documents summary HTML in Documents tab
		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, "Special Project");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				if (window.logistics_load_documents_html) {
					window.logistics_load_documents_html(frm, "Special Project");
				}
			});
		}
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__("Get Documents"), function () {
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
			}, __("Action"));
		}
	},
	internal_job_details_add: function (frm) {
		_refresh_cost_revenue_summary(frm);
		_refresh_dashboard_html(frm);
		_refresh_milestone_html(frm);
	},
	internal_job_details_remove: function (frm) {
		_refresh_cost_revenue_summary(frm);
		_refresh_dashboard_html(frm);
		_refresh_milestone_html(frm);
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

function _refresh_dashboard_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.dashboard_html) return;
	frm._dashboard_html_called = false;
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_dashboard_html",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.dashboard_html) {
				frm.fields_dict.dashboard_html.$wrapper.html(r.message);
				if (window.logistics_group_and_collapse_dash_alerts) {
					setTimeout(function() {
						window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
					}, 100);
				}
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
				}
			}
		}
	});
}

function _refresh_milestone_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.milestone_html) return;
	frm._milestone_html_called = false;
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_milestone_html",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	});
}
