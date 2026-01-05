frappe.ui.form.on("Transport Order", {
	onload: function(frm) {
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		// Apply transport job type filters on load (preserve existing values for existing documents)
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm, !frm.is_new());
		}
	},

	refresh: function(frm) {
		// Clear scheduled_date if coming from Sales Quote creation
		if (frappe.route_options && frappe.route_options.__clear_scheduled_date) {
			frm.set_value('scheduled_date', '');
			// Clear the route option to avoid clearing on subsequent refreshes
			delete frappe.route_options.__clear_scheduled_date;
		}
		
		// Ensure submit button is available for saved documents (docstatus = 0)
		// Frappe should show submit button automatically, but we ensure form is ready
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			// Form is saved and in draft state - submit button should be visible
			// If it's not showing, it might be a permission or form state issue
			console.log("refresh: Document is saved and ready for submission", frm.doc.name);
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
		
		// Apply transport job type filters on refresh (preserve existing values)
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm, true);
		}
		
		// Reapply filters for all legs (only update filters, don't mutate data)
		if (frm.doc.legs && frm.doc.legs.length > 0) {
			frm.doc.legs.forEach(function(leg) {
				if (leg.transport_job_type) {
					apply_leg_vehicle_type_filters_only(frm, leg.doctype, leg.name);
				}
			});
		}
	},
	
	vehicle_type: function(frm) {
		// Validate vehicle type compatibility with transport job type
		// Only check refrigeration if checkbox is actually checked
		if (frm.doc.transport_job_type && frm.doc.vehicle_type) {
			// Pass undefined to let the function determine based on checkbox state
			frm.events.validate_vehicle_compatibility(frm, false, undefined);
		}
		// Auto-populate vehicle_type to all legs that don't have it set (only on user action)
		populate_legs_vehicle_type_from_parent(frm);
	},
	
	transport_job_type: function(frm) {
		// Apply filters and field visibility based on transport job type
		frm.events.apply_transport_job_type_filters(frm);
		// Auto-populate transport_job_type to all legs that don't have it set (only on user action)
		populate_legs_transport_job_type_from_parent(frm);
		// Clear vehicle_type if it's not compatible with new job type (don't check refrigeration when job type changes)
		if (frm.doc.vehicle_type) {
			frm.events.validate_vehicle_compatibility(frm, true, false);
		}
	},

	refrigeration: function(frm) {
		// Reapply filters when refrigeration checkbox changes (user action)
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm);
		}
		// Validate vehicle type if set (check refrigeration when refrigeration checkbox changes)
		if (frm.doc.vehicle_type) {
			frm.events.validate_vehicle_compatibility(frm, true, true);
		}
		// Reapply filters for all legs (user action - can clear vehicle_type if incompatible)
		if (frm.doc.legs && frm.doc.legs.length > 0) {
			frm.doc.legs.forEach(function(leg) {
				if (leg.transport_job_type) {
					// On user action, apply filters and potentially clear incompatible vehicle_type
					apply_leg_vehicle_type_filters(frm, leg.doctype, leg.name);
					if (leg.vehicle_type) {
						validate_leg_vehicle_compatibility(frm, leg.doctype, leg.name);
					}
				}
			});
		}
	},

	consolidate: function(frm) {
		// Update vehicle_type required state when consolidate checkbox changes
		frm.events.toggle_vehicle_type_required(frm);
	},

	toggle_vehicle_type_required: function(frm) {
		// Vehicle Type is mandatory only if Consolidate checkbox is not checked
		const is_required = !frm.doc.consolidate;
		frm.set_df_property('vehicle_type', 'reqd', is_required);
	},

	apply_transport_job_type_filters: function(frm, preserve_existing_value) {
		// Filter vehicle types based on transport job type, refrigeration, and classifications
		// preserve_existing_value: if true, don't clear vehicle_type even if not in filtered list (used during refresh)
		if (!frm.doc.transport_job_type) {
			// Clear filters if no job type selected
			frm.set_df_property('vehicle_type', 'filters', {});
			return;
		}

		// Build filters based on job type and refrigeration
		var filters = {};
		
		// Filter by containerized flag
		if (frm.doc.transport_job_type === "Container") {
			filters.containerized = 1;
		} else if (frm.doc.transport_job_type === "Non-Container") {
			filters.containerized = 0;
		}
		
		// Filter by classifications for Heavy Haul and Oversized
		if (frm.doc.transport_job_type === "Heavy Haul" || frm.doc.transport_job_type === "Oversized") {
			filters.classifications = ["in", ["Heavy", "Special"]];
		}
		
		// Filter for Special job type: requires both reefer=1 and classifications=Special
		if (frm.doc.transport_job_type === "Special") {
			filters.reefer = 1;
			filters.classifications = "Special";
		}
		
		// Filter by reefer if refrigeration is required (for other job types)
		if (frm.doc.refrigeration && frm.doc.transport_job_type !== "Special") {
			filters.reefer = 1;
		}

		frappe.call({
			method: "logistics.transport.doctype.transport_order.transport_order.get_allowed_vehicle_types",
			args: {
				transport_job_type: frm.doc.transport_job_type,
				refrigeration: frm.doc.refrigeration || false
			},
			callback: function(r) {
				if (r.message && r.message.vehicle_types) {
					const allowed_types = r.message.vehicle_types.map(vt => vt.name);
					
					// Apply filters to vehicle_type field
					frm.set_df_property('vehicle_type', 'filters', filters);
					
					// Only clear vehicle_type if current selection is not in allowed types
					// AND we're not preserving existing values (i.e., during refresh after save)
					if (!preserve_existing_value && frm.doc.vehicle_type && !allowed_types.includes(frm.doc.vehicle_type)) {
						frm.set_value('vehicle_type', '');
					}
					
					// Refresh the field to apply filters
					frm.refresh_field('vehicle_type');
				}
			}
		});

		// Show/hide and require container fields based on job type
		const is_container = frm.doc.transport_job_type === "Container";
		const is_non_container = frm.doc.transport_job_type === "Non-Container";
		
		// Container Type field - hidden for Non-Container and other non-container types
		frm.set_df_property('container_type', 'hidden', !is_container);
		frm.set_df_property('container_type', 'reqd', is_container);
		
		// Container No. field - hidden for Non-Container and other non-container types
		frm.set_df_property('container_no', 'hidden', !is_container);
		frm.set_df_property('container_no', 'reqd', is_container);
		
		// Clear container fields if not container job type
		if (!is_container) {
			if (frm.doc.container_type) {
				frm.set_value('container_type', '');
			}
			if (frm.doc.container_no) {
				frm.set_value('container_no', '');
			}
		}
		
		// Hide consolidate checkbox and force consolidate = 0 for Container job type
		frm.set_df_property('consolidate', 'hidden', is_container);
		if (is_container && frm.doc.consolidate) {
			frm.set_value('consolidate', 0);
		}
	},

	validate_vehicle_compatibility: function(frm, clear_if_incompatible, check_refrigeration) {
		if (!frm.doc.transport_job_type || !frm.doc.vehicle_type) {
			return;
		}

		// Only check refrigeration if:
		// 1. check_refrigeration parameter is not explicitly false, AND
		// 2. The refrigeration checkbox is actually checked (=== 1 or === true)
		// For Special job type, always check refrigeration (it's required)
		var should_check_refrigeration = false;
		if (frm.doc.transport_job_type === "Special") {
			should_check_refrigeration = true;
		} else if (check_refrigeration !== false) {
			// Explicitly check if refrigeration is 1 or true (not just truthy)
			if (frm.doc.refrigeration === 1 || frm.doc.refrigeration === true) {
				should_check_refrigeration = true;
			}
		}

		frappe.call({
			method: "logistics.transport.doctype.transport_order.transport_order.validate_vehicle_job_type_compatibility",
			args: {
				transport_job_type: frm.doc.transport_job_type,
				vehicle_type: frm.doc.vehicle_type,
				refrigeration: should_check_refrigeration
			},
			callback: function(r) {
				if (r.message && !r.message.compatible) {
					if (clear_if_incompatible) {
						frm.set_value('vehicle_type', '');
						frappe.msgprint({
							title: __("Incompatible Vehicle Type"),
							message: r.message.message,
							indicator: 'orange'
						});
					} else {
						frappe.msgprint({
							title: __("Incompatible Vehicle Type"),
							message: r.message.message,
							indicator: 'orange'
						});
					}
				}
			}
		});
	},

	before_save: function(frm) {
		// Allow save without blocking - validation will happen on submit
		// This ensures the submit button appears after saving
		return Promise.resolve();
	},
	
	on_save: function(frm) {
		// After save, ensure form is in correct state for submission
		// The submit button should appear automatically when docstatus = 0
		// Don't refresh here - it can cause issues with submit button visibility
		console.log("on_save: Document saved", frm.doc.name, "docstatus:", frm.doc.docstatus);
	},
	
	before_submit: function(frm) {
		// Validate vehicle type compatibility before submitting
		// This validation only runs on submit, not on save
		// Note: Server-side validation in Python will also check for required leg fields
		console.log("before_submit: Starting validation for Transport Order", frm.doc.name);
		return new Promise(function(resolve, reject) {
			var validation_promises = [];
			var timeout_id;
			var is_resolved = false;
			
			// Helper function to safely resolve/reject
			function safe_resolve() {
				if (!is_resolved) {
					is_resolved = true;
					if (timeout_id) clearTimeout(timeout_id);
					resolve();
				}
			}
			
			function safe_reject(error) {
				if (!is_resolved) {
					is_resolved = true;
					if (timeout_id) clearTimeout(timeout_id);
					frappe.msgprint({
						title: __("Validation Error"),
						message: error,
						indicator: 'red'
					});
					reject(error);
				}
			}
			
			// Set a timeout to prevent hanging (10 seconds)
			timeout_id = setTimeout(function() {
				safe_reject(__("Validation timed out. Please try again."));
			}, 10000);
			
			// Validate main form vehicle type (only if not consolidating)
			// If consolidate is checked, vehicle_type is optional at parent level
			if (!frm.doc.consolidate && frm.doc.transport_job_type && frm.doc.vehicle_type) {
				validation_promises.push(
					new Promise(function(res, rej) {
						// For Special job type, always check refrigeration (it's required)
						// For other job types, only check if refrigeration checkbox is explicitly checked (=== 1 or === true)
						var check_refrigeration = false;
						if (frm.doc.transport_job_type === "Special") {
							check_refrigeration = true;
						} else if (frm.doc.refrigeration === 1 || frm.doc.refrigeration === true) {
							check_refrigeration = true;
						}
						
						var call_timeout = setTimeout(function() {
							rej(__("Validation request timed out"));
						}, 8000);
						
						frappe.call({
							method: "logistics.transport.doctype.transport_order.transport_order.validate_vehicle_job_type_compatibility",
							args: {
								transport_job_type: frm.doc.transport_job_type,
								vehicle_type: frm.doc.vehicle_type,
								refrigeration: check_refrigeration
							},
							callback: function(r) {
								clearTimeout(call_timeout);
								if (r.exc) {
									rej(__("Error validating vehicle type compatibility"));
								} else if (r.message && !r.message.compatible) {
									rej(r.message.message);
								} else {
									res();
								}
							},
							error: function(r) {
								clearTimeout(call_timeout);
								rej(__("Error validating vehicle type compatibility"));
							}
						});
					})
				);
			}
			
			// Validate legs - each leg must have vehicle_type and transport_job_type if they are set
			if (frm.doc.legs && frm.doc.legs.length > 0) {
				frm.doc.legs.forEach(function(leg) {
					// Only validate if both transport_job_type and vehicle_type are set
					// Server-side validation will catch missing required fields
					if (leg.transport_job_type && leg.vehicle_type) {
						validation_promises.push(
							new Promise(function(res, rej) {
								// For Special job type, always check refrigeration (it's required)
								// For other job types, only check if refrigeration checkbox is explicitly checked (=== 1 or === true)
								var check_refrigeration = false;
								if (leg.transport_job_type === "Special") {
									check_refrigeration = true;
								} else if (frm.doc.refrigeration === 1 || frm.doc.refrigeration === true) {
									check_refrigeration = true;
								}
								
								var call_timeout = setTimeout(function() {
									rej(__("Leg {0}: Validation request timed out", [leg.idx || '']));
								}, 8000);
								
								frappe.call({
									method: "logistics.transport.doctype.transport_order.transport_order.validate_vehicle_job_type_compatibility",
									args: {
										transport_job_type: leg.transport_job_type,
										vehicle_type: leg.vehicle_type,
										refrigeration: check_refrigeration
									},
									callback: function(r) {
										clearTimeout(call_timeout);
										if (r.exc) {
											rej(__("Leg {0}: Error validating vehicle type compatibility", [leg.idx || '']));
										} else if (r.message && !r.message.compatible) {
											rej(__("Leg {0}: {1}", [leg.idx || '', r.message.message]));
										} else {
											res();
										}
									},
									error: function(r) {
										clearTimeout(call_timeout);
										rej(__("Leg {0}: Error validating vehicle type compatibility", [leg.idx || '']));
									}
								});
							})
						);
					}
				});
			}
			
			// If no validations needed, resolve immediately
			// This allows submission even if vehicle types are not set (server will validate required fields)
			if (validation_promises.length === 0) {
				console.log("before_submit: No validations needed, resolving immediately");
				safe_resolve();
				return;
			}
			
			console.log("before_submit: Validating", validation_promises.length, "vehicle type(s)");
			
			// Wait for all validations
			Promise.all(validation_promises).then(function() {
				console.log("before_submit: All validations passed");
				safe_resolve();
			}).catch(function(error) {
				console.error("before_submit: Validation failed", error);
				safe_reject(error);
			});
		});
	}
});

