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
				if (r && r.message === true) {
					// Enable the field - remove fetch_from behavior and make it editable
					setTimeout(function() {
						let field = frm.fields_dict.storage_location_size;
						
						// Remove fetch_from to allow manual editing
						frm.set_df_property("storage_location_size", "fetch_from", "");
						
						// Set read_only to false
						frm.set_df_property("storage_location_size", "read_only", 0);
						
						// Also try to enable the input directly
						if (field) {
							if (field.$input) {
								field.$input.prop("readonly", false);
								field.$input.prop("disabled", false);
								field.$input.removeClass("read-only");
								field.$input.removeAttr("readonly");
							}
							// Remove any read-only classes from the wrapper
							if (field.$wrapper) {
								field.$wrapper.find("input").prop("readonly", false).prop("disabled", false).removeAttr("readonly");
							}
						}
					}, 100);
				} else {
					// Restore fetch_from when location overflow is disabled
					frm.set_df_property("storage_location_size", "fetch_from", "type.storage_location_size");
					frm.set_df_property("storage_location_size", "read_only", 1);
				}
			}
		},
		error: function(r) {
			// On error, disable the field to be safe
			if (frm.fields_dict.storage_location_size) {
				frm.set_df_property("storage_location_size", "read_only", 1);
			}
		}
	});
}
