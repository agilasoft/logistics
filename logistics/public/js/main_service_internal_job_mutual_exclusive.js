// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Main Service (is_main_service) and Internal Job (is_internal_job) are mutually exclusive
 * on Regular quotes when checkboxes are not locked by sales_quote_ms_ij_rules.
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
		"Project Job",
		"Exhibit Job",
	];

	var CHANGE_NS = ".logistics_ms_ij_exclusive";

	function cint(v) {
		return frappe.utils.cint ? frappe.utils.cint(v) : parseInt(v, 10) || 0;
	}

	function has_both_fields(frm) {
		var ms = frm.get_docfield("is_main_service") || (frm.fields_dict && frm.fields_dict.is_main_service);
		var ij = frm.get_docfield("is_internal_job") || (frm.fields_dict && frm.fields_dict.is_internal_job);
		return !!(ms && ij);
	}

	function checkboxes_locked(frm) {
		return (
			window.logistics &&
			logistics.ms_ij_checkboxes_are_locked &&
			logistics.ms_ij_checkboxes_are_locked(frm)
		);
	}

	function input_checked($inp) {
		return $inp && $inp.length && !!$inp.prop("checked");
	}

	function bind_mutually_exclusive_checkboxes(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm) || checkboxes_locked(frm)) {
			return;
		}
		var ms = frm.fields_dict.is_main_service;
		var ij = frm.fields_dict.is_internal_job;
		if (!ms || !ij) {
			return;
		}

		function wire() {
			var $ms = ms.$input;
			var $ij = ij.$input;
			if (!$ms || !$ms.length || !$ij || !$ij.length) {
				return false;
			}
			$ms.off("change" + CHANGE_NS);
			$ij.off("change" + CHANGE_NS);

			$ms.on("change" + CHANGE_NS, function () {
				if (checkboxes_locked(frm)) {
					return;
				}
				if (input_checked($ms)) {
					frm.set_value("is_internal_job", 0);
				}
			});
			$ij.on("change" + CHANGE_NS, function () {
				if (checkboxes_locked(frm)) {
					return;
				}
				if (input_checked($ij)) {
					frm.set_value("is_main_service", 0);
				}
			});
			return true;
		}

		if (!wire()) {
			setTimeout(function () {
				if (frm && frm.doc && !checkboxes_locked(frm)) {
					wire();
				}
			}, 0);
		}
	}

	function normalize_if_both_checked(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm) || checkboxes_locked(frm)) {
			return;
		}
		if (cint(frm.doc.is_main_service) && cint(frm.doc.is_internal_job)) {
			frm.set_value("is_main_service", 0);
		}
	}

	function on_main_service_form_change(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm) || checkboxes_locked(frm)) {
			return;
		}
		if (cint(frm.doc.is_main_service)) {
			frm.set_value("is_internal_job", 0);
		}
	}

	function on_internal_job_form_change(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm) || checkboxes_locked(frm)) {
			return;
		}
		if (cint(frm.doc.is_internal_job)) {
			frm.set_value("is_main_service", 0);
		}
	}

	var field_handlers = {
		is_main_service: on_main_service_form_change,
		is_internal_job: on_internal_job_form_change,
		refresh: function (frm) {
			if (window.logistics && logistics.apply_sales_quote_ms_ij_rules) {
				logistics.apply_sales_quote_ms_ij_rules(frm);
			}
			setTimeout(function () {
				bind_mutually_exclusive_checkboxes(frm);
				normalize_if_both_checked(frm);
			}, 50);
		},
	};

	DOCTYPES_WITH_MS_AND_IJ.forEach(function (dt) {
		frappe.ui.form.on(dt, field_handlers);
	});
})();
