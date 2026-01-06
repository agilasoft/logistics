// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Helper function to apply load_type filters (same pattern as vehicle_type)
function apply_load_type_filters(frm, preserve_existing_value) {
	// Filter load types based on transport job type and boolean columns
	// preserve_existing_value: if true, don't clear load_type even if not in filtered list (used during refresh)
	if (!frm.doc.transport_job_type) {
		// Clear filters if no job type selected
		frm.set_df_property('load_type', 'filters', {});
		return;
	}

	// Build filters based on job type
	var filters = {
		transport: 1
	};
	
	// Map transport_job_type to Load Type boolean field
	if (frm.doc.transport_job_type === "Container") {
		filters.container = 1;
	} else if (frm.doc.transport_job_type === "Non-Container") {
		filters.non_container = 1;
	} else if (frm.doc.transport_job_type === "Special") {
		filters.special = 1;
	} else if (frm.doc.transport_job_type === "Oversized") {
		filters.oversized = 1;
	} else if (frm.doc.transport_job_type === "Heavy Haul") {
		filters.heavy_haul = 1;
	} else if (frm.doc.transport_job_type === "Multimodal") {
		filters.multimodal = 1;
	}

	// Apply filters to load_type field
	frm.set_df_property('load_type', 'filters', filters);
	
	// Only clear load_type if current selection is not in filtered list
	// AND we're not preserving existing values (i.e., during refresh after save)
	if (!preserve_existing_value && frm.doc.load_type) {
		// Validate if current load_type is still allowed
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Load Type",
				name: frm.doc.load_type
			},
			callback: function(r) {
				if (r.message) {
					const load_type_doc = r.message;
					const field_map = {
						"Container": "container",
						"Non-Container": "non_container",
						"Special": "special",
						"Oversized": "oversized",
						"Multimodal": "multimodal",
						"Heavy Haul": "heavy_haul"
					};
					const allowed_field = field_map[frm.doc.transport_job_type];
					if (allowed_field && !load_type_doc[allowed_field]) {
						frm.set_value('load_type', '');
					}
				}
			}
		});
	}
	
	// Refresh the field to apply filters
	frm.refresh_field('load_type');
}

frappe.ui.form.on('Transport Job', {
	setup: function(frm) {
		// Set default transport_job_type for new documents immediately
		// This must happen in setup (before onload) to prevent validation errors
		if (frm.is_new() && !frm.doc.transport_job_type) {
			frm.doc.transport_job_type = 'Non-Container';
		}
		// Apply load_type filters before field is ever used
		apply_load_type_filters(frm);
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
		// Apply load_type filters on load (preserve existing values for existing documents)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, !frm.is_new());
		}
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
		// Apply load_type filters on refresh (preserve existing values)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, true);
		}
		
		// Fetch and update missing data from Transport Leg
		frm.events.update_legs_missing_data(frm);
		
		// Add button to manually fetch missing leg data (works for submitted docs too)
		if (frm.doc.legs && frm.doc.legs.length > 0) {
			frm.add_custom_button(__('Fetch Missing Leg Data'), function() {
				frm.events.fetch_missing_leg_data_server(frm);
			}, __('Actions'));
		}
		
		// Lalamove Integration
		if (frm.doc.use_lalamove && !frm.is_new()) {
			frm.add_custom_button(__('Lalamove'), function() {
				// Load Lalamove utilities if not already loaded
				if (typeof logistics === 'undefined' || !logistics.lalamove) {
					frappe.require('/assets/logistics/lalamove/utils.js', function() {
						frappe.require('/assets/logistics/lalamove/lalamove_form.js', function() {
							logistics.lalamove.form.showLalamoveDialog(frm);
						});
					});
				} else {
					logistics.lalamove.form.showLalamoveDialog(frm);
				}
			}, __('Actions'));
			
			// Show order status indicator if order exists
			if (frm.doc.lalamove_order) {
				frappe.db.get_value('Lalamove Order', frm.doc.lalamove_order, ['status', 'lalamove_order_id'], (r) => {
					if (r && r.status) {
						const status_color = r.status === 'COMPLETED' ? 'green' : (r.status === 'CANCELLED' ? 'red' : 'blue');
						frm.dashboard.add_indicator(__('Lalamove: {0}', [r.status]), status_color);
					}
				});
			}
		}
	},

	transport_job_type: function(frm) {
		// Update container fields visibility when transport_job_type changes
		frm.events.toggle_container_fields(frm);
		// Apply load_type filters (same pattern as vehicle_type)
		apply_load_type_filters(frm);
		// Clear invalid value when job type changes
		frm.set_value('load_type', null);
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
