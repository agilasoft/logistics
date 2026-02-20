// Cache key for Vehicle Type list by (load_type, hazardous, reefer) - used for load_type-based filter only
function vehicle_type_cache_key(load_type, hazardous, reefer) {
	return (load_type || "") + "|" + (hazardous ? "1" : "0") + "|" + (reefer ? "1" : "0");
}

// Build Address link filter for a leg row - used by pick_address and drop_address get_query.
// Uses (doc, cdt, cdn) so the correct row is used when opening the link from the grid.
function get_address_query_for_leg(frm, doc, cdt, cdn, kind) {
	var leg = null;
	if (locals[cdt] && locals[cdt][cdn]) {
		leg = locals[cdt][cdn];
	} else if (cdt && cdn) {
		leg = frappe.get_doc(cdt, cdn);
	}
	if (!leg) {
		return { filters: { name: '__none__' } };
	}
	var facility_type = kind === 'pick' ? leg.facility_type_from : leg.facility_type_to;
	var facility_name = kind === 'pick' ? leg.facility_from : leg.facility_to;
	if (!facility_type || !facility_name) {
		return { filters: { name: '__none__' } };
	}
	var address_names = [];
	frappe.call({
		method: 'logistics.transport.doctype.transport_order_legs.transport_order_legs.get_addresses_for_facility',
		args: { facility_type: facility_type, facility_name: facility_name },
		async: false,
		callback: function(r) {
			if (r.message && Array.isArray(r.message)) {
				address_names = r.message;
			}
		}
	});
	if (address_names.length > 0) {
		return { filters: { name: ['in', address_names] } };
	}
	return { filters: { name: '__none__' } };
}

// Build filter description for Vehicle Type field (includes Load type so it shows in the dropdown)
function update_vehicle_type_filter_description(frm) {
	if (!frm.fields_dict.vehicle_type) return;
	var parts = [];
	if (frm.doc.load_type) {
		parts.push(__("Load type is {0}", [frm.doc.load_type]));
	}
	parts.push(frm.doc.hazardous ? __("Hazardous is enabled") : __("Hazardous is disabled"));
	parts.push(frm.doc.reefer ? __("Reefer is enabled") : __("Reefer is disabled"));
	if (frm.doc.load_type) {
		var key = vehicle_type_cache_key(frm.doc.load_type, frm.doc.hazardous, frm.doc.reefer);
		var names = frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key];
		if (names && names.length) {
			var nameList = names.length > 5 ? names.slice(0, 5).join(", ") + "…" : names.join(", ");
			parts.push(__("Name is one of {0}", [nameList]));
		}
	}
	frm.fields_dict.vehicle_type.df.filter_description = __("Filtered by: {0}.", [frappe.utils.comma_and(parts)]);
}

// Load Vehicle Type names for load_type + hazardous + reefer (for get_query; load_type filter cannot be done in link_filters)
function load_vehicle_types_for_load_type(frm, load_type, callback) {
	if (!load_type) {
		if (callback) callback();
		return;
	}
	var hazardous = frm.doc.hazardous ? 1 : 0;
	var reefer = frm.doc.reefer ? 1 : 0;
	var key = vehicle_type_cache_key(load_type, hazardous, reefer);
	if (frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key]) {
		if (callback) callback();
		return;
	}
	frappe.call({
		method: "logistics.transport.doctype.transport_order.transport_order.get_vehicle_types_for_load_type",
		args: { load_type: load_type, hazardous: hazardous, reefer: reefer },
		callback: function(r) {
			if (!frm._vehicle_types_by_load_type) frm._vehicle_types_by_load_type = {};
			frm._vehicle_types_by_load_type[key] = (r.message && r.message.vehicle_types) ? r.message.vehicle_types : [];
			if (callback) callback();
		}
	});
}

