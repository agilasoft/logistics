// Copyright (c) 2020, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Type', {
	refresh: function(frm) {
		// Show compatibility information based on current field values
		frm.events.show_compatibility_info(frm);
	},

	classifications: function(frm) {
		// Validate and warn about Special classification requirements
		if (frm.doc.classifications === "Special") {
			if (!frm.doc.reefer) {
				frappe.msgprint({
					title: __("Special Classification Warning"),
					message: __("Vehicle Type with 'Special' classification should have 'Reefer' enabled to be compatible with 'Special' transport job type."),
					indicator: 'orange'
				});
			}
		}
		// Show updated compatibility info
		frm.events.show_compatibility_info(frm);
	},

	containerized: function(frm) {
		// Show updated compatibility info when containerized changes
		frm.events.show_compatibility_info(frm);
	},

	reefer: function(frm) {
		// Validate Special classification with reefer
		if (frm.doc.classifications === "Special" && !frm.doc.reefer) {
			frappe.msgprint({
				title: __("Special Classification Warning"),
				message: __("Vehicle Type with 'Special' classification should have 'Reefer' enabled to be compatible with 'Special' transport job type."),
				indicator: 'orange'
			});
		}
		// Show updated compatibility info
		frm.events.show_compatibility_info(frm);
	},

	show_compatibility_info: function(frm) {
		// Show which transport job types this vehicle type is compatible with
		// This is informational and helps users understand the implications of their choices
		var compatible_job_types = [];
		var warnings = [];

		// Container job type compatibility
		if (frm.doc.containerized) {
			compatible_job_types.push("Container");
		} else {
			compatible_job_types.push("Non-Container");
		}

		// Heavy Haul and Oversized compatibility
		if (frm.doc.classifications === "Heavy" || frm.doc.classifications === "Special") {
			compatible_job_types.push("Heavy Haul", "Oversized");
		}

		// Special job type compatibility (requires both reefer=1 and classifications=Special)
		if (frm.doc.classifications === "Special" && frm.doc.reefer) {
			compatible_job_types.push("Special");
		} else if (frm.doc.classifications === "Special" && !frm.doc.reefer) {
			warnings.push(__("Enable 'Reefer' to make this vehicle type compatible with 'Special' transport job type."));
		}

		// Refrigeration compatibility (for other job types)
		if (frm.doc.reefer) {
			// Vehicle can handle refrigeration requirements for other job types
			// (Special is already handled above)
		} else if (frm.doc.classifications === "Special") {
			// Already warned above
		}

		// Store compatibility info in a custom field or show in console for debugging
		// Note: This is informational - actual filtering happens in transport_order.js
		if (compatible_job_types.length > 0 || warnings.length > 0) {
			// You could add a custom HTML field or info box here to display this
			// For now, we'll just validate the data
		}
	},

	validate: function(frm) {
		// Client-side validation before save
		var errors = [];

		// Special classification must have reefer enabled for Special job type compatibility
		if (frm.doc.classifications === "Special" && !frm.doc.reefer) {
			errors.push(__("Vehicle Type with 'Special' classification should have 'Reefer' enabled to be compatible with 'Special' transport job type."));
		}

		// Note: We use 'should' not 'must' because the validation in transport_order.js
		// will handle the actual compatibility checks when selecting vehicle types.
		// This is just a helpful warning to guide users.

		if (errors.length > 0) {
			frappe.msgprint({
				title: __("Validation Warning"),
				message: errors.join("<br>"),
				indicator: 'orange'
			});
		}
	}
});
