// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.provide("logistics.legacy_job");

var LEGACY_JOB_DOCTYPES = {
	"Air Shipment": 1,
	"Sea Shipment": 1,
	"Transport Job": 1,
	"Declaration": 1,
	"Warehouse Job": 1,
};

function _cint(value) {
	if (value === true || value === 1 || value === "1") {
		return 1;
	}
	var number = parseInt(value, 10);
	return isNaN(number) ? 0 : number;
}

logistics.legacy_job.set_allowed = function (value) {
	var allowed = !!_cint(value);
	logistics.legacy_job._allowed = allowed;
	logistics.legacy_job._live = true;
	if (!frappe.boot.logistics_job_management_settings) {
		frappe.boot.logistics_job_management_settings = {};
	}
	frappe.boot.logistics_job_management_settings.allow_legacy_jobs = allowed ? 1 : 0;
	return allowed;
};

logistics.legacy_job.allowed = function () {
	if (!logistics.legacy_job._live) {
		return false;
	}
	if (typeof logistics.legacy_job._allowed === "boolean") {
		return logistics.legacy_job._allowed;
	}
	var settings = frappe.boot && frappe.boot.logistics_job_management_settings;
	return !!(settings && _cint(settings.allow_legacy_jobs));
};

logistics.legacy_job.is_legacy = function (frm) {
	if (!frm || !frm.doc) {
		return false;
	}
	return !!(frm.doc.is_legacy_job || frm.doc.is_beginning_job);
};

logistics.legacy_job.apply = function (frm) {
	if (!frm || !LEGACY_JOB_DOCTYPES[frm.doctype]) {
		return;
	}
	var allowed = logistics.legacy_job.allowed();
	var legacy = logistics.legacy_job.is_legacy(frm);
	if (frm.fields_dict.is_legacy_job) {
		frm.toggle_display("is_legacy_job", allowed);
		frm.set_df_property("is_legacy_job", "read_only", !allowed || (legacy && !frm.is_new()) ? 1 : 0);
	}
	if (frm.fields_dict.is_beginning_job) {
		frm.toggle_display("is_beginning_job", 0);
	}
	if (frm.fields_dict.legacy_job_no) {
		frm.toggle_display("legacy_job_no", allowed && legacy);
		frm.toggle_reqd("legacy_job_no", allowed && legacy && frm.is_new());
		frm.set_df_property("legacy_job_no", "read_only", frm.is_new() ? 0 : 1);
	}
	if (frm.fields_dict.naming_series) {
		frm.toggle_display("naming_series", !legacy);
	}
	if (frm.fields_dict.charges) {
		frm.set_df_property("charges", "cannot_add_rows", legacy ? 0 : 1);
		frm.set_df_property("charges", "allow_bulk_edit", legacy ? 1 : 0);
		if (frm.fields_dict.charges.grid) {
			frm.fields_dict.charges.grid.cannot_add_rows = !legacy;
			frm.fields_dict.charges.grid.refresh();
		}
	}
};

logistics.legacy_job.sync_and_apply = function (frm) {
	if (!frm || !LEGACY_JOB_DOCTYPES[frm.doctype]) {
		return;
	}
	logistics.legacy_job.apply(frm);
	frappe.call({
		method: "logistics.job_management.legacy_job.get_allow_legacy_jobs",
		callback: function (r) {
			logistics.legacy_job.set_allowed(r && r.message);
			logistics.legacy_job.apply(frm);
		},
	});
};

(function () {
	if (logistics.legacy_job._handlers_registered) {
		return;
	}
	logistics.legacy_job._handlers_registered = true;
	Object.keys(LEGACY_JOB_DOCTYPES).forEach(function (doctype) {
		frappe.ui.form.on(doctype, {
			onload: function (frm) {
				logistics.legacy_job.sync_and_apply(frm);
			},
			refresh: function (frm) {
				logistics.legacy_job.apply(frm);
			},
			is_legacy_job: function (frm) {
				if (frm.fields_dict.is_beginning_job) {
					frm.set_value("is_beginning_job", _cint(frm.doc.is_legacy_job));
				}
				if (!_cint(frm.doc.is_legacy_job) && frm.is_new() && frm.fields_dict.legacy_job_no) {
					frm.set_value("legacy_job_no", "");
				}
				logistics.legacy_job.apply(frm);
			},
		});
	});
})();
