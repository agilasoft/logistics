// Copyright (c) 2026, Agilasoft and contributors
// Read-only virtual linked_services grid (operational bookings / shipments / jobs).

frappe.provide("logistics");

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

logistics.setup_virtual_linked_services_grid = function (frm) {
	logistics.set_virtual_linked_services_read_only(frm);
	setTimeout(function () {
		logistics.hide_virtual_linked_services_add_buttons(frm);
	}, 0);
};
