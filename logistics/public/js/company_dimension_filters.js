// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Company-scoped Branch and Cost Center on every form that has those fields.
 * Profit Center is intentionally not filtered by company.
 */
(function () {
	"use strict";

	if (window.__logistics_company_dimension_filters__) {
		return;
	}
	window.__logistics_company_dimension_filters__ = true;

	function linked_company_field(doctype) {
		if (frappe.meta.has_field(doctype, "company")) return "company";
		if (frappe.meta.has_field(doctype, "custom_company")) return "custom_company";
		if (doctype === "Branch") return "custom_company";
		if (doctype === "Cost Center") return "company";
		return null;
	}

	function dimension_query(doctype, get_company, extra_filters) {
		return function () {
			const filters = Object.assign({}, extra_filters || {});
			const company = (typeof get_company === "function" ? get_company() : get_company) || "";
			const company_field = linked_company_field(doctype);
			if (company && company_field) {
				filters[company_field] = company;
			}
			return { filters };
		};
	}

	function has_company_link(frm) {
		const df = frm.meta && frm.meta.fields && frm.meta.fields.find(function (field) {
			return field.fieldname === "company" && field.fieldtype === "Link" && field.options === "Company";
		});
		return !!df;
	}

	function is_link(df, options) {
		return !!(df && df.fieldtype === "Link" && df.options === options);
	}

	function apply_parent_queries(frm) {
		const company = function () {
			return frm.doc && frm.doc.company;
		};
		if (frm.fields_dict.branch && is_link(frm.fields_dict.branch.df, "Branch")) {
			frm.set_query("branch", dimension_query("Branch", company));
		}
		if (frm.fields_dict.cost_center && is_link(frm.fields_dict.cost_center.df, "Cost Center")) {
			frm.set_query(
				"cost_center",
				dimension_query("Cost Center", company, { is_group: 0, disabled: 0 })
			);
		}
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
		const child_has_company = (meta.fields || []).some(function (field) {
			return field.fieldname === "company" && field.fieldtype === "Link";
		});
		const branch_df = (meta.fields || []).find(function (field) {
			return field.fieldname === "branch" && is_link(field, "Branch");
		});
		const cost_center_df = (meta.fields || []).find(function (field) {
			return field.fieldname === "cost_center" && is_link(field, "Cost Center");
		});
		const company_of_row = function (doc, cdt, cdn) {
			const row = locals[cdt] && locals[cdt][cdn];
			if (child_has_company && row && row.company) {
				return row.company;
			}
			return doc && doc.company;
		};
		if (branch_df) {
			frm.set_query("branch", table_df.fieldname, function (doc, cdt, cdn) {
				return dimension_query("Branch", function () {
					return company_of_row(doc, cdt, cdn);
				})();
			});
		}
		if (cost_center_df) {
			frm.set_query("cost_center", table_df.fieldname, function (doc, cdt, cdn) {
				return dimension_query("Cost Center", function () {
					return company_of_row(doc, cdt, cdn);
				}, { is_group: 0, disabled: 0 })();
			});
		}
	}

	function apply(frm) {
		if (!frm || !frm.meta || !frm.doc || !has_company_link(frm)) {
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
		const company = frm.doc && frm.doc.company;
		if (!company || !has_company_link(frm)) {
			return;
		}
		[
			["branch", "Branch"],
			["cost_center", "Cost Center"],
		].forEach(function (pair) {
			const fieldname = pair[0];
			const doctype = pair[1];
			const df = frm.get_docfield ? frm.get_docfield(fieldname) : null;
			if (!df || df.read_only || !is_link(df, doctype)) {
				return;
			}
			const value = frm.doc[fieldname];
			if (!value) {
				return;
			}
			const company_field = linked_company_field(doctype);
			if (!company_field) {
				return;
			}
			frappe.db.get_value(doctype, value, company_field, function (r) {
				const linked_company = r && r[company_field];
				if (linked_company && linked_company !== company && frm.doc.company === company) {
					frm.set_value(fieldname, "");
				}
			});
		});
	}

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
	});
})();
