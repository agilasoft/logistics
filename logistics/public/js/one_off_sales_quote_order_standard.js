// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Service Role rules from Sales Quote quotation_type and Linked Service children.
 * Loaded desk-wide (hooks app_include_js).
 */
(function () {
	"use strict";

	frappe.provide("logistics");

	var MS_IJ_DOCTYPES = [
		"Air Booking",
		"Air Shipment",
		"Sea Booking",
		"Sea Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration Order",
		"Declaration",
		"VAS Order",
		"Inbound Order",
		"Release Order",
		"Warehouse Job",
		"Project Job",
		"MICE Job",
	];

	function logistics_cint(v) {
		if (frappe.utils && frappe.utils.cint) {
			return frappe.utils.cint(v);
		}
		return parseInt(v, 10) || 0;
	}

	logistics.sync_form_breadcrumbs = function (frmOrDoctype) {
		var dt =
			typeof frmOrDoctype === "string"
				? frmOrDoctype
				: frmOrDoctype && frmOrDoctype.doctype;
		if (!dt) {
			return;
		}
		frappe.model.with_doctype(dt, function () {
			var meta = frappe.get_meta(dt);
			if (meta && meta.module) {
				frappe.breadcrumbs.add(meta.module, dt);
			}
		});
	};

	function service_role_from_doc(doc) {
		if (!doc) return "Standalone";
		var role = String(doc.service_role || "").trim();
		if (role === "Main" || role === "Linked" || role === "Standalone") {
			return role;
		}
		var mt = String(doc.main_service_type || doc.main_job_type || "").trim();
		var mn = String(doc.main_service || doc.main_job || "").trim();
		if (mt && mn) return "Linked";
		if (logistics_cint(doc.is_internal_job)) return "Linked";
		if (logistics_cint(doc.is_main_service)) return "Main";
		return "Standalone";
	}

	function is_linked_satellite_doc(doc) {
		if (service_role_from_doc(doc) !== "Linked") return false;
		var mt = String(doc.main_service_type || doc.main_job_type || "").trim();
		var mn = String(doc.main_service || doc.main_job || "").trim();
		return !!(mt && mn);
	}

	function has_created_linked_service_children_client(doc) {
		var rows = doc.linked_services || doc.internal_job_details || doc.internal_jobs || [];
		for (var i = 0; i < rows.length; i++) {
			if (String(rows[i].job_no || "").trim()) {
				return true;
			}
		}
		return false;
	}

	function is_one_off_quotation_type(quotationType) {
		if (window.logistics && logistics.is_one_off_sales_quote_type) {
			return logistics.is_one_off_sales_quote_type(quotationType);
		}
		return (quotationType || "").trim() === "One-off";
	}

	function is_project_quotation_type(quotationType) {
		if (window.logistics && logistics.is_project_sales_quote_type) {
			return logistics.is_project_sales_quote_type(quotationType);
		}
		return (quotationType || "").trim() === "Project";
	}

	function resolve_service_role_state(doc, quotationType) {
		if (is_linked_satellite_doc(doc)) {
			return { mode: "satellite", service_role: "Linked", lock: true };
		}
		if (is_one_off_quotation_type(quotationType)) {
			return { mode: "one_off", service_role: "Main", lock: true };
		}
		if (is_project_quotation_type(quotationType)) {
			return { mode: "project", service_role: "Standalone", lock: true };
		}
		if (has_created_linked_service_children_client(doc)) {
			return { mode: "main_with_children", service_role: "Main", lock: true };
		}
		return {
			mode: "regular",
			service_role: service_role_from_doc(doc),
			lock: false,
		};
	}

	function apply_service_role_state_to_form(frm, state, is_draft) {
		frm._logistics_ms_ij_locked = !!state.lock;

		function after_values() {
			if (frm.fields_dict.service_role) {
				frm.set_df_property("service_role", "read_only", 1);
			}
			if (typeof logistics_apply_service_role_field_visibility === "function") {
				logistics_apply_service_role_field_visibility(frm);
			}
		}

		if (!is_draft || !frm.get_docfield("service_role")) {
			after_values();
			return;
		}

		if (String(frm.doc.service_role || "").trim() !== state.service_role) {
			Promise.resolve(frm.set_value("service_role", state.service_role))
				.then(after_values)
				.catch(after_values);
		} else {
			after_values();
		}
	}

	logistics.apply_internal_job_satellite_checkbox_locks = function (frm) {
		if (!frm || !frm.doc) return;
		if (!is_linked_satellite_doc(frm.doc)) return;
		frm._logistics_ms_ij_locked = true;
		if (typeof logistics_apply_service_role_field_visibility === "function") {
			logistics_apply_service_role_field_visibility(frm);
		}
	};

	logistics.ms_ij_checkboxes_are_locked = function (frm) {
		return !!(frm && frm._logistics_ms_ij_locked);
	};

	function apply_rules_with_quotation_type(frm, is_draft, quotationType) {
		var state = resolve_service_role_state(frm.doc, quotationType);
		frm._logistics_sales_quote_quotation_type = quotationType || "";
		apply_service_role_state_to_form(frm, state, is_draft);
	}

	logistics.apply_sales_quote_ms_ij_rules = function (frm, opts) {
		opts = opts || {};
		if (!frm || !frm.doc || !frm.get_docfield) return;
		if (!frm.get_docfield("service_role")) return;

		var is_draft = !frm.doc.docstatus;
		var sq = (frm.doc.sales_quote || "").trim();
		var from_recheck = !!opts._from_ms_ij_recheck;

		if (is_linked_satellite_doc(frm.doc)) {
			apply_rules_with_quotation_type(frm, is_draft, null);
			if (!from_recheck) schedule_ms_ij_recheck(frm, opts);
			return;
		}

		if (opts.assume_one_off) {
			apply_rules_with_quotation_type(frm, is_draft, "One-off");
			if (!from_recheck) schedule_ms_ij_recheck(frm, opts);
			return;
		}

		if (!sq || sq.indexOf("new-") === 0) {
			if (has_created_linked_service_children_client(frm.doc)) {
				apply_rules_with_quotation_type(frm, is_draft, null);
			} else {
				frm._logistics_ms_ij_locked = false;
				if (typeof logistics_apply_service_role_field_visibility === "function") {
					logistics_apply_service_role_field_visibility(frm);
				}
			}
			if (!from_recheck) schedule_ms_ij_recheck(frm, opts);
			return;
		}

		if (frm._logistics_one_off_route_pending && (!sq || sq.indexOf("new-") === 0)) {
			return;
		}

		frappe.db.get_value("Sales Quote", sq, "quotation_type", function (r) {
			if (!frm.doc || (frm.doc.sales_quote || "").trim() !== sq) {
				return;
			}
			frm._logistics_one_off_route_pending = false;
			var qt = r && r.quotation_type != null ? String(r.quotation_type).trim() : "";
			apply_rules_with_quotation_type(frm, is_draft, qt);
		});

		if (!from_recheck) schedule_ms_ij_recheck(frm, opts);
	};

	logistics.apply_one_off_sales_quote_order_standard = logistics.apply_sales_quote_ms_ij_rules;

	function schedule_ms_ij_recheck(frm, opts) {
		opts = opts || {};
		if (frm._logistics_ms_ij_recheck_scheduled) return;
		frm._logistics_ms_ij_recheck_scheduled = true;
		var recheck_opts = Object.assign({}, opts, { _from_ms_ij_recheck: true });
		var passes_left = 2;

		function run() {
			if (!frm || !frm.doc || passes_left <= 0) {
				if (frm) frm._logistics_ms_ij_recheck_scheduled = false;
				return;
			}
			passes_left -= 1;
			logistics.apply_sales_quote_ms_ij_rules(frm, recheck_opts);
			if (passes_left <= 0 && frm) {
				frm._logistics_ms_ij_recheck_scheduled = false;
			}
		}

		setTimeout(run, 0);
		setTimeout(run, 150);
	}

	logistics.apply_one_off_route_options_onload = function (frm) {
		if (!frm || !frappe.route_options) return;
		var ro = frappe.route_options;
		if (!ro.logistics_one_off_order_route && !ro.logistics_declaration_order_one_off) {
			return;
		}
		if (ro.logistics_declaration_order_one_off) {
			delete ro.logistics_declaration_order_one_off;
		}
		if (ro.logistics_one_off_order_route) {
			delete ro.logistics_one_off_order_route;
		}
		frm._logistics_one_off_route_pending = true;
		logistics.apply_sales_quote_ms_ij_rules(frm, { assume_one_off: true });
	};

	if (typeof frappe !== "undefined" && frappe.ui && frappe.ui.form && frappe.ui.form.on) {
		MS_IJ_DOCTYPES.forEach(function (dt) {
			frappe.ui.form.on(dt, {
				refresh: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
				sales_quote: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
				project: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
				service_role: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
				linked_services: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
			});
		});
	}
})();
