// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_project_order(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
}

function _logistics_project_order_add_create_or_open_job(frm) {
	// Mirror Transport Order → Transport Job pattern: link to existing Project Job under "Action",
	// otherwise expose the create button under the standard "Create" group.
	if (
		!(window.logistics && logistics.menu && logistics.menu.is_submitted
			? logistics.menu.is_submitted(frm)
			: frm.doc.docstatus === 1) ||
		frm.doc.__islocal ||
		frm.is_new() ||
		!frm.doc.name ||
		String(frm.doc.name).startsWith("new-")
	) {
		return;
	}

	frappe.db.get_value(
		"Project Job",
		{ special_project_order: frm.doc.name },
		"name",
		function (r) {
			if (r && r.name) {
				frm.add_custom_button(__("Project Job"), function () {
					frappe.set_route("Form", "Project Job", r.name);
				}, __("Action"));
				frm.dashboard.add_indicator(__("Project Job: {0}", [r.name]), "blue");
				return;
			}

			frm.add_custom_button(__("Project Job"), function () {
				const fields = [
					{
						fieldname: "title",
						fieldtype: "Data",
						label: __("Job title"),
						reqd: 1,
						default: frm.doc.name + " — " + __("Task"),
					},
				];
				frappe.prompt(
					fields,
					function (values) {
						frappe.call({
							method: "logistics.special_projects.doctype.project_order.project_order.action_create_project_job",
							args: {
								docname: frm.doc.name,
								title: values.title,
							},
							freeze: true,
							freeze_message: __("Creating Project Job..."),
							callback: function (response) {
								if (!response || !response.message) {
									return;
								}
								const payload = response.message;
								if (payload.already_exists) {
									frappe.msgprint({
										title: __("Project Job Already Exists"),
										message: __("Project Job {0} already exists for this Project Order.", [payload.name]),
										indicator: "blue",
									});
									frappe.set_route("Form", "Project Job", payload.name);
									frm.reload_doc();
								} else if (payload.created) {
									frappe.msgprint({
										title: __("Project Job Created"),
										message: __("Project Job {0} created successfully.", [payload.name]),
										indicator: "green",
									});
									frappe.set_route("Form", "Project Job", payload.name);
									frm.reload_doc();
								}
							},
						});
					},
					__("Create Project Job"),
					__("Create")
				);
			}, __("Create"));
		}
	);
}

function _logistics_project_order_populate_from_template(frm, method, freeze_message) {
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

frappe.ui.form.on("Project Order", {
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
		_logistics_project_order_populate_from_template(
			frm,
			"logistics.document_management.api.populate_documents_from_template",
			__("Applying document template...")
		);
	},
	milestone_template(frm) {
		_logistics_project_order_populate_from_template(
			frm,
			"logistics.document_management.api.populate_milestones_from_template",
			__("Applying milestone template...")
		);
	},
	refresh(frm) {
		logistics_set_site_query_project_order(frm);
		_logistics_project_order_add_create_or_open_job(frm);

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
