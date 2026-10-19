// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Permission Studio's Applicable For field passes the permission DocType
// (Company) as the link target. The search then looks for a Company record
// named "Company" and clears whatever was typed. Keep the link on DocType and
// ask for document types that include Company itself.

frappe.provide("logistics.applicable_for");

logistics.applicable_for.FRAPPE_QUERY =
	"frappe.core.doctype.user_permission.user_permission.get_applicable_for_doctype_list";
logistics.applicable_for.QUERY = "logistics.utils.applicable_for_query.applicable_for_query";

logistics.applicable_for.repair_search_args = function (args, field) {
	if (!args || !field || field.fieldname !== "applicable_for") {
		return args;
	}
	if (args.query !== logistics.applicable_for.FRAPPE_QUERY) {
		return args;
	}
	const link_doctype = field.options || "DocType";
	if (!args.doctype || args.doctype === link_doctype) {
		return args;
	}
	const reference = args.doctype;
	args.doctype = link_doctype;
	args.query = logistics.applicable_for.QUERY;
	const filters = args.filters && typeof args.filters === "object" ? args.filters : {};
	args.filters = Object.assign({}, filters, { doctype: reference });
	return args;
};

(function () {
	const control = frappe.ui.form.ControlLink && frappe.ui.form.ControlLink.prototype;
	if (!control || control.__logistics_applicable_for) {
		return;
	}
	if (control.get_search_args) {
		const original = control.get_search_args;
		control.get_search_args = function (txt) {
			return logistics.applicable_for.repair_search_args(original.call(this, txt), this.df);
		};
	} else if (control.set_custom_query) {
		const original_query = control.set_custom_query;
		control.set_custom_query = function (args) {
			original_query.call(this, args);
			logistics.applicable_for.repair_search_args(args, this.df);
		};
	}
	control.__logistics_applicable_for = true;
})();
