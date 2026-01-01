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
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
	},

	refresh: function(frm) {
		// Ensure transport_job_type is always set
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		// Update container fields visibility
		frm.events.toggle_container_fields(frm);
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		
		// Fetch and update missing data from Transport Leg
		frm.events.update_legs_missing_data(frm);
		
		// Add button to manually fetch missing leg data (works for submitted docs too)
		if (frm.doc.legs && frm.doc.legs.length > 0) {
			frm.add_custom_button(__('Fetch Missing Leg Data'), function() {
				frm.events.fetch_missing_leg_data_server(frm);
			}, __('Actions'));
		}
	},

	transport_job_type: function(frm) {
		// Update container fields visibility when transport_job_type changes
		frm.events.toggle_container_fields(frm);
	},

	consolidate: function(frm) {
		// Update vehicle_type required state when consolidate checkbox changes
		frm.events.toggle_vehicle_type_required(frm);
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

	toggle_vehicle_type_required: function(frm) {
		// Vehicle Type is mandatory only if Consolidate checkbox is not checked
		const is_required = !frm.doc.consolidate;
		frm.set_df_property('vehicle_type', 'reqd', is_required);
	},

	validate: function(frm) {
		// Ensure transport_job_type is set before save
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		if (!frm.doc.transport_job_type) {
			frappe.throw(__('Transport Job Type is required. Please select a Transport Job Type before saving.'));
		}
		
		// Validate vehicle_type is required only if consolidate is not checked
		if (!frm.doc.vehicle_type && !frm.doc.consolidate) {
			frappe.throw(__('Vehicle Type is required when Consolidate is not checked.'));
		}
		
		// Fetch and update missing data from Transport Leg before save
		frm.events.update_legs_missing_data(frm);
	},
	
	update_legs_missing_data: function(frm) {
		// Fetch and update missing data from Transport Leg for all legs
		// Only works for draft documents (docstatus = 0)
		if (frm.doc.docstatus !== 0) {
			return;
		}
		
		const legs = frm.doc.legs || [];
		
		legs.forEach((leg, idx) => {
			if (!leg.transport_leg) {
				// Skip if transport_leg is not set
				return;
			}
			
			// Check if any required fields are missing
			const required_fields = [
				'facility_type_from', 'facility_from', 'facility_type_to', 'facility_to',
				'pick_mode', 'drop_mode', 'pick_address', 'drop_address', 'run_sheet'
			];
			
			const has_missing = required_fields.some(field => !leg[field]);
			
			if (has_missing) {
				// Fetch data from Transport Leg and update missing fields
				frappe.model.get_value('Transport Leg', leg.transport_leg, 
					['facility_type_from', 'facility_from', 'facility_type_to', 'facility_to',
					 'pick_mode', 'drop_mode', 'pick_address', 'drop_address', 'run_sheet', 'date'],
					(r) => {
						if (r) {
							// Update only missing fields
							if (!leg.facility_type_from && r.facility_type_from) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_type_from', r.facility_type_from);
							}
							if (!leg.facility_from && r.facility_from) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_from', r.facility_from);
							}
							if (!leg.facility_type_to && r.facility_type_to) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_type_to', r.facility_type_to);
							}
							if (!leg.facility_to && r.facility_to) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_to', r.facility_to);
							}
							if (!leg.pick_mode && r.pick_mode) {
								frappe.model.set_value(leg.doctype, leg.name, 'pick_mode', r.pick_mode);
							}
							if (!leg.drop_mode && r.drop_mode) {
								frappe.model.set_value(leg.doctype, leg.name, 'drop_mode', r.drop_mode);
							}
							if (!leg.pick_address && r.pick_address) {
								frappe.model.set_value(leg.doctype, leg.name, 'pick_address', r.pick_address);
							}
							if (!leg.drop_address && r.drop_address) {
								frappe.model.set_value(leg.doctype, leg.name, 'drop_address', r.drop_address);
							}
							if (!leg.run_sheet && r.run_sheet) {
								frappe.model.set_value(leg.doctype, leg.name, 'run_sheet', r.run_sheet);
							}
							if (!leg.scheduled_date && r.date) {
								frappe.model.set_value(leg.doctype, leg.name, 'scheduled_date', r.date);
							}
						}
					}
				);
			}
		});
	},
	
	fetch_missing_leg_data_server: function(frm) {
		// Call server method to fetch missing data (works for submitted documents too)
		frappe.call({
			method: 'logistics.transport.doctype.transport_job.transport_job.fetch_missing_leg_data',
			args: {
				job_name: frm.doc.name
			},
			freeze: true,
			freeze_message: __('Fetching missing leg data...'),
			callback: function(r) {
				if (r.message) {
					if (r.message.updated_count > 0) {
						frappe.show_alert({
							message: __('Updated {0} leg(s) with missing data', [r.message.updated_count]),
							indicator: 'green'
						});
						frm.reload_doc();
					} else {
						frappe.show_alert({
							message: __('No missing data found in legs'),
							indicator: 'blue'
						});
					}
				}
			}
		});
	}
});

// Child table event handlers for Transport Job Legs
frappe.ui.form.on('Transport Job Legs', {
	transport_leg: function(frm, cdt, cdn) {
		// When transport_leg is selected, trigger a refresh to fetch data
		const row = locals[cdt][cdn];
		if (row.transport_leg) {
			frappe.model.set_value(cdt, cdn, 'transport_leg', row.transport_leg);
			frm.refresh_field('legs');
		}
	}
});
