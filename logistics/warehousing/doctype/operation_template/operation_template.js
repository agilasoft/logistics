// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operation Template', {
	refresh: function(frm) {
		// Add custom buttons
		if (frm.is_new()) {
			frm.add_custom_button(__('Create Default Templates'), function() {
				create_default_templates(frm);
			}, __('Actions'));
		}
		
		// Add button to create default templates for all job types
		frm.add_custom_button(__('Create All Defaults'), function() {
			create_all_default_templates(frm);
		}, __('Actions'));
	},
	
	job_type: function(frm) {
		// Auto-set sequence if not set
		if (!frm.doc.sequence && frm.doc.job_type) {
			frm.set_value('sequence', 1);
		}
	},
	
	sequence: function(frm) {
		// Validate sequence
		if (frm.doc.sequence && frm.doc.sequence < 1) {
			frappe.msgprint({
				title: __('Invalid Sequence'),
				message: __('Sequence must be greater than 0'),
				indicator: 'red'
			});
			frm.set_value('sequence', 1);
		}
	},
	
	estimated_hours: function(frm) {
		// Validate estimated hours
		if (frm.doc.estimated_hours && frm.doc.estimated_hours < 0) {
			frappe.msgprint({
				title: __('Invalid Hours'),
				message: __('Estimated hours cannot be negative'),
				indicator: 'red'
			});
			frm.set_value('estimated_hours', 0);
		}
	}
});

function create_default_templates(frm) {
	frappe.confirm(
		__('This will create default operation templates for the selected job type. Continue?'),
		function() {
			frappe.call({
				method: 'logistics.warehousing.doctype.operation_template.operation_template.create_default_templates',
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __('✅ Default Templates Created'),
							message: __(r.message.message),
							indicator: 'green'
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __('❌ Error'),
							message: __('Failed to create default templates'),
							indicator: 'red'
						});
					}
				}
			});
		}
	);
}

function create_all_default_templates(frm) {
	frappe.confirm(
		__('This will create default operation templates for all job types. Continue?'),
		function() {
			frappe.call({
				method: 'logistics.warehousing.doctype.operation_template.operation_template.create_default_templates',
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __('✅ All Default Templates Created'),
							message: __(r.message.message),
							indicator: 'green'
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __('❌ Error'),
							message: __('Failed to create default templates'),
							indicator: 'red'
						});
					}
				}
			});
		}
	);
}
