// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Special Project", {
	refresh: function (frm) {
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
	},
});