// Helper function to populate vehicle_type in legs from parent (only on user action)
// Only sets value if it actually changes
function populate_legs_vehicle_type_from_parent(frm) {
	if (!frm.doc.legs || frm.doc.legs.length === 0 || !frm.doc.vehicle_type) {
		return;
	}
	
	var updated = false;
	frm.doc.legs.forEach(function(leg) {
		// Only set if leg doesn't have vehicle_type and parent has one
		// Guard: only set if value actually changes
		if (!leg.vehicle_type && frm.doc.vehicle_type) {
			frappe.model.set_value(leg.doctype, leg.name, 'vehicle_type', frm.doc.vehicle_type);
			updated = true;
		}
	});
	
	if (updated) {
		frm.refresh_field('legs');
	}
}

// Helper function to populate transport_job_type in legs from parent (only on user action)
// Only sets value if it actually changes
function populate_legs_transport_job_type_from_parent(frm) {
	if (!frm.doc.legs || frm.doc.legs.length === 0 || !frm.doc.transport_job_type) {
		return;
	}
	
	var updated = false;
	frm.doc.legs.forEach(function(leg) {
		// Only set if leg doesn't have transport_job_type and parent has one
		// Guard: only set if value actually changes
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
		// Guard: only set if value actually changes
		var leg = frappe.get_doc(cdt, cdn);
		if (frm.doc.vehicle_type && !leg.vehicle_type) {
			frappe.model.set_value(cdt, cdn, 'vehicle_type', frm.doc.vehicle_type);
		}
		if (frm.doc.transport_job_type && !leg.transport_job_type) {
			frappe.model.set_value(cdt, cdn, 'transport_job_type', frm.doc.transport_job_type);
		}
		// Apply filters for the leg's vehicle_type field
		apply_leg_vehicle_type_filters(frm, cdt, cdn);
	},

	transport_job_type: function(frm, cdt, cdn) {
		// Apply filters when transport_job_type changes in a leg
		apply_leg_vehicle_type_filters(frm, cdt, cdn);
		// Validate vehicle type if set
		var leg = frappe.get_doc(cdt, cdn);
		if (leg.vehicle_type) {
			validate_leg_vehicle_compatibility(frm, cdt, cdn);
		}
	},

	vehicle_type: function(frm, cdt, cdn) {
		// Validate vehicle type compatibility when changed in a leg
		validate_leg_vehicle_compatibility(frm, cdt, cdn);
	}
});

