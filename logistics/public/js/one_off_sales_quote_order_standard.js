// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * One-off Sales Quote → Orders / Bookings: Main Service is always enabled; Internal Job is read-only.
 * Loaded desk-wide (see hooks app_include_js). Safe no-op if fields are missing on the form.
 */
(function () {
	"use strict";

	frappe.provide("logistics");

	logistics.apply_one_off_sales_quote_order_standard = function (frm) {
		if (!frm || !frm.doc || !frm.get_docfield) return;
		var has_ms = !!frm.get_docfield("is_main_service");
		var has_ij = !!frm.get_docfield("is_internal_job");
		if (!has_ms && !has_ij) return;

		var sq = frm.doc.sales_quote;
		var is_draft = !frm.doc.docstatus;

		function lock_one_off() {
			if (has_ms) frm.set_df_property("is_main_service", "read_only", 1);
			if (has_ij) frm.set_df_property("is_internal_job", "read_only", 1);
		}

		function unlock_when_allowed() {
			if (!is_draft) return;
			if (has_ms) frm.set_df_property("is_main_service", "read_only", 0);
			if (has_ij) frm.set_df_property("is_internal_job", "read_only", 0);
		}

		if (!sq || String(sq).indexOf("new-") === 0) {
			unlock_when_allowed();
			return;
		}

		frappe.db.get_value("Sales Quote", sq, "quotation_type", function (r) {
			if (!frm.doc || frm.doc.sales_quote !== sq) return;
			var qt = r && r.quotation_type;
			if (qt === "One-off") {
				if (is_draft) {
					if (has_ms && !frappe.utils.cint(frm.doc.is_main_service)) {
						frm.set_value("is_main_service", 1);
					}
					if (has_ij && frappe.utils.cint(frm.doc.is_internal_job)) {
						frm.set_value("is_internal_job", 0);
					}
				}
				lock_one_off();
			} else {
				unlock_when_allowed();
			}
		});
	};
})();
