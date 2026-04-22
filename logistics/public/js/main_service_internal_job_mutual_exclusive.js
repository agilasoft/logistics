// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Main Service (is_main_service) and Internal Job (is_internal_job) are mutually exclusive.
 * Native checkbox `change` on each control reads the live checked state and immediately
 * `frm.set_value`s the other field off so the grid updates in the same interaction.
 * Refresh also normalizes when both are on (programmatic / One-off / dialog loads).
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

	var CHANGE_NS = ".logistics_ms_ij_exclusive";

	function has_both_fields(frm) {
		var ms = frm.get_docfield("is_main_service") || (frm.fields_dict && frm.fields_dict.is_main_service);
		var ij = frm.get_docfield("is_internal_job") || (frm.fields_dict && frm.fields_dict.is_internal_job);
		return !!(ms && ij);
	}

	function input_checked($inp) {
		return $inp && $inp.length && !!$inp.prop("checked");
	}

	function both_checked_from_doc(frm) {
		return (
			cint(frm.doc.is_main_service) && cint(frm.doc.is_internal_job)
		);
	}

	/**
	 * Bind once per refresh to the real checkbox inputs so `change` runs after the click toggles DOM.
	 */
	function bind_mutually_exclusive_checkboxes(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm)) {
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
				if (input_checked($ms)) {
					frm.set_value("is_internal_job", 0);
				}
			});
			$ij.on("change" + CHANGE_NS, function () {
				if (input_checked($ij)) {
					frm.set_value("is_main_service", 0);
				}
			});
			return true;
		}

		if (!wire()) {
			setTimeout(function () {
				if (frm && frm.doc) {
					wire();
				}
			}, 0);
		}
	}

	function normalize_if_both_checked(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm)) {
			return;
		}
		if (both_checked_from_doc(frm)) {
			frm.set_value("is_main_service", 0);
		}
	}

	function schedule_normalize_if_both_checked(frm) {
		if (!frm || !frm.doc) {
			return;
		}
		setTimeout(function () {
			normalize_if_both_checked(frm);
		}, 0);
	}

	/** When Frappe updates checks via `set_value` (no native `change`), doc is already current. */
	function on_main_service_form_change(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm)) {
			return;
		}
		if (cint(frm.doc.is_main_service)) {
			frm.set_value("is_internal_job", 0);
		}
	}

	function on_internal_job_form_change(frm) {
		if (!frm || !frm.doc || !has_both_fields(frm)) {
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
			bind_mutually_exclusive_checkboxes(frm);
			schedule_normalize_if_both_checked(frm);
		},
	};

	DOCTYPES_WITH_MS_AND_IJ.forEach(function (dt) {
		frappe.ui.form.on(dt, field_handlers);
	});
})();
