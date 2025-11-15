// Copyright (c) 2025, Logistics Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Air Freight Settings', {
	refresh: function(frm) {
		// Set company default if not set
		if (!frm.doc.company) {
			frm.set_value('company', frappe.defaults.get_user_default("Company"));
		}
		
		// Add custom buttons or actions if needed
	},
	
	company: function(frm) {
		// Validate company is set
		if (!frm.doc.company) {
			frappe.msgprint(__("Company is required"));
			frm.set_value('company', frappe.defaults.get_user_default("Company"));
		}
	},
	
	volume_to_weight_factor: function(frm) {
		// Validate volume to weight factor
		if (frm.doc.volume_to_weight_factor && frm.doc.volume_to_weight_factor <= 0) {
			frappe.msgprint(__("Volume to Weight Factor must be greater than 0"));
			frm.set_value('volume_to_weight_factor', 167); // IATA standard
		}
	},
	
	max_consolidation_weight: function(frm) {
		// Validate max consolidation weight
		if (frm.doc.max_consolidation_weight && frm.doc.max_consolidation_weight <= 0) {
			frappe.msgprint(__("Max Consolidation Weight must be greater than 0"));
			frm.set_value('max_consolidation_weight', null);
		}
	},
	
	max_consolidation_volume: function(frm) {
		// Validate max consolidation volume
		if (frm.doc.max_consolidation_volume && frm.doc.max_consolidation_volume <= 0) {
			frappe.msgprint(__("Max Consolidation Volume must be greater than 0"));
			frm.set_value('max_consolidation_volume', null);
		}
	},
	
	alert_check_interval_hours: function(frm) {
		// Validate alert check interval
		if (frm.doc.alert_check_interval_hours && frm.doc.alert_check_interval_hours <= 0) {
			frappe.msgprint(__("Alert Check Interval must be greater than 0"));
			frm.set_value('alert_check_interval_hours', 1);
		}
	},
	
	billing_check_interval_hours: function(frm) {
		// Validate billing check interval
		if (frm.doc.billing_check_interval_hours && frm.doc.billing_check_interval_hours <= 0) {
			frappe.msgprint(__("Billing Check Interval must be greater than 0"));
			frm.set_value('billing_check_interval_hours', 24);
		}
	}
});






