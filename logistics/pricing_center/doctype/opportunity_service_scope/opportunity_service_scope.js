// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

(function () {
	"use strict";

	const LOAD_TYPE_FLAG_BY_SERVICE = {
		Air: "air",
		Sea: "sea",
		Transport: "transport",
		Customs: "customs",
		Custom: "customs",
		Warehousing: "warehousing",
	};

	function load_type_flag_for_service_type(service_type) {
		const key = String(service_type || "").trim();
		return LOAD_TYPE_FLAG_BY_SERVICE[key] || null;
	}

	function refresh_scope_row_dependencies(frm, cdt, cdn) {
		const grid = frm.fields_dict.custom_opportunity_scopes && frm.fields_dict.custom_opportunity_scopes.grid;
		if (grid && grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn]) {
			grid.grid_rows_by_docname[cdn].refresh_dependency();
		}
		const open_form = frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form();
		if (
			open_form &&
			open_form.row &&
			open_form.row.doc &&
			open_form.row.doc.name === cdn &&
			open_form.layout
		) {
			const row_doc = locals[cdt] && locals[cdt][cdn];
			open_form.layout.refresh_dependency();
			if (typeof open_form.layout.refresh_sections === "function") {
				open_form.layout.refresh_sections();
			}
			if (row_doc) {
				open_form.layout.refresh(row_doc);
			}
		}
	}

	function clear_incompatible_load_type(cdt, cdn, service_type) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row || !row.load_type) {
			return;
		}
		const flag = load_type_flag_for_service_type(service_type);
		if (!flag) {
			return;
		}
		frappe.db.get_value("Load Type", row.load_type, flag, (r) => {
			if (r && r[flag]) {
				return;
			}
			frappe.model.set_value(cdt, cdn, "load_type", "");
		});
	}

	function clear_incompatible_transport_mode(cdt, cdn, service_type) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row || !row.transport_mode) {
			return;
		}
		const flag = load_type_flag_for_service_type(service_type);
		if (!flag) {
			return;
		}
		frappe.db.get_value("Transport Mode", row.transport_mode, flag, (r) => {
			if (r && r[flag]) {
				return;
			}
			frappe.model.set_value(cdt, cdn, "transport_mode", "");
		});
	}

	function strip_load_type_link_filters(frm) {
		const df = frappe.meta.get_docfield("Opportunity Service Scope", "load_type");
		if (df && df.link_filters) {
			df.link_filters = null;
		}
		const grid = frm.fields_dict.custom_opportunity_scopes && frm.fields_dict.custom_opportunity_scopes.grid;
		if (grid) {
			const gdf = grid.get_docfield("load_type");
			if (gdf && gdf.link_filters) {
				gdf.link_filters = null;
			}
		}
	}

	function strip_transport_mode_link_filters(frm) {
		const df = frappe.meta.get_docfield("Opportunity Service Scope", "transport_mode");
		if (df && df.link_filters) {
			df.link_filters = null;
		}
		const grid = frm.fields_dict.custom_opportunity_scopes && frm.fields_dict.custom_opportunity_scopes.grid;
		if (grid) {
			const gdf = grid.get_docfield("transport_mode");
			if (gdf && gdf.link_filters) {
				gdf.link_filters = null;
			}
		}
	}

	window.logistics_setup_opportunity_scope_queries = function (frm) {
		if (!frm.fields_dict.custom_opportunity_scopes) {
			return;
		}
		strip_load_type_link_filters(frm);
		strip_transport_mode_link_filters(frm);
		frm.set_query("load_type", "custom_opportunity_scopes", function (doc, cdt, cdn) {
			strip_load_type_link_filters(frm);
			const row = (locals[cdt] && locals[cdt][cdn]) || doc;
			const filters = { is_active: 1 };
			const flag = load_type_flag_for_service_type(row && row.service_type);
			if (flag) {
				filters[flag] = 1;
			}
			return { filters };
		});
		frm.set_query("transport_mode", "custom_opportunity_scopes", function (doc, cdt, cdn) {
			strip_transport_mode_link_filters(frm);
			const row = (locals[cdt] && locals[cdt][cdn]) || doc;
			const filters = { is_active: 1 };
			const flag = load_type_flag_for_service_type(row && row.service_type);
			if (flag) {
				filters[flag] = 1;
			}
			return { filters };
		});
	};

	window.logistics_refresh_scope_row_dependencies = refresh_scope_row_dependencies;

	frappe.ui.form.on("Opportunity Service Scope", {
		form_render(frm, cdt, cdn) {
			if (frm.doctype !== "Opportunity") {
				return;
			}
			logistics_setup_opportunity_scope_queries(frm);
			setTimeout(() => refresh_scope_row_dependencies(frm, cdt, cdn), 0);
		},
		service_type(frm, cdt, cdn) {
			const row = locals[cdt] && locals[cdt][cdn];
			setTimeout(() => {
				refresh_scope_row_dependencies(frm, cdt, cdn);
				clear_incompatible_load_type(cdt, cdn, row && row.service_type);
				clear_incompatible_transport_mode(cdt, cdn, row && row.service_type);
			if (typeof logistics_refresh_opportunity_scope_actuals === "function") {
				logistics_refresh_opportunity_scope_actuals(frm);
			}
			if (typeof logistics.opportunity_dashboard !== "undefined") {
				logistics.opportunity_dashboard.invalidate(frm);
			}
			}, 0);
		},
	});
})();
