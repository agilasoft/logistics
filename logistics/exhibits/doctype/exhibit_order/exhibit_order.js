// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_exhibit_order(frm) {
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

frappe.ui.form.on("Exhibit Order", {
	refresh(frm) {
		logistics_set_site_query_exhibit_order(frm);
		if (frm.doc.__islocal) {
			return;
		}
		frm.add_custom_button(__("Create Job"), () => {
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
				(values) => {
					frappe.call({
						method: "logistics.exhibits.doctype.exhibit_order.exhibit_order.create_task_job",
						args: {
							docname: frm.doc.name,
							title: values.title,
						},
						freeze: true,
						callback: (r) => {
							if (r.message && r.message.name) {
								frappe.set_route("Form", "Exhibit Job", r.message.name);
							}
						},
					});
				},
				__("Create Exhibit Job"),
				__("Create")
			);
		}, __("Actions"));
	},
});

