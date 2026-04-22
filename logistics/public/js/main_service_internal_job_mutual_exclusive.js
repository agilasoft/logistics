// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Main Job (is_main_service) and Internal Job (is_internal_job) are mutually exclusive:
 * checking one clears the other on the same form interaction (no refresh).
 * `frappe.ui.form.on` requires a string doctype — do not pass an array as the first argument.
 */
(function () {
	"use strict";

	if (typeof frappe === "undefined" || !frappe.ui || !frappe.ui.form || !frappe.ui.form.on) {
		return;
	}

	var DOCTYPES_WITH_MS_AND_IJ = [
		"Air Booking",
		"Air Shipment",
		"Sea Booking",
		"Sea Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration Order",
		"Declaration",
		"Warehouse Job",
		"Inbound Order",
		"Release Order",
	];

	function has_both_fields(frm) {
		var ms = frm.get_docfield("is_main_service") || (frm.fields_dict && frm.fields_dict.is_main_service);
		var ij = frm.get_docfield("is_internal_job") || (frm.fields_dict && frm.fields_dict.is_internal_job);
		return !!(ms && ij);
	}

	/** Prefer control value: field triggers often run before `frm.doc` reflects the new check state. */
	function field_check_cint(frm, fieldname) {
		var fd = frm.fields_dict && frm.fields_dict[fieldname];
		if (fd && typeof fd.get_value === "function") {
			try {
				return frappe.utils.cint(fd.get_value());
			} catch (e) {
				/* ignore */
			}
		}
		return frappe.utils.cint(frm.doc[fieldname]);
	}

	function both_checked(frm) {
		return field_check_cint(frm, "is_main_service") && field_check_cint(frm, "is_internal_job");
	}

	/**
	 * When the user checks Main Service, Internal Job must turn off — and vice versa.
	 * Do not rely on `frm.doc` alone: checkbox handlers can fire before the model updates.
	 */
	function enforce_main_service_excludes_internal(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm)) return;
		if (field_check_cint(frm, "is_main_service")) {
			frm.set_value("is_internal_job", 0);
		}
	}

	function enforce_internal_excludes_main_service(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm)) return;
		if (field_check_cint(frm, "is_internal_job")) {
			frm.set_value("is_main_service", 0);
		}
	}

	/** Run now and on later ticks so we catch doc/control sync delays (Declaration Order, One-off, etc.). */
	function defer_enforce(frm, fn) {
		fn(frm);
		setTimeout(function () {
			fn(frm);
		}, 0);
		setTimeout(function () {
			fn(frm);
		}, 50);
	}

	/** If both are still on after refresh/async set_value (e.g. One-off), normalize once. */
	function normalize_if_both_checked(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm)) return;
		if (both_checked(frm)) {
			frm.set_value("is_main_service", 0);
		}
	}

	function schedule_normalize_if_both_checked(frm) {
		if (!frm || !frm.doc) return;
		// Run after other refresh hooks and microtasks (Promise.all from One-off script).
		setTimeout(function () {
			normalize_if_both_checked(frm);
		}, 0);
		setTimeout(function () {
			normalize_if_both_checked(frm);
		}, 100);
	}

	var field_handlers = {
		is_main_service: function (frm) {
			if (!frm || !frm.doc || !has_both_fields(frm)) return;
			defer_enforce(frm, enforce_main_service_excludes_internal);
		},
		is_internal_job: function (frm) {
			if (!frm || !frm.doc || !has_both_fields(frm)) return;
			defer_enforce(frm, enforce_internal_excludes_main_service);
		},
		refresh: function (frm) {
			schedule_normalize_if_both_checked(frm);
		},
	};

	DOCTYPES_WITH_MS_AND_IJ.forEach(function (dt) {
		frappe.ui.form.on(dt, field_handlers);
	});
})();