// Helper function to apply vehicle type filters for legs (used when user changes transport_job_type)
// This version clears vehicle_type if filters change (only on user action)
function apply_leg_vehicle_type_filters(frm, cdt, cdn) {
	var leg = frappe.get_doc(cdt, cdn);
	if (!leg.transport_job_type) {
		return;
	}

	// Build filters based on job type and parent refrigeration
	var filters = {};
	
	// Filter by containerized flag
	if (leg.transport_job_type === "Container") {
		filters.containerized = 1;
	} else if (leg.transport_job_type === "Non-Container") {
		filters.containerized = 0;
	}
	
	// Filter by classifications for Heavy Haul and Oversized
	if (leg.transport_job_type === "Heavy Haul" || leg.transport_job_type === "Oversized") {
		filters.classifications = ["in", ["Heavy", "Special"]];
	}
	
	// Filter for Special job type: requires both reefer=1 and classifications=Special
	if (leg.transport_job_type === "Special") {
		filters.reefer = 1;
		filters.classifications = "Special";
	}
	
	// Filter by reefer if parent refrigeration is required (for other job types)
	if (frm.doc.refrigeration && leg.transport_job_type !== "Special") {
		filters.reefer = 1;
	}

	// Guard: Only clear vehicle_type if it is non-empty (prevent clearing empty values)
	if (leg.vehicle_type) {
		frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
	}
	
	// Apply filters to vehicle_type field in the leg
	frm.fields_dict.legs.grid.update_docfield_property(
		'vehicle_type',
		'filters',
		filters
	);
	
	frm.refresh_field('legs');
}