// Helper function to apply load_type filters
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
		frm._vehicle_types_by_load_type = {};
		// Apply load_type filters before field is ever used
		apply_load_type_filters(frm);
	},

	onload: function(frm) {
		// Suppress "Transport Order X not found" when form is new/unsaved (package grid triggers API before save)
		if (frm.is_new() || frm.doc.__islocal) {
			if (!frappe._original_msgprint) {
				frappe._original_msgprint = frappe.msgprint;
			}
			frappe.msgprint = function(options) {
				const message = typeof options === 'string' ? options : (options && options.message || '');
				if (message && typeof message === 'string' &&
					message.includes('Transport Order') &&
					message.includes('not found')) {
					return;
				}
				return frappe._original_msgprint.apply(this, arguments);
			};
			frm.$wrapper.one('form-refresh', function() {
				if (!frm.is_new() && !frm.doc.__islocal && frappe._original_msgprint) {
					frappe.msgprint = frappe._original_msgprint;
				}
			});
		}
		// Note: one_off field has been removed from Sales Quote doctype
		// One-off quotes are now handled by the separate "One-Off Quote" doctype
		// This check is no longer needed as Sales Quote no longer has the one_off field
		
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		// Apply transport job type filters on load (container/reefer field visibility, etc.)
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm, !frm.is_new());
		}
		// Apply load_type filters on load (preserve existing values for existing documents)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, !frm.is_new());
		}

		// Set get_query for Load Type so filter is applied and "Filtered by" is shown (transport_job_type based)
		if (frm.fields_dict.load_type) {
			frm.fields_dict.load_type.get_query = function() {
				if (!frm.doc.transport_job_type) {
					return { filters: { transport: 1 } };
				}
				var filters = { transport: 1 };
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
				return { filters: filters };
			};
		}

		// Vehicle Type: filter by load_type + hazardous + reefer (all in get_query; link_filters would overwrite get_query)
		if (frm.fields_dict.vehicle_type) {
			frm.fields_dict.vehicle_type.get_query = function() {
				var filters = {
					hazardous: frm.doc.hazardous ? 1 : 0,
					reefer: frm.doc.reefer ? 1 : 0
				};
				if (!frm.doc.load_type) {
					return { filters: filters };
				}
				var key = vehicle_type_cache_key(frm.doc.load_type, frm.doc.hazardous, frm.doc.reefer);
				var names = frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key];
				if (!names) {
					load_vehicle_types_for_load_type(frm, frm.doc.load_type);
					return { filters: Object.assign({ name: ["in", []] }, filters) };
				}
				filters.name = ["in", names];
				return { filters: filters };
			};
		}
		
		// Pre-load Vehicle Type list when load_type is set so dropdown is filtered when opened
		update_vehicle_type_filter_description(frm);
		if (frm.doc.load_type) {
			load_vehicle_types_for_load_type(frm, frm.doc.load_type, function() {
				update_vehicle_type_filter_description(frm);
				frm.refresh_field('vehicle_type');
			});
		}

		// Legs grid: vehicle_type filter by parent/leg load_type + hazardous + reefer
		if (frm.fields_dict.legs && frm.fields_dict.legs.grid) {
			var vt_field = frm.fields_dict.legs.grid.get_field('vehicle_type');
			if (vt_field) {
				vt_field.get_query = function() {
					var leg = this;
					var lt = leg.load_type || frm.doc.load_type;
					var filters = {
						hazardous: frm.doc.hazardous ? 1 : 0,
						reefer: frm.doc.reefer ? 1 : 0
					};
					if (!lt) return { filters: filters };
					var key = vehicle_type_cache_key(lt, frm.doc.hazardous, frm.doc.reefer);
					var names = frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key];
					if (!names) {
						load_vehicle_types_for_load_type(frm, lt);
						return { filters: Object.assign({ name: ["in", []] }, filters) };
					}
					filters.name = ["in", names];
					return { filters: filters };
				};
			}
			// Set pick_address and drop_address query filters for legs grid using frm.set_query
			// so the callback receives (doc, cdt, cdn) and we filter by that row's Facility From/To
			frm.set_query('pick_address', 'legs', function(doc, cdt, cdn) {
				return get_address_query_for_leg(frm, doc, cdt, cdn, 'pick');
			});
			frm.set_query('drop_address', 'legs', function(doc, cdt, cdn) {
				return get_address_query_for_leg(frm, doc, cdt, cdn, 'drop');
			});
		}
		
		// Set query for quote field to filter out already-used One-Off Quotes
		_setup_quote_query(frm);
	},

	refresh: function(frm) {
		// Helper function to execute refresh operations
		var do_refresh_ops = function() {
		// Guard: Skip database queries if document name is temporary (just saved, not committed yet)
		// This prevents "not found" errors when refresh runs immediately after save
		var skip_db_queries = frm.is_new() || (frm.doc.name && frm.doc.name.startsWith('new-'));
		
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
			console.log("refresh: Document is saved and ready for submission", frm.doc.name);
		}
		
		// Add Create Leg Plan button if transport template is set and document is not submitted
		// Only show if document exists and has a valid name (not temporary)
		if (!frm.is_new() && frm.doc.transport_template && frm.doc.docstatus !== 1 && 
		    frm.doc.name && !frm.doc.name.startsWith('new-')) {
			frm.add_custom_button(__("Leg Plan"), function() {
				// Ensure document is saved before creating leg plan
				if (frm.is_dirty()) {
					frm.save().then(function() {
						_create_leg_plan(frm);
					});
				} else {
					_create_leg_plan(frm);
				}
			}, __("Create"));
		}
		
		// Lalamove Integration
		if (frm.doc.use_lalamove && !frm.is_new() && !skip_db_queries) {
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
			// Delay query to avoid "not found" errors immediately after save
			if (frm.doc.lalamove_order) {
				setTimeout(function() {
					frappe.db.get_value('Lalamove Order', frm.doc.lalamove_order, ['status', 'lalamove_order_id'], (r) => {
						if (r && r.status) {
							const status_color = r.status === 'COMPLETED' ? 'green' : (r.status === 'CANCELLED' ? 'red' : 'blue');
							frm.dashboard.add_indicator(__('Lalamove: {0}', [r.status]), status_color);
						}
					});
				}, 300);
			}
		}
		
		// Add Create Transport Job button if document is submitted
		// Check if Transport Job already exists first
		// Only check if document is saved (not new) and has a real name (not temporary)
		if (frm.doc.docstatus === 1 && !frm.is_new() && frm.doc.name && !frm.doc.name.startsWith('new-') && !skip_db_queries) {
			// Delay query to avoid "not found" errors immediately after save
			setTimeout(function() {
				// Check if a Transport Job already exists for this Transport Order
				frappe.db.get_value('Transport Job', { transport_order: frm.doc.name }, 'name', function(r) {
				if (r && r.name) {
					// Transport Job already exists - show link to existing job
					frm.add_custom_button(__("Transport Job"), function() {
						frappe.set_route("Form", "Transport Job", r.name);
					}, __("View"));
					// Show indicator that Transport Job exists
					frm.dashboard.add_indicator(__('Transport Job: {0}', [r.name]), 'blue');
				} else {
					// No Transport Job exists - show create button
					frm.add_custom_button(__("Transport Job"), function() {
						frappe.call({
							method: "logistics.transport.doctype.transport_order.transport_order.action_create_transport_job",
							args: {
								docname: frm.doc.name
							},
							freeze: true,
							freeze_message: __("Creating transport job..."),
							callback: function(response) {
								if (response.message) {
									if (response.message.already_exists) {
										frappe.msgprint({
											title: __("Transport Job Already Exists"),
											message: __("Transport Job {0} already exists for this Transport Order.", [response.message.name]),
											indicator: 'blue'
										});
										frappe.set_route("Form", "Transport Job", response.message.name);
										// Wait for form to load, then refresh title
										setTimeout(function() {
											var job_frm = frappe.get_cur_form();
											if (job_frm && job_frm.doctype === "Transport Job" && job_frm.doc.name === response.message.name) {
												job_frm.refresh();
												// Force title update
												if (job_frm.page && job_frm.page.set_title) {
													job_frm.page.set_title(job_frm.doc.name);
												}
											}
										}, 500);
										// Refresh to update button (use refresh instead of reload_doc to avoid "not found" errors)
										frm.refresh();
									} else if (response.message.created) {
										frappe.msgprint({
											title: __("Transport Job Created"),
											message: __("Transport Job {0} created successfully.", [response.message.name]),
											indicator: 'green'
										});
										frappe.set_route("Form", "Transport Job", response.message.name);
										// Wait for form to load, then refresh title
										setTimeout(function() {
											var job_frm = frappe.get_cur_form();
											if (job_frm && job_frm.doctype === "Transport Job" && job_frm.doc.name === response.message.name) {
												job_frm.refresh();
												// Force title update
												if (job_frm.page && job_frm.page.set_title) {
													job_frm.page.set_title(job_frm.doc.name);
												}
											}
										}, 500);
										// Refresh to update button (use refresh instead of reload_doc to avoid "not found" errors)
										frm.refresh();
									}
								}
							}
						});
					}, __("Create"));
				}
			});
			}, 300);
		}
		
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		
		// Apply transport job type filters on refresh (container/reefer field visibility, etc.)
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm, true);
		}
		// Apply load_type filters on refresh (preserve existing values)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, true);
		}

		// Set get_query for Load Type on refresh (ensure filter and "Filtered by" work)
		if (frm.fields_dict.load_type) {
			frm.fields_dict.load_type.get_query = function() {
				if (!frm.doc.transport_job_type) {
					return { filters: { transport: 1 } };
				}
				var filters = { transport: 1 };
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
				return { filters: filters };
			};
		}

		// Vehicle Type get_query on refresh (filter by load_type + hazardous + reefer)
		if (frm.fields_dict.vehicle_type) {
			frm.fields_dict.vehicle_type.get_query = function() {
				var filters = {
					hazardous: frm.doc.hazardous ? 1 : 0,
					reefer: frm.doc.reefer ? 1 : 0
				};
				if (!frm.doc.load_type) {
					return { filters: filters };
				}
				var key = vehicle_type_cache_key(frm.doc.load_type, frm.doc.hazardous, frm.doc.reefer);
				var names = frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key];
				if (!names) {
					load_vehicle_types_for_load_type(frm, frm.doc.load_type);
					return { filters: Object.assign({ name: ["in", []] }, filters) };
				}
				filters.name = ["in", names];
				return { filters: filters };
			};
		}
		update_vehicle_type_filter_description(frm);
		if (frm.doc.load_type) {
			load_vehicle_types_for_load_type(frm, frm.doc.load_type, function() {
				update_vehicle_type_filter_description(frm);
			});
		}

		// Legs grid: vehicle_type filter by parent load_type (and parent hazardous/reefer)
		if (frm.fields_dict.legs && frm.fields_dict.legs.grid) {
			var vt_field = frm.fields_dict.legs.grid.get_field('vehicle_type');
			if (vt_field) {
				vt_field.get_query = function() {
					var leg = this;
					var lt = leg.load_type || frm.doc.load_type;
					var filters = {
						hazardous: frm.doc.hazardous ? 1 : 0,
						reefer: frm.doc.reefer ? 1 : 0
					};
					if (!lt) return { filters: filters };
					var key = vehicle_type_cache_key(lt, frm.doc.hazardous, frm.doc.reefer);
					var names = frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key];
					if (!names) {
						load_vehicle_types_for_load_type(frm, lt);
						return { filters: Object.assign({ name: ["in", []] }, filters) };
					}
					filters.name = ["in", names];
					return { filters: filters };
				};
			}
		}
		
		// Set pick_address and drop_address query filters for legs grid on refresh
		// (same as onload: use frm.set_query so callback receives doc, cdt, cdn for correct row)
		if (frm.fields_dict.legs && frm.fields_dict.legs.grid) {
			frm.set_query('pick_address', 'legs', function(doc, cdt, cdn) {
				return get_address_query_for_leg(frm, doc, cdt, cdn, 'pick');
			});
			frm.set_query('drop_address', 'legs', function(doc, cdt, cdn) {
				return get_address_query_for_leg(frm, doc, cdt, cdn, 'drop');
			});
		}
		
		// Refresh quote query setup
		_setup_quote_query(frm);
		
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

		// Store current UOMs on package rows for measurement conversion on change
		(frm.doc.packages || []).forEach(function(row) {
			row._prev_dimension_uom = row.dimension_uom;
			row._prev_volume_uom = row.volume_uom;
			row._prev_weight_uom = row.weight_uom;
			row._prev_chargeable_weight_uom = row.chargeable_weight_uom;
		});
		}; // End of do_refresh_ops function
		
		// Always call refresh operations directly (removed existence check to avoid race conditions)
		do_refresh_ops();
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
		update_vehicle_type_filter_description(frm);
		if (!frm.doc.load_type) {
			frm.refresh_field('vehicle_type');
			frm.refresh_field('legs');
			return;
		}
		load_vehicle_types_for_load_type(frm, frm.doc.load_type, function() {
			update_vehicle_type_filter_description(frm);
			frm.refresh_field('vehicle_type');
			frm.refresh_field('legs');
		});
	},

	transport_job_type: function(frm) {
		// Apply field visibility based on transport job type (container/reefer fields, etc.)
		frm.events.apply_transport_job_type_filters(frm);
		// Update transport_job_type in all legs when parent changes (only on user action)
		populate_legs_transport_job_type_from_parent(frm);
		// Apply load_type filters
		apply_load_type_filters(frm);
		// Clear load_type when job type changes (load_type options depend on job type)
		frm.set_value('load_type', null);
	},

	hazardous: function(frm) {
		update_vehicle_type_filter_description(frm);
		if (frm.doc.load_type) {
			load_vehicle_types_for_load_type(frm, frm.doc.load_type, function() {
				update_vehicle_type_filter_description(frm);
				frm.refresh_field('vehicle_type');
				frm.refresh_field('legs');
			});
		} else {
			frm.refresh_field('vehicle_type');
			frm.refresh_field('legs');
		}
	},
	reefer: function(frm) {
		if (frm.doc.transport_job_type) {
			frm.events.apply_transport_job_type_filters(frm);
		}
		update_vehicle_type_filter_description(frm);
		if (frm.doc.load_type) {
			load_vehicle_types_for_load_type(frm, frm.doc.load_type, function() {
				update_vehicle_type_filter_description(frm);
				frm.refresh_field('vehicle_type');
				frm.refresh_field('legs');
			});
		} else {
			frm.refresh_field('vehicle_type');
			frm.refresh_field('legs');
		}
		if (frm.doc.vehicle_type) {
			frm.events.validate_vehicle_compatibility(frm, true, true);
		}
	},

	sales_quote: function(frm) {
		_populate_charges_from_quote(frm);
	},
	quote_type: function(frm) {
		// Don't clear quote fields if document is already submitted
		if (frm.doc.docstatus === 1) {
			return;
		}
		
		// If changing quote type and there's an existing quote, clear it
		// This ensures users select a new quote of the correct type
		if (frm.doc.quote) {
			frm.set_value('quote', '');
		}
		
		// Setup query filter for quote field based on quote_type
		_setup_quote_query(frm);
		
		if (!frm.doc.quote) {
			frm.clear_table('charges');
			frm.refresh_field('charges');
		} else {
			_populate_charges_from_quote(frm);
		}
	},
	quote: function(frm) {
		// Don't clear quote fields if document is already submitted
		if (frm.doc.docstatus === 1) {
			return;
		}
		if (!frm.doc.quote) {
			frm.clear_table('charges');
			frm.refresh_field('charges');
			// Clear sales_quote when quote is cleared
			if (frm.doc.sales_quote) {
				frm.set_value('sales_quote', '');
			}
			return;
		}
		// Sync sales_quote field when quote_type is "Sales Quote"
		if (frm.doc.quote_type === 'Sales Quote' && frm.doc.quote) {
			frm.set_value('sales_quote', frm.doc.quote);
		} else if (frm.doc.quote_type === 'One-Off Quote') {
			// Clear sales_quote for One-Off Quote
			frm.set_value('sales_quote', '');
		}
		_populate_charges_from_quote(frm);
	}
});

