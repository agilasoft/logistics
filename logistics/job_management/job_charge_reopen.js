// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt
//
// Reopen/Close Job from Action menu — driven by logistics Job Status (charge_reopen.CHARGE_REOPEN_CONFIG).

frappe.provide("logistics.job_charge_reopen");

/** Locked Job Status values (must match logistics_job_status.CHARGE_LOCKED_STATUSES) */
var JOB_STATUS_CHARGE_LOCKED = {
	Completed: 1,
	Closed: 1,
};

/** status_field per DocType (must match charge_reopen.CHARGE_REOPEN_CONFIG) */
var JOB_CHARGE_REOPEN_STATUS_FIELD = {
	"Transport Job": "status",
	"Sea Shipment": "job_status",
	"Air Shipment": "job_status",
	"Warehouse Job": "job_status",
	Declaration: "job_status",
};

function _normalize_job_status_value(s) {
	if (s === undefined || s === null) {
		return "";
	}
	return String(s)
		.replace(/\u00a0/g, " ")
		.replace(/[\u200b-\u200d\ufeff]/g, "")
		.replace(/\s+/g, " ")
		.trim();
}

function _cint(v) {
	if (v === true || v === 1 || v === "1") {
		return 1;
	}
	var n = parseInt(v, 10);
	return isNaN(n) ? 0 : n;
}

function _remove_charge_reopen_buttons(frm) {
	if (typeof frm.remove_custom_button === "function") {
		frm.remove_custom_button(__("Reopen Job"), __("Action"));
		frm.remove_custom_button(__("Close Job"), __("Action"));
	}
}

logistics.job_charge_reopen._job_status_value = function (frm) {
	var fn = JOB_CHARGE_REOPEN_STATUS_FIELD[frm.doctype];
	if (!fn || !frm.doc) {
		return "";
	}
	return _normalize_job_status_value(frm.doc[fn]);
};

logistics.job_charge_reopen.is_charges_locked = function (frm) {
	var d = frm.doc;
	if (!d || _cint(d.docstatus) !== 1) {
		return false;
	}
	var js = logistics.job_charge_reopen._job_status_value(frm);
	if (!js || js.toLowerCase() === "reopened") {
		return false;
	}
	if (JOB_STATUS_CHARGE_LOCKED[js]) {
		return true;
	}
	var lower = js.toLowerCase();
	for (var k in JOB_STATUS_CHARGE_LOCKED) {
		if (k && k.toLowerCase() === lower) {
			return true;
		}
	}
	return false;
};

logistics.job_charge_reopen.can_close_job = function (frm) {
	var d = frm.doc;
	if (!d || _cint(d.docstatus) !== 1) {
		return false;
	}
	return logistics.job_charge_reopen._job_status_value(frm).toLowerCase() === "reopened";
};

logistics.job_charge_reopen.setup = function (frm, opts) {
	opts = opts || {};
	_remove_charge_reopen_buttons(frm);
	var d = frm.doc;
	var locked = logistics.job_charge_reopen.is_charges_locked(frm);
	if (frm.fields_dict.charges) {
		frm.set_df_property("charges", "read_only", locked ? 1 : 0);
	}
	if (!d || _cint(d.docstatus) !== 1) {
		return;
	}
	if (frm.doctype === "Sea Shipment" && opts.sea_deferred_buttons_only) {
		return;
	}
	if (frm.doctype === "Air Shipment" && opts.air_deferred_buttons_only) {
		return;
	}
	if (locked) {
		frm.add_custom_button(
			__("Reopen Job"),
			function () {
				frappe.call({
					method: "logistics.job_management.charge_reopen.reopen_job_for_charges",
					args: { doctype: frm.doctype, name: frm.doc.name },
					freeze: true,
					callback: function (r) {
						if (!r.exc) {
							frm.reload_doc();
						}
					},
				});
			},
			__("Action")
		);
	}
	if (logistics.job_charge_reopen.can_close_job(frm)) {
		frm.add_custom_button(
			__("Close Job"),
			function () {
				frappe.call({
					method: "logistics.job_management.charge_reopen.close_job_for_charges",
					args: { doctype: frm.doctype, name: frm.doc.name },
					freeze: true,
					callback: function (r) {
						if (!r.exc) {
							frm.reload_doc();
						}
					},
				});
			},
			__("Action")
		);
	}
};

(function () {
	if (logistics.job_charge_reopen._handlers_registered) {
		return;
	}
	logistics.job_charge_reopen._handlers_registered = true;
	var DOCTYPES = [
		"Transport Job",
		"Sea Shipment",
		"Air Shipment",
		"Warehouse Job",
		"Declaration",
	];
	DOCTYPES.forEach(function (dt) {
		frappe.ui.form.on(dt, {
			refresh: function (frm) {
				if (dt === "Sea Shipment") {
					logistics.job_charge_reopen.setup(frm, { sea_deferred_buttons_only: true });
				} else if (dt === "Air Shipment") {
					logistics.job_charge_reopen.setup(frm, { air_deferred_buttons_only: true });
				} else {
					logistics.job_charge_reopen.setup(frm);
				}
			},
		});
	});
})();
