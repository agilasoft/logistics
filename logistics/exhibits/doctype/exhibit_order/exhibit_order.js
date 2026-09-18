// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_exhibit_order(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
}

function _exhibit_order_can_create_job(frm) {
	if (window.logistics && logistics.menu && logistics.menu.is_submitted) {
		return logistics.menu.is_submitted(frm);
	}
	return !!(
		frm.doc &&
		frm.doc.name &&
		!frm.doc.__islocal &&
		(frm.doc.docstatus === 1 || frm.doc.docstatus === "1")
	);
}

function _exhibit_order_open_create_job_prompt(frm) {
	frappe.prompt(
		[
			{
				fieldname: "title",
				fieldtype: "Data",
				label: __("Job title"),
				reqd: 1,
				default: frm.doc.name + " — " + __("Task"),
			},
		],
		function (values) {
			frappe.call({
				method: "logistics.exhibits.doctype.exhibit_order.exhibit_order.create_task_job",
				args: {
					docname: frm.doc.name,
					title: values.title,
				},
				freeze: true,
				freeze_message: __("Creating Exhibit Job..."),
				callback: function (r) {
					if (r.message && r.message.name) {
						frappe.set_route("Form", "Exhibit Job", r.message.name);
					}
				},
			});
		},
		__("Create Exhibit Job"),
		__("Create")
	);
}

function _exhibit_order_add_create_job_button(frm) {
	if (!_exhibit_order_can_create_job(frm)) {
		return;
	}
	if (window.logistics && logistics.menu && typeof logistics.menu.add === "function") {
		logistics.menu.add(frm, {
			label: __("Create Job"),
			group: __("Create"),
			doctype: "Exhibit Job",
			ptype: "create",
			action: function () {
				_exhibit_order_open_create_job_prompt(frm);
			},
		});
		return;
	}
	frm.add_custom_button(__("Create Job"), function () {
		_exhibit_order_open_create_job_prompt(frm);
	}, __("Create"));
}

frappe.ui.form.on("Exhibit Order", {
	refresh(frm) {
		logistics_set_site_query_exhibit_order(frm);
		if (window.logistics && logistics.menu && logistics.menu.when_submitted) {
			logistics.menu.when_submitted(frm, _exhibit_order_add_create_job_button);
		} else {
			_exhibit_order_add_create_job_button(frm);
		}
	},
});

