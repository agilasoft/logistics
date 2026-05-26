// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Main Service / Internal Job rules from Sales Quote quotation_type, conversion state,
 * and main-service internal-job children. Loaded desk-wide (hooks app_include_js).
 */
(function () {
	"use strict";

	frappe.provide("logistics");

	var MAIN_JOB_FIELDNAMES = ["is_main_service", "is_main_job"];

	var MS_IJ_DOCTYPES = [
		"Air Booking",
		"Air Shipment",
		"Sea Booking",
		"Sea Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration Order",
		"Declaration",
		"Inbound Order",
		"Release Order",
		"Warehouse Job",
		"Project Job",
		"Exhibit Job",
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

	function ms_ij_checkbox_fieldnames(main_fields, has_ij) {
		var names = (main_fields || []).slice();
		if (has_ij && names.indexOf("is_internal_job") === -1) {
			names.push("is_internal_job");
		}
		return names;
	}

	function set_ms_ij_checkboxes_disabled(frm, fieldnames, disabled) {
		if (!frm || !frm.get_docfield) {
			return;
		}
		(fieldnames || []).forEach(function (fn) {
			if (!frm.get_docfield(fn)) {
				return;
			}
			frm.set_df_property(fn, "read_only", disabled ? 1 : 0);
			var field = frm.fields_dict[fn];
			if (!field) {
				frm.refresh_field(fn);
				return;
			}
			if (typeof field.toggle_enable === "function") {
				field.toggle_enable(!disabled);
			}
			frm.refresh_field(fn);
			setTimeout(function () {
				if (!frm || !frm.fields_dict || !frm.fields_dict[fn]) {
					return;
				}
				var fld = frm.fields_dict[fn];
				var $inp = fld.$input;
				if ($inp && $inp.length) {
					$inp.prop("disabled", !!disabled);
					$inp.closest(".checkbox, .form-check").toggleClass("disabled", !!disabled);
				}
			}, 0);
		});
	}

	function is_internal_job_satellite_doc(doc) {
		return (
			logistics_cint(doc.is_internal_job) &&
			String(doc.main_job_type || "").trim() &&
			String(doc.main_job || "").trim()
		);
	}

	function has_created_internal_job_children_client(doc) {
		var rows = doc.internal_job_details || [];
		for (var i = 0; i < rows.length; i++) {
			if (String(rows[i].job_no || "").trim()) {
				return true;
			}
		}
		return false;
	}

	function main_service_has_created_internal_jobs_client(doc) {
		return logistics_cint(doc.is_main_service) && has_created_internal_job_children_client(doc);
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

	/**
	 * Resolve UI state. mode: satellite | one_off | project | main_with_children | regular
	 */
	function resolve_ms_ij_state(doc, quotationType) {
		if (is_internal_job_satellite_doc(doc)) {
			return {
				mode: "satellite",
				is_main_service: 0,
				is_internal_job: 1,
				lock_main_service: true,
				lock_internal_job: true,
			};
		}
		if (is_one_off_quotation_type(quotationType)) {
			return {
				mode: "one_off",
				is_main_service: 1,
				is_internal_job: 0,
				lock_main_service: true,
				lock_internal_job: true,
			};
		}
		if (is_project_quotation_type(quotationType)) {
			return {
				mode: "project",
				is_main_service: 0,
				is_internal_job: 0,
				lock_main_service: true,
				lock_internal_job: true,
			};
		}
		if (has_created_internal_job_children_client(doc)) {
			return {
				mode: "main_with_children",
				is_main_service: 1,
				is_internal_job: 0,
				lock_main_service: true,
				lock_internal_job: false,
			};
		}
		return {
			mode: "regular",
			is_main_service: logistics_cint(doc.is_main_service),
			is_internal_job: logistics_cint(doc.is_internal_job),
			lock_main_service: false,
			lock_internal_job: false,
		};
	}

	function apply_ms_ij_state_to_form(frm, state, main_fields, has_ij, is_draft) {
		var ms_ij_fields = ms_ij_checkbox_fieldnames(main_fields, has_ij);
		frm._logistics_ms_ij_locked =
			state.lock_main_service || state.lock_internal_job;

		function after_values() {
			if (state.lock_main_service && main_fields.indexOf("is_main_service") !== -1) {
				set_ms_ij_checkboxes_disabled(frm, ["is_main_service"], true);
			} else if (main_fields.indexOf("is_main_service") !== -1) {
				set_ms_ij_checkboxes_disabled(frm, ["is_main_service"], false);
			}
			if (state.lock_internal_job && has_ij) {
				set_ms_ij_checkboxes_disabled(frm, ["is_internal_job"], true);
			} else if (has_ij) {
				set_ms_ij_checkboxes_disabled(frm, ["is_internal_job"], false);
			}
			if (state.lock_main_service && state.lock_internal_job) {
				set_ms_ij_checkboxes_disabled(frm, ms_ij_fields, true);
			}
		}

		if (!is_draft) {
			after_values();
			return;
		}

		var tasks = [];
		if (
			main_fields.indexOf("is_main_service") !== -1 &&
			logistics_cint(frm.doc.is_main_service) !== state.is_main_service
		) {
			tasks.push(Promise.resolve(frm.set_value("is_main_service", state.is_main_service)));
		}
		if (
			has_ij &&
			logistics_cint(frm.doc.is_internal_job) !== state.is_internal_job
		) {
			tasks.push(Promise.resolve(frm.set_value("is_internal_job", state.is_internal_job)));
		}
		if (tasks.length) {
			Promise.all(tasks).then(after_values).catch(after_values);
		} else {
			after_values();
		}
	}

	logistics.apply_internal_job_satellite_checkbox_locks = function (frm) {
		if (!frm || !frm.doc || !frm.get_docfield) {
			return;
		}
		if (!is_internal_job_satellite_doc(frm.doc)) {
			return;
		}
		set_ms_ij_checkboxes_disabled(frm, ["is_internal_job", "is_main_service"], true);
		frm._logistics_ms_ij_locked = true;
	};

	logistics.ms_ij_checkboxes_are_locked = function (frm) {
		return !!(frm && frm._logistics_ms_ij_locked);
	};

	function apply_rules_with_quotation_type(frm, main_fields, has_ij, is_draft, quotationType) {
		var state = resolve_ms_ij_state(frm.doc, quotationType);
		frm._logistics_sales_quote_quotation_type = quotationType || "";
		apply_ms_ij_state_to_form(frm, state, main_fields, has_ij, is_draft);
	}

	logistics.apply_sales_quote_ms_ij_rules = function (frm, opts) {
		opts = opts || {};
		if (!frm || !frm.doc || !frm.get_docfield) return;

		var main_fields = MAIN_JOB_FIELDNAMES.filter(function (fn) {
			return !!frm.get_docfield(fn);
		});
		var has_ij = !!frm.get_docfield("is_internal_job");
		if (!main_fields.length && !has_ij) return;

		var is_draft = !frm.doc.docstatus;
		var sq = (frm.doc.sales_quote || "").trim();
		var from_recheck = !!opts._from_ms_ij_recheck;

		// Satellite first (any quote type)
		if (is_internal_job_satellite_doc(frm.doc)) {
			apply_rules_with_quotation_type(frm, main_fields, has_ij, is_draft, null);
			if (!from_recheck) {
				schedule_ms_ij_recheck(frm, opts);
			}
			return;
		}

		if (opts.assume_one_off) {
			apply_rules_with_quotation_type(frm, main_fields, has_ij, is_draft, "One-off");
			if (!from_recheck) {
				schedule_ms_ij_recheck(frm, opts);
			}
			return;
		}

		// Scenario 1 without sales_quote still applies
		if (!sq || sq.indexOf("new-") === 0) {
			if (main_service_has_created_internal_jobs_client(frm.doc)) {
				apply_rules_with_quotation_type(frm, main_fields, has_ij, is_draft, null);
			} else {
				frm._logistics_ms_ij_locked = false;
				if (is_draft) {
					set_ms_ij_checkboxes_disabled(
						frm,
						ms_ij_checkbox_fieldnames(main_fields, has_ij),
						false
					);
				}
			}
			if (!from_recheck) {
				schedule_ms_ij_recheck(frm, opts);
			}
			return;
		}

		if (
			frm._logistics_one_off_route_pending &&
			(!sq || sq.indexOf("new-") === 0)
		) {
			return;
		}

		frappe.db.get_value("Sales Quote", sq, "quotation_type", function (r) {
			if (!frm.doc || (frm.doc.sales_quote || "").trim() !== sq) {
				return;
			}
			frm._logistics_one_off_route_pending = false;
			var qt =
				r && r.quotation_type != null ? String(r.quotation_type).trim() : "";
			apply_rules_with_quotation_type(frm, main_fields, has_ij, is_draft, qt);
		});

		if (!from_recheck) {
			schedule_ms_ij_recheck(frm, opts);
		}
	};

	logistics.apply_one_off_sales_quote_order_standard = logistics.apply_sales_quote_ms_ij_rules;

	/** Bounded deferred re-apply after set_value / DOM render. Must not reschedule itself (was freezing forms). */
	function schedule_ms_ij_recheck(frm, opts) {
		opts = opts || {};
		if (frm._logistics_ms_ij_recheck_scheduled) {
			return;
		}
		frm._logistics_ms_ij_recheck_scheduled = true;
		var recheck_opts = Object.assign({}, opts, { _from_ms_ij_recheck: true });
		var passes_left = 2;

		function run() {
			if (!frm || !frm.doc || passes_left <= 0) {
				if (frm) {
					frm._logistics_ms_ij_recheck_scheduled = false;
				}
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
					if (!frm.layout || !frm.layout.wrapper || frm._logistics_ms_ij_tab_bound) {
						return;
					}
					frm._logistics_ms_ij_tab_bound = true;
					frm.layout.wrapper.on(
						"shown.bs.tab.logistics_ms_ij",
						'[data-fieldname], a[data-toggle="tab"]',
						function () {
							if (logistics.apply_sales_quote_ms_ij_rules) {
								logistics.apply_sales_quote_ms_ij_rules(frm);
							}
						}
					);
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
				is_main_service: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
				is_internal_job: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
				internal_job_details: function (frm) {
					if (logistics.apply_sales_quote_ms_ij_rules) {
						logistics.apply_sales_quote_ms_ij_rules(frm);
					}
				},
			});
		});
	}
})();
