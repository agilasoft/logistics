// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Handling Unit", {
	onload(frm) {
		_toggle_storage_location_size(frm);
	},
	
	refresh(frm) {
		_toggle_storage_location_size(frm);
	},
	
	company(frm) {
		_toggle_storage_location_size(frm);
	},
	
	type(frm) {
		// Also check when type changes since storage_location_size fetches from type
		_toggle_storage_location_size(frm);
	}
});

function _toggle_storage_location_size(frm) {
	// Disable storage_location_size field if location overflow is not enabled in warehouse settings
	if (!frm.doc.company) {
		// If no company is set, disable the field
		if (frm.fields_dict.storage_location_size) {
			frm.set_df_property("storage_location_size", "read_only", 1);
			console.log("Handling Unit: storage_location_size disabled - no company");
		}
		return;
	}
	
	// Use server method for more reliable checking
	frappe.call({
		method: "logistics.warehousing.doctype.handling_unit.handling_unit.is_location_overflow_enabled",
		args: {
			company: frm.doc.company
		},
		callback: function(r) {
			if (frm.fields_dict.storage_location_size) {
				if (r && r.message) {
					frm.set_df_property("storage_location_size", "read_only", 0);
					console.log("Handling Unit: storage_location_size enabled - location overflow is ON for company", frm.doc.company);
				} else {
					frm.set_df_property("storage_location_size", "read_only", 1);
					console.log("Handling Unit: storage_location_size disabled - location overflow is OFF for company", frm.doc.company);
				}
			} else {
				console.log("Handling Unit: storage_location_size field not found in form");
			}
		},
		error: function(r) {
			// On error, disable the field to be safe
			if (frm.fields_dict.storage_location_size) {
				frm.set_df_property("storage_location_size", "read_only", 1);
				console.log("Handling Unit: storage_location_size disabled - error checking warehouse settings", r);
			}
		}
	});
}