// Setup query filter for quote field to exclude already-used One-Off Quotes
function _setup_quote_query(frm) {
	if (frm.doc.quote_type === 'One-Off Quote') {
		// Load available One-Off Quotes filters
		frappe.call({
			method: 'logistics.transport.doctype.transport_order.transport_order.get_available_one_off_quotes',
			args: { transport_order_name: frm.doc.name || null },
			callback: function(r) {
				if (r.message && r.message.filters) {
					frm._available_one_off_quotes_filters = r.message.filters;
				}
			}
		});
		
		// Set query filter for quote field
		frm.set_query('quote', function() {
			// Return cached filters or empty filters
			// If filters not loaded yet, they'll be empty but that's okay
			// The user can still type and select, validation will catch duplicates
			return { 
				filters: frm._available_one_off_quotes_filters || {} 
			};
		});
	} else if (frm.doc.quote_type === 'Sales Quote') {
		// For Sales Quote, clear any special filters
		frm.set_query('quote', function() {
			return { filters: {} };
		});
	}
}

function _populate_charges_from_quote(frm) {
	var docname = frm.is_new() ? null : frm.doc.name;
	var quote_type = frm.doc.quote_type;
	var quote = frm.doc.quote;
	var sales_quote = frm.doc.sales_quote;
	
	// Determine which quote to use
	var target_quote = null;
	var method_name = null;
	var freeze_message = null;
	var success_message_template = null;
	
	if (quote_type === 'Sales Quote' && quote) {
		target_quote = quote;
		method_name = "logistics.transport.doctype.transport_order.transport_order.populate_charges_from_sales_quote";
		freeze_message = __("Fetching charges from Sales Quote...");
		success_message_template = __("Successfully populated {0} charges from Sales Quote: {1}");
	} else if (quote_type === 'One-Off Quote' && quote) {
		target_quote = quote;
		method_name = "logistics.transport.doctype.transport_order.transport_order.populate_charges_from_one_off_quote";
		freeze_message = __("Fetching charges from One-Off Quote...");
		success_message_template = __("Successfully populated {0} charges from One-Off Quote: {1}");
	} else if (sales_quote) {
		// Fallback to sales_quote field for backward compatibility
		target_quote = sales_quote;
		method_name = "logistics.transport.doctype.transport_order.transport_order.populate_charges_from_sales_quote";
		freeze_message = __("Fetching charges from Sales Quote...");
		success_message_template = __("Successfully populated {0} charges from Sales Quote: {1}");
	}
	
	if (!target_quote || !method_name) {
		frm.clear_table('charges');
		frm.refresh_field('charges');
		return;
	}
	
	frappe.call({
		method: method_name,
		args: {
			docname: docname,
			sales_quote: quote_type === 'Sales Quote' ? target_quote : null,
			one_off_quote: quote_type === 'One-Off Quote' ? target_quote : null
		},
		freeze: true,
		freeze_message: freeze_message,
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
				// Update charges on the form (works for both new and saved documents)
				// This avoids "document has been modified" errors by not saving on server
				if (r.message.charges && r.message.charges.length > 0) {
					frm.clear_table('charges');
					r.message.charges.forEach(function(charge) {
						var row = frm.add_child('charges');
						Object.keys(charge).forEach(function(key) {
							if (charge[key] !== null && charge[key] !== undefined) {
								row[key] = charge[key];
							}
						});
					});
					frm.refresh_field('charges');
					if (r.message.charges_count > 0) {
						var message = success_message_template;
						if (quote_type === 'One-Off Quote') {
							message = __("Successfully populated {0} charges from One-Off Quote: {1}", [r.message.charges_count, target_quote]);
						} else {
							message = __("Successfully populated {0} charges from Sales Quote: {1}", [r.message.charges_count, target_quote]);
						}
						frappe.msgprint({
							title: __("Charges Updated"),
							message: message,
							indicator: 'green'
						});
					}
				} else {
					frm.clear_table('charges');
					frm.refresh_field('charges');
				}
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to populate charges from quote."),
				indicator: 'red'
			});
		}
	});
}

