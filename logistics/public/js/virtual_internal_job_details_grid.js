// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

(function () {
	"use strict";

	var VIRTUAL_IJ_PARENTS = [
		"Sea Booking",
		"Sea Shipment",
		"Air Booking",
		"Air Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration",
		"Declaration Order",
		"Warehouse Job",
		"Inbound Order",
		"Release Order",
		"Cross-Docking Order",
		"General Job",
		"Project Job",
		"MICE Job",
		"Exhibit Job",
	];

	function enableVirtualInternalJobDetailsGrid(frm) {
		if (!frm || !frm.doc || frm.doc.docstatus !== 0) return;
		if (!frm.fields_dict.internal_job_details) return;
		var grid = frm.fields_dict.internal_job_details.grid;
		if (!grid || !grid.wrapper) return;
		grid.display_status = "Write";
		grid.wrapper.find(".grid-footer").removeClass("hidden");
		grid.wrapper
			.find(".grid-add-row, .grid-add-multiple-rows")
			.removeClass("hidden d-none");
		if (typeof grid.setup_toolbar === "function") {
			grid.setup_toolbar();
		}
	}

	function markInternalJobDetailsFromForm(frm) {
		if (!frm || !frm.doc) return;
		if ((frm.doc.internal_job_details || []).length) {
			frm.doc.flags = frm.doc.flags || {};
			frm.doc.flags._internal_job_details_from_form = true;
		}
	}

	VIRTUAL_IJ_PARENTS.forEach(function (doctype) {
		frappe.ui.form.on(doctype, {
			refresh: function (frm) {
				enableVirtualInternalJobDetailsGrid(frm);
			},
			before_save: function (frm) {
				markInternalJobDetailsFromForm(frm);
			},
		});
	});
})();
