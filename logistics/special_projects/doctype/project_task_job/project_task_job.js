// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_project_task_job(frm) {
	frm.set_query("site", function () {
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

frappe.ui.form.on("Project Task Job", {
	refresh(frm) {
		logistics_set_site_query_project_task_job(frm);
	},
});
