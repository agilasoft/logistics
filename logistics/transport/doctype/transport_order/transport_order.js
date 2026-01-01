frappe.ui.form.on("Transport Order", {
	onload: function(frm) {
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
	},

	refresh: function(frm) {
		// Clear scheduled_date if coming from Sales Quote creation
		if (frappe.route_options && frappe.route_options.__clear_scheduled_date) {
			frm.set_value('scheduled_date', '');
			// Clear the route option to avoid clearing on subsequent refreshes
			delete frappe.route_options.__clear_scheduled_date;
		}
		
		// Add Create Leg Plan button if transport template is set and document is not submitted
		if (!frm.is_new() && frm.doc.transport_template && frm.doc.docstatus !== 1) {
			frm.add_custom_button(__("Leg Plan"), function() {
				frappe.call({
					method: "logistics.transport.doctype.transport_order.transport_order.action_get_leg_plan",
					args: {
						docname: frm.doc.name,
						replace: 1,
						save: 1
					},
					freeze: true,
					freeze_message: __("Creating leg plan..."),
					callback: function(r) {
						if (r.message && r.message.ok) {
							frm.reload_doc();
						}
					}
				});
			}, __("Create"));
		}
		
		// Add Create Transport Job button if document is submitted
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Transport Job"), function() {
				frappe.call({
					method: "logistics.transport.doctype.transport_order.transport_order.action_create_transport_job",
					args: {
						docname: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Creating transport job..."),
					callback: function(r) {
						if (r.message) {
							if (r.message.already_exists) {
								frappe.msgprint(__("Transport Job {0} already exists for this Transport Order.", [r.message.name]));
								frappe.set_route("Form", "Transport Job", r.message.name);
							} else if (r.message.created) {
								frappe.msgprint(__("Transport Job {0} created successfully.", [r.message.name]));
								frappe.set_route("Form", "Transport Job", r.message.name);
							}
						}
					}
				});
			}, __("Create"));
		}
		
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		
		// Auto-populate vehicle_type and transport_job_type to legs on form load
		populate_legs_from_parent(frm);
	},
	
	vehicle_type: function(frm) {
		// Auto-populate vehicle_type to all legs that don't have it set
		populate_legs_from_parent(frm);
	},
	
	transport_job_type: function(frm) {
		// Auto-populate transport_job_type to all legs that don't have it set
		populate_legs_from_parent(frm);
	},

	consolidate: function(frm) {
		// Update vehicle_type required state when consolidate checkbox changes
		frm.events.toggle_vehicle_type_required(frm);
	},

	toggle_vehicle_type_required: function(frm) {
		// Vehicle Type is mandatory only if Consolidate checkbox is not checked
		const is_required = !frm.doc.consolidate;
		frm.set_df_property('vehicle_type', 'reqd', is_required);
	}
});

// Helper function to populate legs with parent values
function populate_legs_from_parent(frm) {
	if (!frm.doc.legs || frm.doc.legs.length === 0) {
		return;
	}
	
	var updated = false;
	frm.doc.legs.forEach(function(leg) {
		if (!leg.vehicle_type && frm.doc.vehicle_type) {
			frappe.model.set_value(leg.doctype, leg.name, 'vehicle_type', frm.doc.vehicle_type);
			updated = true;
		}
		if (!leg.transport_job_type && frm.doc.transport_job_type) {
			frappe.model.set_value(leg.doctype, leg.name, 'transport_job_type', frm.doc.transport_job_type);
			updated = true;
		}
	});
	
	if (updated) {
		frm.refresh_field('legs');
	}
}

// Child table events for Transport Order Legs
frappe.ui.form.on('Transport Order Legs', {
	legs_add: function(frm, cdt, cdn) {
		// When a new leg is added, auto-populate vehicle_type and transport_job_type from parent if not set
		if (frm.doc.vehicle_type) {
			frappe.model.set_value(cdt, cdn, 'vehicle_type', frm.doc.vehicle_type);
		}
		if (frm.doc.transport_job_type) {
			frappe.model.set_value(cdt, cdn, 'transport_job_type', frm.doc.transport_job_type);
		}
	}
});