// Helper function to apply vehicle type filters for legs (used during refresh - no data mutation)
// This version only updates filters, doesn't clear vehicle_type
function apply_leg_vehicle_type_filters_only(frm, cdt, cdn) {
	var leg = frappe.get_doc(cdt, cdn);
	if (!leg.transport_job_type) {
		return;
	}

	// Build filters based on job type and parent refrigeration
	var filters = {};
	
	// Filter by containerized flag
	if (leg.transport_job_type === "Container") {
		filters.containerized = 1;
	} else if (leg.transport_job_type === "Non-Container") {
		filters.containerized = 0;
	}
	
	// Filter by classifications for Heavy Haul and Oversized
	if (leg.transport_job_type === "Heavy Haul" || leg.transport_job_type === "Oversized") {
		filters.classifications = ["in", ["Heavy", "Special"]];
	}
	
	// Filter for Special job type: requires both reefer=1 and classifications=Special
	if (leg.transport_job_type === "Special") {
		filters.reefer = 1;
		filters.classifications = "Special";
	}
	
	// Filter by reefer if parent refrigeration is required (for other job types)
	if (frm.doc.refrigeration && leg.transport_job_type !== "Special") {
		filters.reefer = 1;
	}
	
	// Apply filters to vehicle_type field in the leg (no data mutation)
	frm.fields_dict.legs.grid.update_docfield_property(
		'vehicle_type',
		'filters',
		filters
	);
}