frappe.ui.form.on("Transport Order", {
	consolidate: function(frm) {
		// Update vehicle_type required state when consolidate checkbox changes
		frm.events.toggle_vehicle_type_required(frm);
	},
	
	aggregate_volume_from_packages: function(frm) {
		// Aggregate volume and weight from all packages and update header
		// This is called when package volumes or weights change
		if (frm.is_new() || frm.doc.__islocal) return;
		if (!frm.doc.packages || frm.doc.packages.length === 0) {
			return;
		}
		
		// Call server-side method to aggregate volumes and weights with proper UOM conversion
		frm.call({
			method: 'aggregate_volume_from_packages_api',
			doc: frm.doc,
			callback: function(r) {
				// After aggregation, update form values if header fields exist
				if (r && !r.exc && r.message) {
					// Note: Transport Order doesn't have header volume/weight fields currently,
					// but this method is available for future use or API calls
					if (r.message.volume !== undefined && frm.fields_dict.volume) {
						frm.set_value('volume', r.message.volume);
					}
					if (r.message.weight !== undefined && frm.fields_dict.weight) {
						frm.set_value('weight', r.message.weight);
					}
				}
			}
		});
	},

	toggle_vehicle_type_required: function(frm) {
		// Vehicle Type is mandatory only if Consolidate checkbox is not checked
		const is_required = !frm.doc.consolidate;
		frm.set_df_property('vehicle_type', 'reqd', is_required);
	},

	apply_transport_job_type_filters: function(frm, preserve_existing_value) {
		// Show/hide and require container/reefer fields based on transport job type (Vehicle Type filters are in Edit Doctype)
		if (!frm.doc.transport_job_type) {
			return;
		}

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
			if ((frm.doc.reefer) === 1 || (frm.doc.reefer) === true) {
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
						} else if ((frm.doc.reefer) === 1 || (frm.doc.reefer) === true) {
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
								} else if ((frm.doc.reefer) === 1 || (frm.doc.reefer) === true) {
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

// Helper function to create leg plan
function _create_leg_plan(frm) {
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
			if (r.exc) {
				frappe.msgprint({
					title: __("Error"),
					message: r.exc || __("Failed to create leg plan. Please try again."),
					indicator: 'red'
				});
				return;
			}
			if (r.message) {
				if (r.message.error) {
					if (r.message.error === "doc_not_ready") {
						frappe.msgprint({
							title: __("Document Not Ready"),
							message: __("The document is not ready yet. Please wait a moment and try again."),
							indicator: 'orange'
						});
					} else {
						frappe.msgprint({
							title: __("Error"),
							message: r.message.error,
							indicator: 'red'
						});
					}
					return;
				}
				if (r.message.ok) {
					// Reload document to show the new legs
					if (r.message.saved) {
						frm.reload_doc();
					} else {
						frm.refresh();
					}
				}
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to create leg plan. Please try again."),
				indicator: 'red'
			});
		}
	});
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
		// Vehicle Type filters for legs are defined in Edit Doctype (link_filters on Transport Order Legs)
		frm.refresh_field('legs');
	},

	transport_job_type: function(frm, cdt, cdn) {
		// Clear vehicle_type when transport_job_type changes so user picks again (filters are in Edit Doctype)
		var leg = frappe.get_doc(cdt, cdn);
		if (leg.vehicle_type) {
			frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
		}
		frm.refresh_field('legs');
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
	} else if ((frm.doc.reefer) === 1 || (frm.doc.reefer) === true) {
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

// Child table events for Transport Order Package (UOM conversion is in measurements_uom_conversion.js)
frappe.ui.form.on('Transport Order Package', {
	commodity: function(frm, cdt, cdn) {
		// Populate HS code from commodity's default_hs_code
		let row = locals[cdt][cdn];
		if (row.commodity) {
			frappe.db.get_value('Commodity', row.commodity, 'default_hs_code', (r) => {
				if (r && r.default_hs_code) {
					frappe.model.set_value(cdt, cdn, 'hs_code', r.default_hs_code);
				} else {
					// Clear HS code if commodity doesn't have a default HS code
					frappe.model.set_value(cdt, cdn, 'hs_code', '');
				}
			});
		} else {
			// Clear HS code if commodity is cleared
			frappe.model.set_value(cdt, cdn, 'hs_code', '');
		}
	},
	
	// Trigger aggregation when package volume changes
	volume: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		frm.trigger('aggregate_volume_from_packages');
	},
	
	// Trigger aggregation when package weight changes
	weight: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		frm.trigger('aggregate_volume_from_packages');
	},
	
	// Trigger recalculation when weight UOM changes
	weight_uom: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		setTimeout(function() {
			frm.trigger('aggregate_volume_from_packages');
		}, 100);
	},
	
	// Trigger volume calculation and aggregation when dimensions change
	length: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		setTimeout(function() {
			frm.trigger('aggregate_volume_from_packages');
		}, 100);
	},
	
	width: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		setTimeout(function() {
			frm.trigger('aggregate_volume_from_packages');
		}, 100);
	},
	
	height: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		setTimeout(function() {
			frm.trigger('aggregate_volume_from_packages');
		}, 100);
	},
	
	// Trigger recalculation when UOMs change (volume will be recalculated by global handler)
	dimension_uom: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		setTimeout(function() {
			frm.trigger('aggregate_volume_from_packages');
		}, 100);
	},
	
	volume_uom: function(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		setTimeout(function() {
			frm.trigger('aggregate_volume_from_packages');
		}, 100);
	}
});