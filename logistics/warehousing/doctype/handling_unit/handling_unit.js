// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Handling Unit", {
	refresh(frm) {
		_toggle_storage_location_size(frm);
	},
	
	company(frm) {
		_toggle_storage_location_size(frm);
	}
});

function _toggle_storage_location_size(frm) {
	// Disable storage_location_size field if location overflow is not enabled in warehouse settings
	if (frm.doc.company) {
		frappe.db.get_value("Warehouse Settings", frm.doc.company, "enable_location_overflow", (r) => {
			if (r && r.enable_location_overflow) {
				frm.set_df_property("storage_location_size", "read_only", 0);
			} else {
				frm.set_df_property("storage_location_size", "read_only", 1);
			}
		});
	} else {
		// If no company is set, disable the field
		frm.set_df_property("storage_location_size", "read_only", 1);
	}
}
