// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Get Job Tasks, same Action menu entry as Get Milestones.
// Keep this list aligned with JOB_TASK_PARENTS in logistics/job_management/job_task.py.
(function () {
	"use strict";

	var JOB_TASK_PARENTS = [
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Release Order",
		"Transfer Order",
		"Cross-Docking Order",
		"VAS Order",
		"Stocktake Order",
		"Project Order",
		"MICE Order",
		"Air Shipment",
		"Air Consolidation",
		"Sea Shipment",
		"Sea Consolidation",
		"Transport Job",
		"Transport Consolidation",
		"Warehouse Job",
		"Declaration",
		"General Job",
		"Project Job",
		"MICE Job",
		"Exhibit Job",
		"Time Sensitive Case",
	];

	function populate(frm) {
		frappe.call({
			method: "logistics.job_management.job_task.populate_job_tasks",
			args: { doctype: frm.doctype, docname: frm.doc.name },
			freeze: true,
			callback: function (r) {
				var payload = r && r.message;
				if (payload && payload.added !== undefined) {
					frm.reload_doc();
					if (payload.message) {
						frappe.show_alert({ message: __(payload.message), indicator: "blue" }, 4);
					}
				}
			},
		});
	}

	if (typeof frappe === "undefined" || !frappe.ui || !frappe.ui.form || !frappe.ui.form.on) {
		return;
	}

	JOB_TASK_PARENTS.forEach(function (doctype) {
		frappe.ui.form.on(doctype, {
			refresh: function (frm) {
				if (!frm || frm.is_new() || !frm.doc || !frm.doc.name) {
					return;
				}
				if (!frm.fields_dict || !frm.fields_dict.job_tasks) {
					return;
				}
				if (!window.logistics || !logistics.menu || typeof logistics.menu.add !== "function") {
					return;
				}
				logistics.menu.add(frm, {
					label: __("Get Job Tasks"),
					group: __("Action"),
					ptype: "write",
					action: function () {
						populate(frm);
					},
				});
			},
		});
	});
})();
