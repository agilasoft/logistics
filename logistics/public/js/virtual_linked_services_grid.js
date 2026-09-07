// Copyright (c) 2026, Agilasoft and contributors
// Read-only virtual linked_services grid (operational bookings / shipments / jobs).

frappe.provide("logistics");

/** Canvas columns on Linked Service Detail, except Sales Quote (identity only). */
logistics.SALES_QUOTE_LINKED_SERVICES_HIDE_COLUMNS = [
	"job_type",
	"order_no",
	"job_no",
	"job_description",
];

logistics.set_virtual_linked_services_read_only = function (frm) {
	if (!frm || !frm.get_docfield || !frm.get_docfield("linked_services")) {
		return;
	}
	frm.set_df_property("linked_services", "cannot_add_rows", 1);
	frm.set_df_property("linked_services", "read_only", 1);
};

logistics.hide_virtual_linked_services_add_buttons = function (frm) {
	if (window.logistics_hide_cannot_add_rows_buttons) {
		window.logistics_hide_cannot_add_rows_buttons(frm, "linked_services");
	}
};

logistics._linked_services_grid_fieldname = function (frm) {
	if (!frm || !frm.fields_dict) {
		return null;
	}
	if (frm.fields_dict.linked_services) {
		return "linked_services";
	}
	if (frm.fields_dict.internal_job_details) {
		return "internal_job_details";
	}
	return null;
};

logistics.apply_sales_quote_linked_services_columns = function (frm) {
	if (!frm || frm.doctype !== "Sales Quote") {
		return;
	}
	const fieldname = logistics._linked_services_grid_fieldname(frm);
	if (!fieldname) {
		return;
	}
	const field = frm.get_field(fieldname);
	const grid = field && field.grid;
	if (!grid) {
		return;
	}
	const hide = logistics.SALES_QUOTE_LINKED_SERVICES_HIDE_COLUMNS;
	if (typeof grid.set_column_disp_in_list_view === "function") {
		grid.set_column_disp_in_list_view(hide, false);
		return;
	}
	if (typeof grid.update_docfield_property !== "function") {
		return;
	}
	hide.forEach(function (fn) {
		try {
			grid.update_docfield_property(fn, "in_list_view", 0);
		} catch (e) {
			// Field missing on older meta.
		}
	});
};

logistics.setup_virtual_linked_services_grid = function (frm) {
	logistics.set_virtual_linked_services_read_only(frm);
	logistics.apply_sales_quote_linked_services_columns(frm);
	setTimeout(function () {
		logistics.hide_virtual_linked_services_add_buttons(frm);
		logistics.apply_sales_quote_linked_services_columns(frm);
	}, 0);
};
