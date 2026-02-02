// Helper function to load allowed vehicle types for a load_type and cache them
function load_allowed_vehicle_types(frm, load_type, callback) {
	// Load allowed vehicle types for the given load_type and cache them
	if (!load_type) {
		if (callback) callback();
		return;
	}
	
	// Check cache first
	if (frm.allowed_vehicle_types_cache[load_type]) {
		if (callback) callback();
		return;
	}
	
	// Load from server
	frappe.call({
		method: "logistics.transport.doctype.transport_order.transport_order.get_vehicle_types_for_load_type",
		args: {
			load_type: load_type
		},
		callback: function(r) {
			if (r.message && r.message.vehicle_types) {
				frm.allowed_vehicle_types_cache[load_type] = r.message.vehicle_types;
			} else {
				frm.allowed_vehicle_types_cache[load_type] = [];
			}
			if (callback) callback();
		}
	});
}

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

frappe.ui.form.on("Transport Order", {
	setup: function(frm) {
		// Initialize cache for allowed vehicle types
		frm.allowed_vehicle_types_cache = {};
		// Apply load_type filters before field is ever used
		apply_load_type_filters(frm);
	},

	onload: function(frm) {
		// Check if this is a duplicated document with a one-off sales_quote
		// Clear sales_quote field if it's a one-off quote (server-side validation will also handle this)
		if (frm.is_new() && frm.doc.sales_quote) {
			var sales_quote_name = frm.doc.sales_quote;
			frappe.db.get_value('Sales Quote', sales_quote_name, ['one_off'], function(r) {
				if (r && r.one_off === 1) {
					// Clear the sales_quote field and charges
					frm.set_value('sales_quote', '');
					if (frm.doc.charges && frm.doc.charges.length > 0) {
						frm.clear_table('charges');
						frm.refresh_field('charges');
					}
					frappe.msgprint({
						title: __("Sales Quote Cleared"),
						message: __("Sales Quote '{0}' is a one-off quote and cannot be duplicated. The Sales Quote field has been cleared.").format(sales_quote_name),
						indicator: 'orange'
					});
				}
			});
		}
		
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		// Apply transport job type filters on load (preserve existing values for existing documents)
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm, !frm.is_new());
		}
		// Apply load_type filters on load (preserve existing values for existing documents)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, !frm.is_new());
		}
		
		// Set vehicle_type query filter based on load_type (main form)
		if (frm.fields_dict.vehicle_type) {
			frm.fields_dict.vehicle_type.get_query = function() {
				if (!frm.doc.load_type) {
					return {
						filters: {}
					};
				}
				
				// Get cached allowed vehicle types
				const allowed_vehicle_types = frm.allowed_vehicle_types_cache[frm.doc.load_type] || [];
				
				if (allowed_vehicle_types.length === 0) {
					// If no vehicle types are allowed, return empty filter (will show no results)
					return {
						filters: {
							name: ["in", []]
						}
					};
				}
				
				return {
					filters: {
						name: ["in", allowed_vehicle_types]
					}
				};
			};
		}
		
		// Load allowed vehicle types for current load_type if set
		if (frm.doc.load_type) {
			load_allowed_vehicle_types(frm, frm.doc.load_type);
		}
		
		// Set vehicle_type query filter for legs grid (once per form)
		if (frm.fields_dict.legs && frm.fields_dict.legs.grid) {
			frm.fields_dict.legs.grid.get_field('vehicle_type').get_query = function () {
				// 'this' context is the grid row
				var leg = this;
				
				// Filter by load_type if available (from parent or leg)
				var leg_load_type = leg.load_type || frm.doc.load_type;
				if (leg_load_type) {
					// Get cached allowed vehicle types
					const allowed_vehicle_types = frm.allowed_vehicle_types_cache[leg_load_type] || [];
					
					if (allowed_vehicle_types.length === 0) {
						// If no vehicle types are allowed, return empty filter (will show no results)
						return {
							filters: {
								name: ["in", []]
							}
						};
					}
					
					return {
						filters: {
							name: ["in", allowed_vehicle_types]
						}
					};
				}
				
				// Fallback to transport_job_type filtering if no load_type
				var filters = {};
				if (!leg.transport_job_type) {
					return { filters: {} };
				}
				
				// Filter by container flag
				if (leg.transport_job_type === "Container") {
					filters.container = 1;
				} else if (leg.transport_job_type === "Non-Container") {
					filters.container = 0;
				}
				
				// Filter by boolean columns for specific transport job types
				if (leg.transport_job_type === "Special") {
					filters.special = 1;
					filters.reefer = 1;
				} else if (leg.transport_job_type === "Oversized") {
					filters.oversized = 1;
				} else if (leg.transport_job_type === "Heavy Haul") {
					filters.heavy_haul = 1;
				} else if (leg.transport_job_type === "Multimodal") {
					filters.multimodal = 1;
				}
				
				// Filter by reefer if parent refrigeration is required
				if (frm.doc.refrigeration && leg.transport_job_type !== "Special") {
					filters.reefer = 1;
				}
				
				return { filters: filters };
			};
			
			// Set pick_address query filter for legs grid
			var pick_address_field = frm.fields_dict.legs.grid.get_field('pick_address');
			if (pick_address_field) {
				pick_address_field.get_query = function () {
					// 'this' context is the grid row
					var leg = this;
					if (leg.facility_type_from && leg.facility_from) {
						return { 
							filters: { 
								link_doctype: leg.facility_type_from, 
								link_name: leg.facility_from 
							} 
						};
					}
					return { filters: { name: '__none__' } };
				};
			}
			
			// Set drop_address query filter for legs grid
			var drop_address_field = frm.fields_dict.legs.grid.get_field('drop_address');
			if (drop_address_field) {
				drop_address_field.get_query = function () {
					// 'this' context is the grid row
					var leg = this;
					if (leg.facility_type_to && leg.facility_to) {
						return { 
							filters: { 
								link_doctype: leg.facility_type_to, 
								link_name: leg.facility_to 
							} 
						};
					}
					return { filters: { name: '__none__' } };
				};
			}
		}
	},

	refresh: function(frm) {
		// Clear scheduled_date if coming from Sales Quote creation
		if (frappe.route_options && frappe.route_options.__clear_scheduled_date) {
			frm.set_value('scheduled_date', '');
			// Clear the route option to avoid clearing on subsequent refreshes
			delete frappe.route_options.__clear_scheduled_date;
		}
		
		// Show charges populated message after reload (from sales_quote change)
		if (frappe.route_options && frappe.route_options.__show_charges_message) {
			var msg_info = frappe.route_options.__show_charges_message;
			frappe.msgprint({
				title: __("Charges Updated"),
				message: __("Successfully populated {0} charges from Sales Quote: {1}", [msg_info.count, msg_info.sales_quote]),
				indicator: 'green'
			});
			// Clear the route option to avoid showing on subsequent refreshes
			delete frappe.route_options.__show_charges_message;
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
		
		// Apply vehicle_type filters based on load_type on refresh (preserve existing values)
		if (frm.doc.load_type) {
			frm.events.apply_vehicle_type_filters_for_load_type(frm, true);
		}
		// Apply transport job type filters on refresh (preserve existing values)
		// Note: This is now secondary to load_type filtering
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm, true);
		}
		// Apply load_type filters on refresh (preserve existing values)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, true);
		}
		
		// Set vehicle_type query filter for legs grid (ensure it's set on refresh)
		if (frm.fields_dict.legs && frm.fields_dict.legs.grid) {
			frm.fields_dict.legs.grid.get_field('vehicle_type').get_query = function () {
				// 'this' context is the grid row
				var leg = this;
				
				// Filter by load_type if available (from parent or leg)
				var leg_load_type = leg.load_type || frm.doc.load_type;
				if (leg_load_type) {
					// Get cached allowed vehicle types
					const allowed_vehicle_types = frm.allowed_vehicle_types_cache[leg_load_type] || [];
					
					if (allowed_vehicle_types.length === 0) {
						// If no vehicle types are allowed, return empty filter (will show no results)
						return {
							filters: {
								name: ["in", []]
							}
						};
					}
					
					return {
						filters: {
							name: ["in", allowed_vehicle_types]
						}
					};
				}
				
				// Fallback to transport_job_type filtering if no load_type
				var filters = {};
				if (!leg.transport_job_type) {
					return { filters: {} };
				}
				
				// Filter by container flag
				if (leg.transport_job_type === "Container") {
					filters.container = 1;
				} else if (leg.transport_job_type === "Non-Container") {
					filters.container = 0;
				}
				
				// Filter by boolean columns for specific transport job types
				if (leg.transport_job_type === "Special") {
					filters.special = 1;
					filters.reefer = 1;
				} else if (leg.transport_job_type === "Oversized") {
					filters.oversized = 1;
				} else if (leg.transport_job_type === "Heavy Haul") {
					filters.heavy_haul = 1;
				} else if (leg.transport_job_type === "Multimodal") {
					filters.multimodal = 1;
				}
				
				// Filter by reefer if parent refrigeration is required
				if (frm.doc.refrigeration && leg.transport_job_type !== "Special") {
					filters.reefer = 1;
				}
				
				return { filters: filters };
			};
			
			// Set pick_address query filter for legs grid (ensure it's set on refresh)
			var pick_address_field = frm.fields_dict.legs.grid.get_field('pick_address');
			if (pick_address_field) {
				pick_address_field.get_query = function () {
					// 'this' context is the grid row
					var leg = this;
					if (leg.facility_type_from && leg.facility_from) {
						return { 
							filters: { 
								link_doctype: leg.facility_type_from, 
								link_name: leg.facility_from 
							} 
						};
					}
					return { filters: { name: '__none__' } };
				};
			}
			
			// Set drop_address query filter for legs grid (ensure it's set on refresh)
			var drop_address_field = frm.fields_dict.legs.grid.get_field('drop_address');
			if (drop_address_field) {
				drop_address_field.get_query = function () {
					// 'this' context is the grid row
					var leg = this;
					if (leg.facility_type_to && leg.facility_to) {
						return { 
							filters: { 
								link_doctype: leg.facility_type_to, 
								link_name: leg.facility_to 
							} 
						};
					}
					return { filters: { name: '__none__' } };
				};
			}
		}
		
		// Load allowed vehicle types for current load_type if set
		if (frm.doc.load_type) {
			load_allowed_vehicle_types(frm, frm.doc.load_type);
		}
		
		// Render address HTML for all existing legs
		if (frm.doc.legs && frm.doc.legs.length > 0) {
			frm.doc.legs.forEach(function(leg) {
				if (leg.pick_address) {
					render_pick_address_html(frm, leg.doctype, leg.name);
				}
				if (leg.drop_address) {
					render_drop_address_html(frm, leg.doctype, leg.name);
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
		// Update vehicle_type in all legs when parent changes (only on user action)
		populate_legs_vehicle_type_from_parent(frm);
	},
	
	load_type: function(frm) {
		// If load_type is cleared, clear vehicle_type and reset filters
		if (!frm.doc.load_type) {
			if (frm.fields_dict.vehicle_type) {
				frm.fields_dict.vehicle_type.get_query = function() {
					return { filters: {} };
				};
			}
			if (frm.doc.vehicle_type) {
				frm.set_value('vehicle_type', '');
			}
			frm.refresh_field('vehicle_type');
			return;
		}
		
		// Load allowed vehicle types for the selected load_type
		load_allowed_vehicle_types(frm, frm.doc.load_type, function() {
			// Clear vehicle_type if it's not compatible with new load_type
			if (frm.doc.vehicle_type) {
				const allowed_types = frm.allowed_vehicle_types_cache[frm.doc.load_type] || [];
				if (!allowed_types.includes(frm.doc.vehicle_type)) {
					frm.set_value('vehicle_type', '');
					frappe.msgprint({
						title: __("Incompatible Vehicle Type"),
						message: __("Selected vehicle type is not compatible with the selected load type."),
						indicator: 'orange'
					});
				}
			}
			// Refresh the field to apply filters
			frm.refresh_field('vehicle_type');
		});
	},

	transport_job_type: function(frm) {
		// Apply filters and field visibility based on transport job type
		frm.events.apply_transport_job_type_filters(frm);
		// Update transport_job_type in all legs when parent changes (only on user action)
		populate_legs_transport_job_type_from_parent(frm);
		// Clear vehicle_type if it's not compatible with new job type (don't check refrigeration when job type changes)
		if (frm.doc.vehicle_type) {
			frm.events.validate_vehicle_compatibility(frm, true, false);
		}
		// Apply load_type filters (same pattern as vehicle_type)
		apply_load_type_filters(frm);
		// Clear invalid value when job type changes
		frm.set_value('load_type', null);
		// Clear vehicle_type when load_type is cleared (since vehicle_type depends on load_type)
		if (frm.doc.vehicle_type) {
			frm.set_value('vehicle_type', '');
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

	sales_quote: function(frm) {
		// If sales_quote is cleared, clear charges
		if (!frm.doc.sales_quote) {
			// Clear charges table
			frm.clear_table('charges');
			frm.refresh_field('charges');
			return;
		}

		// Get the Sales Quote to check if it's one-off
		frappe.db.get_value('Sales Quote', frm.doc.sales_quote, ['one_off'], function(r) {
			if (r && r.one_off === 1) {
				// Check if a Transport Order already exists for this Sales Quote
				// Build filters to exclude the current document if it's being edited
				var filters = {
					sales_quote: frm.doc.sales_quote
				};
				
				// If this is an existing document, exclude it from the check
				if (!frm.is_new() && frm.doc.name) {
					filters.name = ['!=', frm.doc.name];
				}

				// Use get_list to check if any Transport Order exists with this sales_quote
				frappe.db.get_list('Transport Order', {
					filters: filters,
					limit: 1,
					fields: ['name']
				}).then(function(existing_orders) {
					if (existing_orders && existing_orders.length > 0) {
						frappe.msgprint({
							title: __("Error"),
							message: __("A Transport Order has already been created from this Sales Quote."),
							indicator: 'red'
						});
						// Clear the sales_quote field
						frm.set_value('sales_quote', '');
					}
				});
			}
		});

		// Populate charges from sales_quote
		var docname = frm.is_new() ? null : frm.doc.name;
		var was_saved = !frm.is_new() && docname; // Track if document was saved on server
		
		frappe.call({
			method: "logistics.transport.doctype.transport_order.transport_order.populate_charges_from_sales_quote",
			args: {
				docname: docname,
				sales_quote: frm.doc.sales_quote
			},
			freeze: true,
			freeze_message: __("Fetching charges from Sales Quote..."),
			callback: function(r) {
				if (r.message) {
					if (r.message.error) {
						frappe.msgprint({
							title: __("Error"),
							message: r.message.error,
							indicator: 'red'
						});
						return;
					}
					
					if (r.message.message) {
						frappe.msgprint({
							title: __("No Charges Found"),
							message: r.message.message,
							indicator: 'orange'
						});
					}
					
					// If document was saved on server, reload to sync timestamp
					// This prevents "Document has been modified" error
					// The server-side method now saves the sales_quote field, so it will be preserved on reload
					if (was_saved) {
						// Store message info in route_options to show after reload
						if (r.message.charges_count > 0) {
							frappe.route_options = frappe.route_options || {};
							frappe.route_options.__show_charges_message = {
								count: r.message.charges_count,
								sales_quote: frm.doc.sales_quote
							};
						}
						frm.reload_doc();
					} else {
						// Populate charges in the frontend (only if document wasn't saved on server)
						if (r.message.charges && r.message.charges.length > 0) {
							frm.clear_table('charges');
							r.message.charges.forEach(function(charge) {
								var row = frm.add_child('charges');
								// Set values directly on the row object
								Object.keys(charge).forEach(function(key) {
									if (charge[key] !== null && charge[key] !== undefined) {
										row[key] = charge[key];
									}
								});
							});
							frm.refresh_field('charges');
							
							if (r.message.charges_count > 0) {
								frappe.msgprint({
									title: __("Charges Updated"),
									message: __("Successfully populated {0} charges from Sales Quote: {1}", [r.message.charges_count, frm.doc.sales_quote]),
									indicator: 'green'
								});
							}
						} else {
							// Clear charges if none found
							frm.clear_table('charges');
							frm.refresh_field('charges');
						}
					}
				}
			},
			error: function(r) {
				frappe.msgprint({
					title: __("Error"),
					message: __("Failed to populate charges from Sales Quote."),
					indicator: 'red'
				});
			}
		});
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

	apply_vehicle_type_filters_for_load_type: function(frm, preserve_existing_value) {
		// Filter vehicle types based on load_type using allowed_load_types
		// preserve_existing_value: if true, don't clear vehicle_type even if not in filtered list (used during refresh)
		if (!frm.doc.load_type) {
			// Clear filters if no load_type selected
			if (frm.fields_dict.vehicle_type) {
				frm.fields_dict.vehicle_type.get_query = function() {
					return { filters: {} };
				};
			}
			frm.refresh_field('vehicle_type');
			return;
		}

		// Load allowed vehicle types and then validate
		load_allowed_vehicle_types(frm, frm.doc.load_type, function() {
			// Validate current vehicle_type if set
			if (!preserve_existing_value && frm.doc.vehicle_type) {
				const allowed_types = frm.allowed_vehicle_types_cache[frm.doc.load_type] || [];
				if (!allowed_types.includes(frm.doc.vehicle_type)) {
					frm.set_value('vehicle_type', '');
				}
			}
			frm.refresh_field('vehicle_type');
		});
	},

	apply_transport_job_type_filters: function(frm, preserve_existing_value) {
		// Filter vehicle types based on transport job type, refrigeration, and boolean columns
		// NOTE: This is now secondary to load_type filtering. Vehicle type filtering is primarily based on load_type.
		// preserve_existing_value: if true, don't clear vehicle_type even if not in filtered list (used during refresh)
		if (!frm.doc.transport_job_type) {
			// Clear filters if no job type selected
			// But only if load_type is also not set (since vehicle_type now depends on load_type)
			if (!frm.doc.load_type) {
				if (frm.fields_dict.vehicle_type) {
					frm.fields_dict.vehicle_type.get_query = function() {
						return { filters: {} };
					};
				}
				frm.refresh_field('vehicle_type');
			}
			return;
		}

		// If load_type is set, vehicle_type filtering is handled by load_type
		// Only apply transport_job_type filters if load_type is not set
		if (frm.doc.load_type) {
			// Vehicle type filtering is handled by load_type, so skip transport_job_type filtering
			return;
		}

		// Build filters based on job type and refrigeration
		var filters = {};
		
		// Filter by container flag
		if (frm.doc.transport_job_type === "Container") {
			filters.container = 1;
		} else if (frm.doc.transport_job_type === "Non-Container") {
			filters.container = 0;
		}
		
		// Filter by boolean columns for specific transport job types
		if (frm.doc.transport_job_type === "Special") {
			filters.special = 1;
			// Special job type also requires reefer
			filters.reefer = 1;
		} else if (frm.doc.transport_job_type === "Oversized") {
			filters.oversized = 1;
		} else if (frm.doc.transport_job_type === "Heavy Haul") {
			filters.heavy_haul = 1;
		} else if (frm.doc.transport_job_type === "Multimodal") {
			filters.multimodal = 1;
		}
		
		// Filter by reefer if refrigeration is required (for other job types)
		// Note: Special job type already has reefer=1 filter above
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
		
		// Validate packages is not empty
		var packages = frm.doc.packages || [];
		if (!packages || packages.length === 0) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __("Packages are required. Please add at least one package before submitting the Transport Order."),
				indicator: 'red'
			});
			return Promise.reject(__("Packages are required. Please add at least one package before submitting the Transport Order."));
		}
		
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
// Updates all legs when parent vehicle_type changes
function populate_legs_vehicle_type_from_parent(frm) {
	if (!frm.doc.legs || frm.doc.legs.length === 0 || !frm.doc.vehicle_type) {
		return;
	}
	
	var updated = false;
	frm.doc.legs.forEach(function(leg) {
		// Update all legs with parent vehicle_type (even if they already have a value)
		if (leg.vehicle_type !== frm.doc.vehicle_type) {
			frappe.model.set_value(leg.doctype, leg.name, 'vehicle_type', frm.doc.vehicle_type);
			updated = true;
		}
	});
	
	if (updated) {
		frm.refresh_field('legs');
	}
}

// Helper function to populate transport_job_type in legs from parent (only on user action)
// Updates all legs when parent transport_job_type changes
function populate_legs_transport_job_type_from_parent(frm) {
	if (!frm.doc.legs || frm.doc.legs.length === 0 || !frm.doc.transport_job_type) {
		return;
	}
	
	var updated = false;
	frm.doc.legs.forEach(function(leg) {
		// Update all legs with parent transport_job_type (even if they already have a value)
		if (leg.transport_job_type !== frm.doc.transport_job_type) {
			frappe.model.set_value(leg.doctype, leg.name, 'transport_job_type', frm.doc.transport_job_type);
			updated = true;
		}
	});
	
	if (updated) {
		frm.refresh_field('legs');
	}
}

// ---------- Auto-fill Address Functions for Transport Order Legs ----------
async function auto_fill_pick_address(frm, cdt, cdn) {
	var leg = frappe.get_doc(cdt, cdn);
	if (!leg.facility_type_from || !leg.facility_from) {
		return;
	}
	
	try {
		const result = await frappe.call({
			method: 'logistics.transport.doctype.transport_order_legs.transport_order_legs.get_primary_address',
			args: {
				facility_type: leg.facility_type_from,
				facility_name: leg.facility_from
			}
		});
		
		if (result.message && !leg.pick_address) {
			frappe.model.set_value(cdt, cdn, 'pick_address', result.message);
			// Render address HTML after setting the address
			setTimeout(function() {
				render_pick_address_html(frm, cdt, cdn);
			}, 100);
		}
	} catch (error) {
		console.error('Error auto-filling pick address:', error);
	}
}

async function auto_fill_drop_address(frm, cdt, cdn) {
	var leg = frappe.get_doc(cdt, cdn);
	if (!leg.facility_type_to || !leg.facility_to) {
		return;
	}
	
	try {
		const result = await frappe.call({
			method: 'logistics.transport.doctype.transport_order_legs.transport_order_legs.get_primary_address',
			args: {
				facility_type: leg.facility_type_to,
				facility_name: leg.facility_to
			}
		});
		
		if (result.message && !leg.drop_address) {
			frappe.model.set_value(cdt, cdn, 'drop_address', result.message);
			// Render address HTML after setting the address
			setTimeout(function() {
				render_drop_address_html(frm, cdt, cdn);
			}, 100);
		}
	} catch (error) {
		console.error('Error auto-filling drop address:', error);
	}
}

// ---------- Render Address HTML Functions for Transport Order Legs ----------
function render_pick_address_html(frm, cdt, cdn) {
	var leg = frappe.get_doc(cdt, cdn);
	if (!leg.pick_address) {
		frappe.model.set_value(cdt, cdn, 'pick_address_html', '');
		return;
	}
	
	frappe.call({
		method: 'logistics.utils.address.render_address_html',
		args: { address_name: leg.pick_address },
		callback: function(r) {
			if (r.message) {
				// Remove <br> tags from the address HTML
				var address_html = r.message.replace(/<br\s*\/?>/gi, '');
				frappe.model.set_value(cdt, cdn, 'pick_address_html', address_html);
			}
		}
	});
}

function render_drop_address_html(frm, cdt, cdn) {
	var leg = frappe.get_doc(cdt, cdn);
	if (!leg.drop_address) {
		frappe.model.set_value(cdt, cdn, 'drop_address_html', '');
		return;
	}
	
	frappe.call({
		method: 'logistics.utils.address.render_address_html',
		args: { address_name: leg.drop_address },
		callback: function(r) {
			if (r.message) {
				// Remove <br> tags from the address HTML
				var address_html = r.message.replace(/<br\s*\/?>/gi, '');
				frappe.model.set_value(cdt, cdn, 'drop_address_html', address_html);
			}
		}
	});
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
	},

	facility_type_from: function(frm, cdt, cdn) {
		// Fetch primary address when facility_type_from changes
		var leg = frappe.get_doc(cdt, cdn);
		if (leg.facility_type_from && leg.facility_from) {
			auto_fill_pick_address(frm, cdt, cdn);
		} else {
			// Clear pick_address if facility_type_from is cleared
			if (leg.pick_address) {
				frappe.model.set_value(cdt, cdn, 'pick_address', '');
			}
		}
		frm.refresh_field('legs');
	},

	facility_from: function(frm, cdt, cdn) {
		// Fetch primary address when facility_from changes
		var leg = frappe.get_doc(cdt, cdn);
		if (leg.facility_type_from && leg.facility_from) {
			auto_fill_pick_address(frm, cdt, cdn);
		} else {
			// Clear pick_address if facility_from is cleared
			if (leg.pick_address) {
				frappe.model.set_value(cdt, cdn, 'pick_address', '');
			}
		}
		frm.refresh_field('legs');
	},

	facility_type_to: function(frm, cdt, cdn) {
		// Fetch primary address when facility_type_to changes
		var leg = frappe.get_doc(cdt, cdn);
		if (leg.facility_type_to && leg.facility_to) {
			auto_fill_drop_address(frm, cdt, cdn);
		} else {
			// Clear drop_address if facility_type_to is cleared
			if (leg.drop_address) {
				frappe.model.set_value(cdt, cdn, 'drop_address', '');
			}
		}
		frm.refresh_field('legs');
	},

	facility_to: function(frm, cdt, cdn) {
		// Fetch primary address when facility_to changes
		var leg = frappe.get_doc(cdt, cdn);
		if (leg.facility_type_to && leg.facility_to) {
			auto_fill_drop_address(frm, cdt, cdn);
		} else {
			// Clear drop_address if facility_to is cleared
			if (leg.drop_address) {
				frappe.model.set_value(cdt, cdn, 'drop_address', '');
			}
		}
		frm.refresh_field('legs');
	},

	pick_address: function(frm, cdt, cdn) {
		// Render address HTML when pick_address changes
		render_pick_address_html(frm, cdt, cdn);
	},

	drop_address: function(frm, cdt, cdn) {
		// Render address HTML when drop_address changes
		render_drop_address_html(frm, cdt, cdn);
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
	
	// Filter by container flag
	if (leg.transport_job_type === "Container") {
		filters.container = 1;
	} else if (leg.transport_job_type === "Non-Container") {
		filters.container = 0;
	}
	
	// Filter by boolean columns for specific transport job types
	if (leg.transport_job_type === "Special") {
		filters.special = 1;
		// Special job type also requires reefer
		filters.reefer = 1;
	} else if (leg.transport_job_type === "Oversized") {
		filters.oversized = 1;
	} else if (leg.transport_job_type === "Heavy Haul") {
		filters.heavy_haul = 1;
	} else if (leg.transport_job_type === "Multimodal") {
		filters.multimodal = 1;
	}
	
	// Filter by reefer if parent refrigeration is required (for other job types)
	// Note: Special job type already has reefer=1 filter above
	if (frm.doc.refrigeration && leg.transport_job_type !== "Special") {
		filters.reefer = 1;
	}

	// Guard: Only clear vehicle_type if it is non-empty (prevent clearing empty values)
	if (leg.vehicle_type) {
		frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
	}
	
	// Refresh the field to apply the get_query filter (set in onload)
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
	
	// Filter by container flag
	if (leg.transport_job_type === "Container") {
		filters.container = 1;
	} else if (leg.transport_job_type === "Non-Container") {
		filters.container = 0;
	}
	
	// Filter by boolean columns for specific transport job types
	if (leg.transport_job_type === "Special") {
		filters.special = 1;
		// Special job type also requires reefer
		filters.reefer = 1;
	} else if (leg.transport_job_type === "Oversized") {
		filters.oversized = 1;
	} else if (leg.transport_job_type === "Heavy Haul") {
		filters.heavy_haul = 1;
	} else if (leg.transport_job_type === "Multimodal") {
		filters.multimodal = 1;
	}
	
	// Filter by reefer if parent refrigeration is required (for other job types)
	// Note: Special job type already has reefer=1 filter above
	if (frm.doc.refrigeration && leg.transport_job_type !== "Special") {
		filters.reefer = 1;
	}
	
	// get_query is set in onload and reads from current row dynamically
	// No need to set it here - just refresh if needed
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

// ---------- Package Volume Calculation Functions ----------
// Helper function to calculate volume for a package row
function calculate_package_volume(frm, cdt, cdn) {
	var package_row = frappe.get_doc(cdt, cdn);
	if (package_row.length && package_row.width && package_row.height) {
		// Calculate volume: length × width × height
		const volume = package_row.length * package_row.width * package_row.height;
		frappe.model.set_value(cdt, cdn, 'volume', volume);
	} else {
		frappe.model.set_value(cdt, cdn, 'volume', 0);
	}
}

// Child table events for Transport Order Package
frappe.ui.form.on('Transport Order Package', {
	length: function(frm, cdt, cdn) {
		calculate_package_volume(frm, cdt, cdn);
	},

	width: function(frm, cdt, cdn) {
		calculate_package_volume(frm, cdt, cdn);
	},

	height: function(frm, cdt, cdn) {
		calculate_package_volume(frm, cdt, cdn);
	}
});