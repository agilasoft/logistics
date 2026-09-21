// Copyright (c) 2026, www.agilasoft.com and contributors
// Desk: Sales Invoice may still carry a legacy `job_costing_number` Link to removed DocType
// "Job Costing Number" (cached meta / stale Custom Field). Patch meta before controls bind;
// hide duplicate when `job_number` exists.

(function () {
	"use strict";

	function patch_docfields(doctype) {
		(frappe.meta.get_docfields(doctype) || []).forEach(function (df) {
			if (
				df &&
				df.fieldname === "job_costing_number" &&
				df.fieldtype === "Link" &&
				df.options === "Job Costing Number"
			) {
				df.options = "Job Number";
			}
		});
	}

	function copy_job_number_from_return_against(frm) {
		if (frm.doc.docstatus !== 0 || !frm.doc.is_return || !frm.doc.return_against || frm.doc.job_number) {
			return;
		}
		frappe.db.get_value(frm.doctype, frm.doc.return_against, "job_number", function (r) {
			if (r && r.job_number && !frm.doc.job_number) {
				frm.set_value("job_number", r.job_number);
			}
		});
	}

	function bind(doctype) {
		frappe.ui.form.on(doctype, {
			setup: function (frm) {
				patch_docfields(frm.doctype);
				if (doctype === "Sales Invoice" || doctype === "Purchase Invoice") {
					patch_docfields(doctype + " Item");
				}
			},
			refresh: function (frm) {
				if (frm.fields_dict.job_number && frm.fields_dict.job_costing_number) {
					frm.set_df_property("job_costing_number", "hidden", 1);
					frm.set_df_property("job_costing_number", "reqd", 0);
				}
				copy_job_number_from_return_against(frm);
			},
			is_return: copy_job_number_from_return_against,
			return_against: copy_job_number_from_return_against,
		});
	}

	bind("Sales Invoice");
	bind("Purchase Invoice");
})();
