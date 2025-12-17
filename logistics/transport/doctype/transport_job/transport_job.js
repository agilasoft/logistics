// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Job', {
	setup: function(frm) {
		// Set default transport_job_type for new documents immediately
		// This must happen in setup (before onload) to prevent validation errors
		if (frm.is_new() && !frm.doc.transport_job_type) {
			frm.doc.transport_job_type = 'Non-Container';
		}
	},

	onload: function(frm) {
		// Ensure transport_job_type is always set
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		// Update container fields visibility
		frm.events.toggle_container_fields(frm);
	},

	refresh: function(frm) {
		// Ensure transport_job_type is always set
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		// Update container fields visibility
		frm.events.toggle_container_fields(frm);
	},

	transport_job_type: function(frm) {
		// Update container fields visibility when transport_job_type changes
		frm.events.toggle_container_fields(frm);
	},

	toggle_container_fields: function(frm) {
		// Show/hide container fields based on transport_job_type
		const is_container = frm.doc.transport_job_type === 'Container';
		
		frm.set_df_property('container_type', 'hidden', !is_container);
		frm.set_df_property('container_no', 'hidden', !is_container);
		
		// Clear container fields if not Container
		if (!is_container) {
			if (frm.doc.container_type) {
				frm.set_value('container_type', null);
			}
			if (frm.doc.container_no) {
				frm.set_value('container_no', null);
			}
		}
	},

	validate: function(frm) {
		// Ensure transport_job_type is set before save
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		if (!frm.doc.transport_job_type) {
			frappe.throw(__('Transport Job Type is required. Please select a Transport Job Type before saving.'));
		}
	}
});
