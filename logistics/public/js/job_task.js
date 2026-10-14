// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Populate Job Tasks on bookings and the execution jobs they become.
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
				if (payload && payload.message) {
					frappe.show_alert({ message: __(payload.message), indicator: "blue" }, 4);
				}
				if (frm.dashboard && typeof frm.dashboard.refresh === "function") {
					frm.dashboard.refresh();
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
				if (!window.logistics || !logistics.menu || typeof logistics.menu.add !== "function") {
					return;
				}
				logistics.menu.add(frm, {
					label: __("Populate Job Tasks"),
					group: __("Action"),
					ptype: "write",
					also: [{ doctype: "Job Task", ptype: "create" }],
					action: function () {
						populate(frm);
					},
				});
			},
		});
	});
})();