// Helper function to validate vehicle compatibility for legs
function validate_leg_vehicle_compatibility(frm, cdt, cdn) {
	var leg = frappe.get_doc(cdt, cdn);
	if (!leg.transport_job_type || !leg.vehicle_type) {
		return;
	}

	// For Special job type, always check refrigeration (it's required)
	// For other job types, only check if refrigeration checkbox is explicitly checked (=== 1 or === true)
	var check_refrigeration = false;
	if (leg.transport_job_type === "Special") {
		check_refrigeration = true;
	} else if (frm.doc.refrigeration === 1 || frm.doc.refrigeration === true) {
		check_refrigeration = true;
	}

	frappe.call({
		method: "logistics.transport.doctype.transport_order.transport_order.validate_vehicle_job_type_compatibility",
		args: {
			transport_job_type: leg.transport_job_type,
			vehicle_type: leg.vehicle_type,
			refrigeration: check_refrigeration
		},
		callback: function(r) {
			if (r.message && !r.message.compatible) {
				frappe.msgprint({
					title: __("Incompatible Vehicle Type"),
					message: __("Leg {0}: {1}", [leg.idx || '', r.message.message]),
					indicator: 'orange'
				});
				// Guard: Only clear the incompatible vehicle type if it's non-empty
				var leg = frappe.get_doc(cdt, cdn);
				if (leg.vehicle_type) {
					frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
				}
			}
		}
	});
}

