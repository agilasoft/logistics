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

	/**
	 * When this document is an internal-job satellite fully linked to a main job, both checkboxes
	 * must stay disabled (client `set_df_property` can otherwise override JSON `read_only_depends_on`).
	 */
	logistics.apply_internal_job_satellite_checkbox_locks = function (frm) {
		if (!frm || !frm.doc || !frm.get_docfield) {
			return;
		}
		var cint = frappe.utils.cint || function (v) {
			return parseInt(v, 10) || 0;
		};
		var linked =
			cint(frm.doc.is_internal_job) &&
			(String(frm.doc.main_job_type || "").trim()) &&
			(String(frm.doc.main_job || "").trim());
		if (!linked) {
			return;
		}
		["is_internal_job", "is_main_service"].forEach(function (fn) {
			if (!frm.get_docfield(fn)) {
				return;
			}
			frm.set_df_property(fn, "read_only", 1);
			frm.refresh_field(fn);
		});
	};

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
		var linkedIJ =
			cint(frm.doc.is_internal_job) &&
			(frm.doc.main_job_type || "").toString().trim() &&
			(frm.doc.main_job || "").toString().trim();
		var tasks = [];
		// Main Service and Internal Job are mutually exclusive. Do not force Main Service when this doc is
		// already an Internal Job (e.g. Declaration Order customs-only, or Transport Order / booking
		// satellites created from Internal Job on a one-off freight leg).
		if (
			main_fields.indexOf("is_main_service") !== -1 &&
			!cint(frm.doc.is_main_service) &&
			!cint(frm.doc.is_internal_job)
		) {
			tasks.push(Promise.resolve(frm.set_value("is_main_service", 1)));
		}
		// One-off locks Main Service read-only; mutual-exclusive set_value may not clear it when Internal Job
		// is turned on (e.g. internal-job dialog). Always drop Main Service if Internal Job is checked.
		if (cint(frm.doc.is_internal_job) && main_fields.indexOf("is_main_service") !== -1) {
			tasks.push(Promise.resolve(frm.set_value("is_main_service", 0)));
		}
		if (main_fields.indexOf("is_main_job") !== -1 && !cint(frm.doc.is_main_job)) {
			tasks.push(Promise.resolve(frm.set_value("is_main_job", 1)));
		}
		// Do not clear Internal Job when it is a linked satellite (Main Job Type / Main Job set), or on
		// Declaration Order (internal customs job without a freight main link is still valid).
		var skip_ij_clear = frm.doctype === "Declaration Order" || linkedIJ;
		if (has_ij && cint(frm.doc.is_internal_job) && !skip_ij_clear) {
			tasks.push(Promise.resolve(frm.set_value("is_internal_job", 0)));
		}
		if (tasks.length) {
			Promise.all(tasks).then(refresh_ms_ij_if_present).catch(refresh_ms_ij_if_present);
		}
	}

	logistics.apply_one_off_sales_quote_order_standard = function (frm, opts) {
		opts = opts || {};
		if (!frm || !frm.doc || !frm.get_docfield) return;
		logistics.apply_internal_job_satellite_checkbox_locks(frm);
		var main_fields = MAIN_JOB_FIELDNAMES.filter(function (fn) {
			return !!frm.get_docfield(fn);
		});
		var has_ij = !!frm.get_docfield("is_internal_job");
		if (!main_fields.length && !has_ij) return;

		var sq = frm.doc.sales_quote;
		var is_draft = !frm.doc.docstatus;

		function unlock_when_allowed() {
			if (!is_draft) return;
			var cint = frappe.utils.cint || function (v) {
				return parseInt(v, 10) || 0;
			};
			var linkedIJ =
				cint(frm.doc.is_internal_job) &&
				(frm.doc.main_job_type || "").toString().trim() &&
				(frm.doc.main_job || "").toString().trim();
			main_fields.forEach(function (fn) {
				if (fn === "is_main_service" && linkedIJ) {
					return;
				}
				frm.set_df_property(fn, "read_only", 0);
			});
			if (has_ij) {
				if (!linkedIJ) {
					frm.set_df_property("is_internal_job", "read_only", 0);
				}
			}
			if (linkedIJ) {
				if (frm.fields_dict.is_main_service) {
					frm.refresh_field("is_main_service");
				}
				if (has_ij && frm.fields_dict.is_internal_job) {
					frm.refresh_field("is_internal_job");
				}
			}
			// Standard / non–One-off quotes: must re-apply after unlock so linked internal-job satellites
			// stay read-only (same as read_only_depends_on in DocType JSON).
			logistics.apply_internal_job_satellite_checkbox_locks(frm);
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
