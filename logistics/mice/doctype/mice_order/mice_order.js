// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_exhibit_order(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
}

function _logistics_mice_order_add_create_or_open_job(frm) {
	// Mirror Transport Order → Transport Job / Project Order → Project Job.
	if (frm.doc.__islocal || frm.is_new() || !frm.doc.name || String(frm.doc.name).startsWith("new-")) {
		return;
	}

	frappe.db.get_value("MICE Job", { exhibit_order: frm.doc.name }, "name", function (r) {
		if (r && r.name) {
			frm.add_custom_button(__("MICE Job"), function () {
				frappe.set_route("Form", "MICE Job", r.name);
			}, __("Action"));
			frm.dashboard.add_indicator(__("MICE Job: {0}", [r.name]), "blue");
			return;
		}

		frm.add_custom_button(__("Job"), function () {
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
						method: "logistics.mice.doctype.mice_order.mice_order.action_create_mice_job",
						args: {
							docname: frm.doc.name,
							title: values.title,
						},
						freeze: true,
						freeze_message: __("Creating MICE Job..."),
						callback: function (response) {
							if (!response || !response.message) {
								return;
							}
							const payload = response.message;
							if (payload.already_exists) {
								frappe.msgprint({
									title: __("MICE Job Already Exists"),
									message: __("MICE Job {0} already exists for this MICE Order.", [payload.name]),
									indicator: "blue",
								});
								frappe.set_route("Form", "MICE Job", payload.name);
								frm.reload_doc();
							} else if (payload.created) {
								frappe.msgprint({
									title: __("MICE Job Created"),
									message: __("MICE Job {0} created successfully.", [payload.name]),
									indicator: "green",
								});
								frappe.set_route("Form", "MICE Job", payload.name);
								frm.reload_doc();
							}
						},
					});
				},
				__("Create MICE Job"),
				__("Create")
			);
		}, __("Create"));
	});
}

frappe.ui.form.on("MICE Order", {
	refresh(frm) {
		logistics_set_site_query_exhibit_order(frm);
		_logistics_mice_order_add_create_or_open_job(frm);
	},
});
