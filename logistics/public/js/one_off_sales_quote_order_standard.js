// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * One-off Sales Quote → Orders / Bookings: Main Job fields (is_main_service / is_main_job) and
 * Internal Job (is_internal_job) are read-only. Same behaviour for sea, air, transport,
 * warehousing, and customs target doctypes. Loaded desk-wide (see hooks app_include_js).
 * Safe no-op if fields are missing on the form.
 */
(function () {
	"use strict";

	frappe.provide("logistics");

	/** Parent-form fields that identify the main leg/job (doctypes use is_main_service; none use is_main_job on parent today). */
	var MAIN_JOB_FIELDNAMES = ["is_main_service", "is_main_job"];

	function apply_one_off_locks_and_defaults(frm, main_fields, has_ij, is_draft) {
		function lock_one_off() {
			main_fields.forEach(function (fn) {
				frm.set_df_property(fn, "read_only", 1);
			});
			if (has_ij) frm.set_df_property("is_internal_job", "read_only", 1);
		}
		// Lock immediately. Deferring lock until after frm.set_value() promises meant a window where
		// refresh could run with writable Main Service / Internal Job (set_value is async).
		lock_one_off();

		function refresh_ms_ij_if_present() {
			main_fields.forEach(function (fn) {
				if (frm.fields_dict[fn]) {
					frm.refresh_field(fn);
				}
			});
			if (frm.fields_dict.is_internal_job) {
				frm.refresh_field("is_internal_job");
			}
		}
		// Always re-render controls so read_only sticks (if we only lock and skip set_value tasks,
		// refresh never ran — checkboxes stayed clickable).
		refresh_ms_ij_if_present();
		if (!is_draft) {
			return;
		}
		var tasks = [];
		// Main Service and Internal Job are mutually exclusive. Declaration Order may keep Internal Job
		// (customs with no quote charges); do not force Main Service when Internal Job is set — that would
		// leave both checked (skip_ij_clear below would not clear Internal Job).
		if (
			main_fields.indexOf("is_main_service") !== -1 &&
			!frappe.utils.cint(frm.doc.is_main_service) &&
			!(frm.doctype === "Declaration Order" && frappe.utils.cint(frm.doc.is_internal_job))
		) {
			tasks.push(Promise.resolve(frm.set_value("is_main_service", 1)));
		}
		// One-off locks Main Service read-only; mutual-exclusive set_value may not clear it when Internal Job
		// is turned on (e.g. internal-job dialog). Always drop Main Service if Internal Job is set on DO.
		if (frm.doctype === "Declaration Order" && frappe.utils.cint(frm.doc.is_internal_job)) {
			tasks.push(Promise.resolve(frm.set_value("is_main_service", 0)));
		}
		if (main_fields.indexOf("is_main_job") !== -1 && !frappe.utils.cint(frm.doc.is_main_job)) {
			tasks.push(Promise.resolve(frm.set_value("is_main_job", 1)));
		}
		// Declaration Order can be an Internal Job (customs with no quote charges); do not clear the flag.
		var skip_ij_clear = frm.doctype === "Declaration Order";
		if (has_ij && frappe.utils.cint(frm.doc.is_internal_job) && !skip_ij_clear) {
			tasks.push(Promise.resolve(frm.set_value("is_internal_job", 0)));
		}
		if (tasks.length) {
			Promise.all(tasks).then(refresh_ms_ij_if_present).catch(refresh_ms_ij_if_present);
		}
	}

	logistics.apply_one_off_sales_quote_order_standard = function (frm, opts) {
		opts = opts || {};
		if (!frm || !frm.doc || !frm.get_docfield) return;
		var main_fields = MAIN_JOB_FIELDNAMES.filter(function (fn) {
			return !!frm.get_docfield(fn);
		});
		var has_ij = !!frm.get_docfield("is_internal_job");
		if (!main_fields.length && !has_ij) return;

		var sq = frm.doc.sales_quote;
		var is_draft = !frm.doc.docstatus;

		function unlock_when_allowed() {
			if (!is_draft) return;
			main_fields.forEach(function (fn) {
				frm.set_df_property(fn, "read_only", 0);
			});
			if (has_ij) frm.set_df_property("is_internal_job", "read_only", 0);
		}

		// Must run before the empty sales_quote check: onload can fire before frm.doc.sales_quote is set
		// (e.g. One-off → order/booking with route_options), which would unlock and return early otherwise.
		if (opts.assume_one_off) {
			apply_one_off_locks_and_defaults(frm, main_fields, has_ij, is_draft);
			return;
		}

		// One-off navigation from Sales Quote can refresh before sales_quote is on the client;
		// unlock_when_allowed() would clear locks applied in onload — keep locks until we have sq + type.
		if (
			(!sq || String(sq).indexOf("new-") === 0) &&
			frm._logistics_one_off_route_pending
		) {
			return;
		}

		if (!sq || String(sq).indexOf("new-") === 0) {
			unlock_when_allowed();
			return;
		}

		frappe.db.get_value("Sales Quote", sq, "quotation_type", function (r) {
			if (!frm.doc || frm.doc.sales_quote !== sq) return;
			frm._logistics_one_off_route_pending = false;
			var qt = (r && r.quotation_type) != null ? String(r.quotation_type).trim() : "";
			if (qt === "One-off") {
				apply_one_off_locks_and_defaults(frm, main_fields, has_ij, is_draft);
			} else {
				unlock_when_allowed();
			}
		});
	};

	/**
	 * Call from Form onload when `frappe.route_options.logistics_one_off_order_route` or legacy
	 * `logistics_declaration_order_one_off` is set (navigation from a One-off Sales Quote).
	 */
	logistics.apply_one_off_route_options_onload = function (frm) {
		if (!frm || !frappe.route_options) return;
		var ro = frappe.route_options;
		if (!ro.logistics_one_off_order_route && !ro.logistics_declaration_order_one_off) return;
		if (ro.logistics_declaration_order_one_off) {
			delete ro.logistics_declaration_order_one_off;
		}
		if (ro.logistics_one_off_order_route) {
			delete ro.logistics_one_off_order_route;
		}
		frm._logistics_one_off_route_pending = true;
		logistics.apply_one_off_sales_quote_order_standard(frm, { assume_one_off: true });
	};
})();
