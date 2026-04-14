// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

(function () {
	"use strict";

	var JOB_TYPE_BY_SERVICE = {
		Air: "Air Booking",
		Sea: "Sea Booking",
		Transport: "Transport Order",
		Customs: "Declaration Order",
		Warehousing: "Inbound Order",
	};

	function sync_job_type_from_service(cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (!row) {
			return;
		}
		var st = String(row.service_type || "").trim();
		var jt = JOB_TYPE_BY_SERVICE[st];
		if (jt) {
			frappe.model.set_value(cdt, cdn, "job_type", jt);
		}
	}

	frappe.ui.form.on("Internal Job Detail", {
		service_type: function (frm, cdt, cdn) {
			sync_job_type_from_service(cdt, cdn);
		},
	});
})();
