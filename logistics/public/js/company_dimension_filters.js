// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Branch and Cost Center link fields follow the Company set on the same form,
 * child row, dialog, or report filter.
 *
 * Branch is stored against Branch.custom_company. Cost Center uses company,
 * and only non-group, enabled cost centers are offered.
 *
 * Linked Service and Linked Service Detail leave Branch unfiltered. A service
 * branch is copied onto the booking and is not company-scoped. Cost Center on
 * those doctypes still follows the service company.
 * Profit Center is not company-filtered.
 */
(function () {
	"use strict";

	if (window.__logistics_company_dimension_filters__) {
		return;
	}
	window.__logistics_company_dimension_filters__ = true;

	const BRANCH_UNFILTERED = {
		"Linked Service": true,
		"Linked Service Detail": true,
	};

	function linked_company_field(doctype) {
		if (frappe.meta && frappe.meta.has_field(doctype, "company")) return "company";
		if (frappe.meta && frappe.meta.has_field(doctype, "custom_company")) return "custom_company";
		if (doctype === "Branch") return "custom_company";
		if (doctype === "Cost Center") return "company";
		return null;
	}

	function is_link(df, options) {
		return !!(df && df.fieldtype === "Link" && df.options === options);
	}

	function is_company_link(df) {
		return !!(
			df &&
			df.fieldtype === "Link" &&
			df.options === "Company" &&
			(df.fieldname === "company" || df.fieldname === "custom_company")
		);
	}

	function dimension_filters(doctype, company) {
		const filters = {};
		if (doctype === "Cost Center") {
			filters.is_group = 0;
			filters.disabled = 0;
		}
		const company_field = linked_company_field(doctype);
		if (company && company_field) {
			filters[company_field] = company;
		}
		return filters;
	}

	function dimension_query(doctype, get_company) {
		return function () {
			const company = (typeof get_company === "function" ? get_company() : get_company) || "";
			return { filters: dimension_filters(doctype, company) };
		};
	}

	function company_fieldname(fields) {
		const df = (fields || []).find(is_company_link);
		return df ? df.fieldname : null;
	}

	function merge_query_filters(base, extra) {
		const out = base && typeof base === "object" ? base : {};
		if (Array.isArray(out.filters)) {
			const rows = out.filters.slice();
			Object.keys(extra || {}).forEach(function (fieldname) {
				const exists = rows.some(function (row) {
					if (!Array.isArray(row)) return false;
					const name = row.length >= 4 ? row[1] : row[0];
					return name === fieldname;
				});
				if (!exists) {
					rows.push([fieldname, "=", extra[fieldname]]);
				}
			});
			out.filters = rows;
			return out;
		}
		out.filters = Object.assign({}, out.filters || {}, extra || {});
		return out;
	}

	function wrap_get_query(control, doctype, get_company) {
		if (!control || control.__logistics_company_dimension) return;
		const previous = control.get_query;
		control.get_query = function () {
			const company = (typeof get_company === "function" ? get_company() : get_company) || "";
			const base = typeof previous === "function" ? previous.apply(this, arguments) || {} : {};
			return merge_query_filters(base, dimension_filters(doctype, company));
		};
		control.__logistics_company_dimension = true;
	}

	function apply_parent_queries(frm) {
		const fieldname = company_fieldname(frm.meta.fields);
		if (!fieldname) return;
		const company = function () {
			return frm.doc && frm.doc[fieldname];
		};
		const skip_branch = !!BRANCH_UNFILTERED[frm.doctype];
		(frm.meta.fields || []).forEach(function (df) {
			if (df.fieldtype === "Table") return;
			if (!skip_branch && is_link(df, "Branch")) {
				frm.set_query(df.fieldname, dimension_query("Branch", company));
			}
			if (is_link(df, "Cost Center")) {
				frm.set_query(df.fieldname, dimension_query("Cost Center", company));
			}
		});
	}

	function apply_child_queries(frm, table_df) {
		const child_dt = table_df.options;
		const meta = frappe.get_meta(child_dt);
		if (!meta) {
			frappe.model.with_doctype(child_dt, function () {
				if (frm.doctype) {
					apply_child_queries(frm, table_df);
				}
			});
			return;
		}
		const grid_field = frm.fields_dict && frm.fields_dict[table_df.fieldname];
		if (!grid_field || !grid_field.grid || typeof grid_field.grid.get_field !== "function") {
			return;
		}
		const child_company = company_fieldname(meta.fields);
		const skip_branch = !!BRANCH_UNFILTERED[child_dt];
		const company_of_row = function (doc, cdt, cdn) {
			const row = locals[cdt] && locals[cdt][cdn];
			if (child_company && row && row[child_company]) {
				return row[child_company];
			}
			const parent_field = company_fieldname(frm.meta.fields);
			return parent_field && doc ? doc[parent_field] : "";
		};
		(meta.fields || []).forEach(function (field) {
			const grid_df = grid_field.grid.get_field(field.fieldname);
			if (!grid_df) return;
			if (!skip_branch && is_link(field, "Branch")) {
				frm.set_query(field.fieldname, table_df.fieldname, function (doc, cdt, cdn) {
					return dimension_query("Branch", function () {
						return company_of_row(doc, cdt, cdn);
					})();
				});
			}
			if (is_link(field, "Cost Center")) {
				frm.set_query(field.fieldname, table_df.fieldname, function (doc, cdt, cdn) {
					return dimension_query("Cost Center", function () {
						return company_of_row(doc, cdt, cdn);
					})();
				});
			}
		});
	}

	function apply(frm) {
		if (!frm || !frm.meta || !frm.doc || !company_fieldname(frm.meta.fields)) {
			return;
		}
		apply_parent_queries(frm);
		(frm.meta.fields || []).forEach(function (df) {
			if (df.fieldtype === "Table" && df.options) {
				apply_child_queries(frm, df);
			}
		});
	}

	function clear_mismatched(frm) {
		const fieldname = company_fieldname(frm.meta && frm.meta.fields);
		const company = fieldname && frm.doc && frm.doc[fieldname];
		if (!company) return;
		const skip_branch = !!BRANCH_UNFILTERED[frm.doctype];
		(frm.meta.fields || []).forEach(function (df) {
			if (df.fieldtype === "Table" || df.read_only) return;
			const doctype = is_link(df, "Branch") ? "Branch" : is_link(df, "Cost Center") ? "Cost Center" : null;
			if (!doctype || (doctype === "Branch" && skip_branch)) return;
			const value = frm.doc[df.fieldname];
			if (!value) return;
			const company_field = linked_company_field(doctype);
			if (!company_field) return;
			frappe.db.get_value(doctype, value, company_field, function (r) {
				const linked_company = r && r[company_field];
				if (linked_company && linked_company !== company && frm.doc[fieldname] === company) {
					frm.set_value(df.fieldname, "");
				}
			});
		});
	}

	function apply_dialog(dialog) {
		if (!dialog || !dialog.fields_dict || !dialog.fields) return;
		const company_df = dialog.fields.find(is_company_link);
		if (!company_df) return;
		dialog.fields.forEach(function (df) {
			const doctype = is_link(df, "Branch") ? "Branch" : is_link(df, "Cost Center") ? "Cost Center" : null;
			if (!doctype) return;
			wrap_get_query(dialog.fields_dict[df.fieldname], doctype, function () {
				return dialog.get_value(company_df.fieldname) || "";
			});
		});
	}

	function apply_report_filters(report) {
		const filters = (report && report.report_settings && report.report_settings.filters) || [];
		const company_df = filters.find(is_company_link);
		if (!company_df) return;
		filters.forEach(function (df) {
			if (df.__logistics_company_dimension) return;
			const doctype = is_link(df, "Branch") ? "Branch" : is_link(df, "Cost Center") ? "Cost Center" : null;
			if (!doctype) return;
			const previous = df.get_query;
			df.get_query = function () {
				let company = "";
				try {
					company =
						(frappe.query_report &&
							frappe.query_report.get_filter_value &&
							frappe.query_report.get_filter_value(company_df.fieldname)) ||
						"";
				} catch (e) {
					company = "";
				}
				const base = typeof previous === "function" ? previous() || {} : {};
				return merge_query_filters(base, dimension_filters(doctype, company));
			};
			df.__logistics_company_dimension = true;
		});
	}

	function patch_query_report() {
		const query_report = frappe.views && frappe.views.QueryReport;
		if (!query_report || !query_report.prototype || query_report.prototype.__logistics_company_dimensions) {
			return;
		}
		const original = query_report.prototype.setup_filters;
		query_report.prototype.setup_filters = function () {
			try {
				apply_report_filters(this);
			} catch (e) {
				console.error("Company dimension report filters", e);
			}
			return original.apply(this, arguments);
		};
		query_report.prototype.__logistics_company_dimensions = true;
	}

	function patch_dialog() {
		if (!frappe.ui || !frappe.ui.Dialog || frappe.ui.Dialog.prototype.__logistics_company_dimensions) {
			return;
		}
		const original = frappe.ui.Dialog.prototype.show;
		frappe.ui.Dialog.prototype.show = function () {
			try {
				apply_dialog(this);
			} catch (e) {
				console.error("Company dimension dialog filters", e);
			}
			return original.apply(this, arguments);
		};
		frappe.ui.Dialog.prototype.__logistics_company_dimensions = true;
	}

	patch_query_report();
	patch_dialog();

	frappe.ui.form.on("*", {
		setup(frm) {
			try {
				apply(frm);
			} catch (e) {
				console.error("Company dimension filters", e);
			}
		},
		refresh(frm) {
			try {
				apply(frm);
			} catch (e) {
				console.error("Company dimension filters", e);
			}
		},
		company(frm, cdt) {
			if (cdt && cdt !== frm.doctype) {
				return;
			}
			try {
				apply(frm);
				clear_mismatched(frm);
			} catch (e) {
				console.error("Company dimension filters", e);
			}
		},
		custom_company(frm, cdt) {
			if (cdt && cdt !== frm.doctype) {
				return;
			}
			try {
				apply(frm);
				clear_mismatched(frm);
			} catch (e) {
				console.error("Company dimension filters", e);
			}
		},
	});
})();
