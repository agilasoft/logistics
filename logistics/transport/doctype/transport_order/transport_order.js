// Cache key for allowed Vehicle Type names (job type + load type + hazardous + reefer)
function vehicle_type_cache_key(transport_job_type, load_type, hazardous, reefer) {
	return (transport_job_type || "") + "|" + (load_type || "") + "|" + (hazardous ? "1" : "0") + "|" + (reefer ? "1" : "0");
}

function invalidate_vehicle_type_cache(frm) {
	frm._allowed_vehicle_types = {};
}

function get_cached_vehicle_type_names(frm, transport_job_type, load_type, hazardous, reefer) {
	var key = vehicle_type_cache_key(transport_job_type, load_type, hazardous, reefer);
	return frm._allowed_vehicle_types && frm._allowed_vehicle_types[key];
}

function load_allowed_vehicle_types(frm, transport_job_type, load_type, callback) {
	var hazardous = frm.doc.contains_dangerous_goods ? 1 : 0;
	var reefer = frm.doc.reefer ? 1 : 0;
	if (!transport_job_type && !load_type) {
		if (callback) callback();
		return;
	}
	var key = vehicle_type_cache_key(transport_job_type, load_type, hazardous, reefer);
	if (frm._allowed_vehicle_types && frm._allowed_vehicle_types[key]) {
		if (callback) callback();
		return;
	}
	frappe.call({
		method: "logistics.transport.doctype.transport_order.transport_order.get_vehicle_types_for_transport_order",
		args: {
			transport_job_type: transport_job_type || null,
			load_type: load_type || null,
			hazardous: hazardous,
			reefer: reefer
		},
		callback: function(r) {
			if (!frm._allowed_vehicle_types) frm._allowed_vehicle_types = {};
			frm._allowed_vehicle_types[key] = (r.message && r.message.vehicle_types) ? r.message.vehicle_types : [];
			if (callback) callback();
		}
	});
}

function reload_allowed_vehicle_types(frm, callback) {
	load_allowed_vehicle_types(
		frm,
		frm.doc.transport_job_type,
		frm.doc.load_type,
		callback
	);
}

function fetch_allowed_vehicle_types_sync(frm, transport_job_type, load_type) {
	var hazardous = frm.doc.contains_dangerous_goods ? 1 : 0;
	var reefer = frm.doc.reefer ? 1 : 0;
	var cached = get_cached_vehicle_type_names(frm, transport_job_type, load_type, hazardous, reefer);
	if (cached) {
		return cached;
	}
	// Never block the UI thread; onload/refresh already preload via reload_allowed_vehicle_types.
	load_allowed_vehicle_types(frm, transport_job_type, load_type);
	return [];
}

function get_vehicle_type_link_filters(frm, transport_job_type, load_type) {
	var filters = {
		is_active: 1,
		hazardous: frm.doc.contains_dangerous_goods ? 1 : 0,
		reefer: frm.doc.reefer ? 1 : 0
	};
	if (!transport_job_type && !load_type) {
		return { filters: Object.assign({ name: ["in", ["__none__"]] }, filters) };
	}

	var names = fetch_allowed_vehicle_types_sync(frm, transport_job_type, load_type);
	filters.name = ["in", names.length ? names : ["__none__"]];
	return { filters: filters };
}

function setup_vehicle_type_get_query(frm) {
	// frm.set_query survives link control init; link_filters on the DocType would overwrite get_query.
	frm.set_query("vehicle_type", function() {
		return get_vehicle_type_link_filters(frm, frm.doc.transport_job_type, frm.doc.load_type);
	});
	frm.set_query("vehicle_type", "legs", function(doc, cdt, cdn) {
		var leg = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : doc;
		var job_type = (leg && leg.transport_job_type) || frm.doc.transport_job_type;
		var lt = (leg && leg.load_type) || frm.doc.load_type;
		return get_vehicle_type_link_filters(frm, job_type, lt);
	});
}

function clear_incompatible_leg_vehicle_types(frm) {
	(frm.doc.legs || []).forEach(function(leg) {
		if (leg.vehicle_type) {
			frappe.model.set_value(leg.doctype, leg.name, 'vehicle_type', '');
		}
	});
}

/** True if this Transport Order form still represents the document the async call was made for (avoids stale callbacks). */
function _transport_order_async_still_for_doc(frm, docname_when_called) {
	if (!frm || frm.doctype !== "Transport Order" || docname_when_called == null) {
		return false;
	}
	return String(frm.doc.name || "") === String(docname_when_called);
}

function _load_milestone_html(frm, opts) {
	opts = opts || {};
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) {
		if (opts.done) opts.done();
		return;
	}
	var _milestone_docname = frm.doc.name;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Transport Order', docname: _milestone_docname },
		callback: function(r) {
			if (!_transport_order_async_still_for_doc(frm, _milestone_docname)) {
				return;
			}
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	}).always(function() {
		if (opts.done) opts.done();
	});
}

function _load_dashboard_html(frm, opts) {
	opts = opts || {};
	if (!frm.fields_dict.dashboard_html || !frm.doc.name || frm.doc.__islocal) {
		if (opts.done) opts.done();
		return;
	}
	var _dashboard_docname = frm.doc.name;
	frappe.call({
		method: 'logistics.transport.doctype.transport_order.transport_order.get_dashboard_html_by_name',
		args: { docname: _dashboard_docname },
		callback: function(r) {
			if (!_transport_order_async_still_for_doc(frm, _dashboard_docname)) {
				return;
			}
			if (r.message && frm.fields_dict.dashboard_html) {
				frm.fields_dict.dashboard_html.$wrapper.html(r.message);
				if (window.logistics_group_and_collapse_dash_alerts) {
					setTimeout(function() {
						window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
					}, 100);
				}
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
				}
			}
		}
	}).always(function() {
		if (opts.done) opts.done();
	});
}

function _bind_transport_order_lazy_tabs(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !window.logistics || !logistics.bind_lazy_tab_loader) {
		return;
	}
	if (frm.doc.modified !== frm._logistics_lazy_modified) {
		logistics.invalidate_lazy_tab_loaders(frm);
		frm._logistics_lazy_modified = frm.doc.modified;
	}
	logistics.bind_lazy_tab_loader(frm, "dashboard_tab", "dashboard", _load_dashboard_html);
	logistics.bind_lazy_tab_loader(frm, "milestones_tab", "milestones", _load_milestone_html, {
		defer_if_active: false,
	});
	if (window.logistics_load_documents_html) {
		logistics.bind_lazy_tab_loader(
			frm,
			"documents_tab",
			"documents",
			function (f, o) {
				window.logistics_load_documents_html(f, "Transport Order", o);
			},
			{ defer_if_active: false }
		);
	}
}

/** Table flags for charges: `cannot_add_rows` / `allow_bulk_edit` may not match client meta; set on the docfield so the grid hides Add / Upload / Download as intended. */
function _logistics_set_charges_cannot_add_rows(frm) {
	if (!frm.get_docfield || !frm.get_docfield("charges")) {
		return;
	}
	frm.set_df_property("charges", "cannot_add_rows", 1);
	frm.set_df_property("charges", "allow_bulk_edit", 0);
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

// Build filter description for Vehicle Type field
function update_vehicle_type_filter_description(frm) {
	if (!frm.fields_dict.vehicle_type) return;
	var parts = [];
	if (frm.doc.transport_job_type) {
		parts.push(__("Job type is {0}", [frm.doc.transport_job_type]));
	}
	if (frm.doc.load_type) {
		parts.push(__("Load type is {0}", [frm.doc.load_type]));
	}
	parts.push(frm.doc.contains_dangerous_goods ? __("Hazardous is enabled") : __("Hazardous is disabled"));
	parts.push(frm.doc.reefer ? __("Reefer is enabled") : __("Reefer is disabled"));
	if (frm.doc.transport_job_type || frm.doc.load_type) {
		var key = vehicle_type_cache_key(
			frm.doc.transport_job_type,
			frm.doc.load_type,
			frm.doc.contains_dangerous_goods,
			frm.doc.reefer
		);
		var names = frm._allowed_vehicle_types && frm._allowed_vehicle_types[key];
		if (names && names.length) {
			var nameList = names.length > 5 ? names.slice(0, 5).join(", ") + "…" : names.join(", ");
			parts.push(__("Name is one of {0}", [nameList]));
		}
	}
	frm.fields_dict.vehicle_type.df.filter_description = __("Filtered by: {0}.", [frappe.utils.comma_and(parts)]);
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

	if (frm._transport_template_allowed_load_types && frm._transport_template_allowed_load_types.length) {
		filters.name = ["in", frm._transport_template_allowed_load_types];
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

function load_transport_template_constraints(frm, callback) {
	if (!frm.doc.transport_template) {
		frm._transport_template_allowed_load_types = [];
		if (callback) callback({});
		return;
	}
	frappe.call({
		method: "logistics.transport.doctype.transport_template.transport_template.get_transport_template_constraints",
		args: { template_name: frm.doc.transport_template },
		callback: function(r) {
			var constraints = (r && r.message) || {};
			frm._transport_template_allowed_load_types = constraints.allowed_load_types || [];
			if (callback) callback(constraints);
		},
	});
}

function apply_transport_template_defaults_to_order(frm, constraints) {
	constraints = constraints || {};
	var allowed = constraints.allowed_load_types || [];
	if (frm.doc.load_type && allowed.length && allowed.indexOf(frm.doc.load_type) === -1) {
		frm.set_value("load_type", "");
	}
	if (!frm.doc.load_type && constraints.default_load_type) {
		frm.set_value("load_type", constraints.default_load_type);
	}
	if (!frm.doc.vehicle_type && constraints.default_vehicle_type) {
		frm.set_value("vehicle_type", constraints.default_vehicle_type);
	}
	apply_load_type_filters(frm);
	reload_allowed_vehicle_types(frm, function() {
		frm.refresh_field("vehicle_type");
	});
}

frappe.ui.form.on("Transport Order", {
	setup: function(frm) {
		frm.set_query('milestone_template', function() {
			return frappe.call('logistics.document_management.api.get_milestone_template_filters', { doctype: frm.doctype })
				.then(function(r) { return r.message || { filters: [] }; });
		});
		frm.set_query('warehouse_item', 'packages', function() {
			var filters = {};
			if (frm.doc.customer) {
				filters.customer = frm.doc.customer;
			}
			return { filters: filters };
		});
		frm._allowed_vehicle_types = {};
		// Apply load_type filters before field is ever used
		apply_load_type_filters(frm);
		if (logistics.party_address_contact) {
			logistics.party_address_contact.setup_queries(frm);
		}
	},

	shipper(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_shipper_change(frm);
		} else if (logistics.party_defaults) {
			logistics.party_defaults.apply(frm);
		}
	},

	consignee(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_consignee_change(frm);
		} else if (logistics.party_defaults) {
			logistics.party_defaults.apply(frm);
		}
	},

	shipper_address(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_shipper_address_change(frm);
		}
	},

	consignee_address(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_consignee_address_change(frm);
		}
	},

	shipper_contact(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_shipper_contact_change(frm);
		}
	},

	consignee_contact(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_consignee_contact_change(frm);
		}
	},

	onload: function(frm) {
		if (window.logistics && logistics.apply_one_off_route_options_onload) {
			logistics.apply_one_off_route_options_onload(frm);
		}
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
		if (frm.doc.transport_template) {
			load_transport_template_constraints(frm, function(constraints) {
				apply_load_type_filters(frm, !frm.is_new());
				if (frm.is_new()) {
					apply_transport_template_defaults_to_order(frm, constraints);
				}
			});
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

		setup_vehicle_type_get_query(frm);

		update_vehicle_type_filter_description(frm);
		if (frm.doc.transport_job_type || frm.doc.load_type) {
			reload_allowed_vehicle_types(frm, function() {
				update_vehicle_type_filter_description(frm);
				frm.refresh_field('vehicle_type');
			});
		}

		if (frm.fields_dict.legs && frm.fields_dict.legs.grid) {
			// Set pick_address and drop_address query filters for legs grid using frm.set_query
			// so the callback receives (doc, cdt, cdn) and we filter by that row's Facility From/To
			frm.set_query('pick_address', 'legs', function(doc, cdt, cdn) {
				return get_address_query_for_leg(frm, doc, cdt, cdn, 'pick');
			});
			frm.set_query('drop_address', 'legs', function(doc, cdt, cdn) {
				return get_address_query_for_leg(frm, doc, cdt, cdn, 'drop');
			});
		}
		
		_logistics_set_charges_cannot_add_rows(frm);
	},

	refresh: function(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.populate_displays_if_missing(frm);
		}
		if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
			logistics.apply_one_off_sales_quote_order_standard(frm);
		}
		_logistics_set_charges_cannot_add_rows(frm);
		if (window.logistics && logistics.add_get_charges_from_quotation_button_if_allowed) {
			logistics.add_get_charges_from_quotation_button_if_allowed(frm);
		}
		setTimeout(function () {
			if (window.logistics_hide_cannot_add_rows_buttons) {
				window.logistics_hide_cannot_add_rows_buttons(frm, "charges");
			}
		}, 0);
		// Lazy-load tab HTML (dashboard deferred if active; others on tab click)
		_bind_transport_order_lazy_tabs(frm);

		// Populate Documents from Template
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__('Get Documents'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_documents_from_template',
					args: { doctype: 'Transport Order', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Action'));
		}

		// Get Milestones (populate from template)
		if (!frm.doc.__islocal && frm.fields_dict.milestones) {
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Transport Order', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Action'));
		}

		// Recalculate Charges
		if (!frm.is_new() && frm.doc.charges && frm.doc.charges.length > 0) {
			frm.add_custom_button(__('Calculate Charges'), function() {
				frappe.call({
					method: 'logistics.transport.doctype.transport_order.transport_order.recalculate_all_charges',
					args: { docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'green' }, 3);
						}
					}
				});
			}, __('Action'));
		}

		// Dashboard HTML is loaded lazily via _bind_transport_order_lazy_tabs

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
		
		// Event charges populated message after reload (from sales_quote change)
		if (frappe.route_options && frappe.route_options.__event_charges_message) {
			var msg_info = frappe.route_options.__event_charges_message;
			frappe.msgprint({
				title: __("Charges Updated"),
				message: __("Successfully populated {0} charges from Sales Quote: {1}", [msg_info.count, msg_info.sales_quote]),
				indicator: 'green'
			});
			// Clear the route option to avoid showing on subsequent refreshes
			delete frappe.route_options.__event_charges_message;
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
			}, __("Action"));
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
			}, __('Action'));
			
			// Event order status indicator if order exists
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
					}, __("Action"));
					// Event indicator that Transport Job exists
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
											var job_frm = typeof cur_frm !== "undefined" ? cur_frm : null;
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
											var job_frm = typeof cur_frm !== "undefined" ? cur_frm : null;
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

		setup_vehicle_type_get_query(frm);
		update_vehicle_type_filter_description(frm);
		if (frm.doc.transport_job_type || frm.doc.load_type) {
			reload_allowed_vehicle_types(frm, function() {
				update_vehicle_type_filter_description(frm);
			});
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
		invalidate_vehicle_type_cache(frm);
		update_vehicle_type_filter_description(frm);
		if (!frm.doc.transport_job_type && !frm.doc.load_type) {
			frm.refresh_field('vehicle_type');
			frm.refresh_field('legs');
			return;
		}
		reload_allowed_vehicle_types(frm, function() {
			update_vehicle_type_filter_description(frm);
			frm.refresh_field('vehicle_type');
			frm.refresh_field('legs');
		});
	},

	transport_template: function(frm) {
		load_transport_template_constraints(frm, function(constraints) {
			apply_transport_template_defaults_to_order(frm, constraints);
		});
	},

	transport_job_type: function(frm) {
		frm.events.apply_transport_job_type_filters(frm);
		populate_legs_transport_job_type_from_parent(frm);
		apply_load_type_filters(frm);
		frm.set_value('load_type', null);
		invalidate_vehicle_type_cache(frm);
		if (frm.doc.vehicle_type) {
			frm.set_value('vehicle_type', '');
		}
		clear_incompatible_leg_vehicle_types(frm);
		reload_allowed_vehicle_types(frm, function() {
			update_vehicle_type_filter_description(frm);
			frm.refresh_field('vehicle_type');
			frm.refresh_field('legs');
		});
	},

	contains_dangerous_goods: function(frm) {
		invalidate_vehicle_type_cache(frm);
		update_vehicle_type_filter_description(frm);
		if (frm.doc.transport_job_type || frm.doc.load_type) {
			reload_allowed_vehicle_types(frm, function() {
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
		invalidate_vehicle_type_cache(frm);
		update_vehicle_type_filter_description(frm);
		if (frm.doc.transport_job_type || frm.doc.load_type) {
			reload_allowed_vehicle_types(frm, function() {
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
		if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
			logistics.apply_one_off_sales_quote_order_standard(frm);
		}
		// Sales Quote is read-only; use Action → Get Charges from Quotation.
	}
});

function _warn_if_missing_service_charges(frm, service_type) {
	var charges = frm.doc.charges || [];
	var has_match = charges.some(function(row) {
		return (row.service_type || '').trim() === service_type;
	});
	if (!has_match) {
		frappe.msgprint({
			title: __("Charges Warning"),
			message: __("No {0} charges found yet. You can continue in draft, but submit will be blocked.", [service_type]),
			indicator: "orange"
		});
	}
}

function _recalculate_transport_order_charge_rows(frm, done) {
	var charges = frm.doc.charges || [];
	if (!charges.length) {
		if (done) {
			done();
		}
		return;
	}
	var idx = 0;
	function run_next() {
		if (idx >= charges.length) {
			frm.refresh_field("charges");
			if (done) {
				done();
			}
			return;
		}
		var row = charges[idx];
		idx += 1;
		frappe.call({
			method: "logistics.utils.charges_calculation.calculate_charge_row",
			args: {
				doctype: "Transport Order Charges",
				parenttype: "Transport Order",
				parent: frm.doc.name || "new",
				row_data: JSON.stringify(row),
				parent_overrides:
					window.logistics && logistics.charge_row_parent_overrides
						? logistics.charge_row_parent_overrides(frm)
						: null,
			},
			callback: function(r) {
				if (r.message && r.message.success && row.name) {
					if (r.message.estimated_revenue != null) {
						frappe.model.set_value("Transport Order Charges", row.name, "estimated_revenue", r.message.estimated_revenue);
					}
					if (r.message.estimated_cost != null) {
						frappe.model.set_value("Transport Order Charges", row.name, "estimated_cost", r.message.estimated_cost);
					}
					if (r.message.quantity != null) {
						frappe.model.set_value("Transport Order Charges", row.name, "quantity", r.message.quantity);
					}
					if (r.message.cost_quantity != null) {
						frappe.model.set_value("Transport Order Charges", row.name, "cost_quantity", r.message.cost_quantity);
					}
					if ("revenue_calc_notes" in r.message) {
						frappe.model.set_value("Transport Order Charges", row.name, "revenue_calc_notes", r.message.revenue_calc_notes || "");
					}
					if ("cost_calc_notes" in r.message) {
						frappe.model.set_value("Transport Order Charges", row.name, "cost_calc_notes", r.message.cost_calc_notes || "");
					}
					if (window.logistics && logistics.charges_disbursement && logistics.charges_disbursement.apply_charge_row_response) {
						logistics.charges_disbursement.apply_charge_row_response("Transport Order Charges", row.name, r);
					}
				}
				run_next();
			},
			error: function() {
				run_next();
			},
		});
	}
	run_next();
}

function _populate_charges_from_sales_quote(frm) {
	var docname = frm.is_new() ? null : frm.doc.name;
	var sales_quote = frm.doc.sales_quote;
	var ij = (frm.doc.service_role === "Linked" || frm.doc.is_internal_job) ? 1 : 0;
	var mjt = frm.doc.main_service_type || frm.doc.main_job_type;
	var mj = frm.doc.main_job;

	if (!sales_quote) {
		frm.clear_table('charges');
		frm.refresh_field('charges');
		return;
	}
	// Skip when sales_quote is a temporary name (unsaved document)
	if (String(sales_quote).startsWith('new-')) {
		frappe.msgprint({
			title: __("Save Required"),
			message: __("Please save the Sales Quote first before selecting it here."),
			indicator: 'orange'
		});
		return;
	}

	frappe.call({
		method: "logistics.transport.doctype.transport_order.transport_order.populate_charges_from_sales_quote",
		args: {
			docname: docname,
			sales_quote: sales_quote,
			is_internal_job: ij,
			main_job_type: mjt,
			main_job: mj
		},
		freeze: true,
		freeze_message: __("Fetching charges from Sales Quote..."),
		callback: function(r) {
			if (r.message) {
				if (!frm.doc.customer && r.message.customer) {
					frm.set_value('customer', r.message.customer);
				}
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
					_recalculate_transport_order_charge_rows(frm, function() {
						if (r.message.charges_count > 0) {
							frappe.msgprint({
								title: __("Charges Updated"),
								message: __("Successfully populated {0} charges from Sales Quote: {1}", [r.message.charges_count, sales_quote]),
								indicator: 'green'
							});
						}
						if (window.logistics && logistics.apply_sales_quote_linked_services_after_fetch) {
							logistics.apply_sales_quote_linked_services_after_fetch(frm, sales_quote);
						}
					});
					_warn_if_missing_service_charges(frm, "Transport");
				} else {
					frm.clear_table('charges');
					frm.refresh_field('charges');
					if (!_transport_internal_job_dialog_handled(frm, sales_quote)) {
						frm._internal_job_dialog_shown_for_quote = frm._internal_job_dialog_shown_for_quote || {};
						frm._internal_job_dialog_shown_for_quote[sales_quote] = true;
						frappe.msgprint({
							title: __("Cannot create internal job"),
							message: __(
								"Add charge lines for this service on the Sales Quote and define a matching Internal Job on the Internal Jobs tab before creating."
							),
							indicator: "orange"
						});
					}
					_warn_if_missing_service_charges(frm, "Transport");
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

function _transport_internal_job_dialog_handled(frm, sales_quote) {
	if (!frm._internal_job_dialog_shown_for_quote) {
		frm._internal_job_dialog_shown_for_quote = {};
	}
	return !!frm._internal_job_dialog_shown_for_quote[sales_quote];
}

function _prompt_internal_transport_job_dialog(frm, sales_quote) {
	if (!_transport_internal_job_dialog_handled(frm, sales_quote)) {
		frm._internal_job_dialog_shown_for_quote[sales_quote] = true;
	}

	frappe.db.get_doc("Sales Quote", sales_quote).then(function(sq) {
		var defaults = {
			company: frm.doc.company || sq.company || "",
			branch: frm.doc.branch || sq.branch || "",
			cost_center: frm.doc.cost_center || sq.cost_center || "",
			profit_center: frm.doc.profit_center || sq.profit_center || "",
			location_type: frm.doc.location_type || sq.location_type || "UNLOCO",
			location_from: frm.doc.location_from || sq.location_from || sq.origin_port || "",
			location_to: frm.doc.location_to || sq.location_to || sq.destination_port || "",
			scheduled_date: frm.doc.scheduled_date || frappe.datetime.get_today()
		};

		var dialog = new frappe.ui.Dialog({
			title: __("Create Internal Job - Transport"),
			fields: [
				{ fieldtype: "HTML", fieldname: "context_html" },
				{ fieldtype: "Section Break", label: __("Internal Job Setup") },
				{ fieldtype: "Check", fieldname: "is_internal_job", label: __("Linked Service"), default: 1, read_only: 1 },
				{ fieldtype: "Link", fieldname: "main_job_type", label: __("Main Service Type"), options: "DocType", reqd: 1, default: frm.doc.main_service_type || frm.doc.main_job_type || "" },
				{
					fieldtype: "Dynamic Link",
					fieldname: "main_job",
					label: __("Main Service"),
					options: "main_job_type",
					reqd: 1,
					default: frm.doc.main_service || frm.doc.main_job || ""
				},
				{ fieldtype: "Section Break", label: __("Defaults") },
				{ fieldtype: "Link", fieldname: "company", label: __("Company"), options: "Company", default: defaults.company },
				{ fieldtype: "Link", fieldname: "branch", label: __("Branch"), options: "Branch", default: defaults.branch },
				{ fieldtype: "Link", fieldname: "cost_center", label: __("Cost Center"), options: "Cost Center", default: defaults.cost_center },
				{ fieldtype: "Link", fieldname: "profit_center", label: __("Profit Center"), options: "Profit Center", default: defaults.profit_center },
				{ fieldtype: "Section Break", label: __("Required Additional Details") },
				{ fieldtype: "Select", fieldname: "location_type", label: __("Location Type"), options: "\nUNLOCO\nAddress\nEconomic Zone", reqd: 1, default: defaults.location_type },
				{ fieldtype: "Dynamic Link", fieldname: "location_from", label: __("Location From"), options: "location_type", reqd: 1, default: defaults.location_from },
				{ fieldtype: "Dynamic Link", fieldname: "location_to", label: __("Location To"), options: "location_type", reqd: 1, default: defaults.location_to },
				{ fieldtype: "Date", fieldname: "scheduled_date", label: __("Scheduled Date"), reqd: 1, default: defaults.scheduled_date }
			],
			primary_action_label: __("Create Internal Job"),
			primary_action: function(values) {
				frm.set_value("service_role", "Linked");
				frm.set_value("main_service_type", values.main_job_type || values.main_service_type);
				if (frm.get_docfield("main_job_type")) { frm.set_value("main_job_type", values.main_job_type || values.main_service_type); }
				frm.set_value("main_service", values.main_job || values.main_service);
				if (frm.get_docfield("main_job")) { frm.set_value("main_job", values.main_job || values.main_service); }
				frm.set_value("company", values.company || frm.doc.company);
				frm.set_value("branch", values.branch || "");
				frm.set_value("cost_center", values.cost_center || "");
				frm.set_value("profit_center", values.profit_center || "");
				frm.set_value("location_type", values.location_type);
				frm.set_value("location_from", values.location_from);
				frm.set_value("location_to", values.location_to);
				frm.set_value("scheduled_date", values.scheduled_date);
				dialog.hide();
				_populate_charges_from_sales_quote(frm);
			}
		});

		dialog.fields_dict.context_html.$wrapper.html(
			'<div class="text-muted">' +
			__("No Transport charges were found on Sales Quote <b>{0}</b>. This will be created as an Internal Job linked to a Main Job.", [sales_quote]) +
			"</div>"
		);
		dialog.show();
	}).catch(function() {
		// Ignore prefill failures; keep default no-charges behavior.
	});
}

frappe.ui.form.on("Transport Order", {
	document_list_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_documents_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				}
			});
		});
	},
	milestone_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_milestones_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				}
			});
		});
	},
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

		var _aggregate_docname = frm.doc.name;
		// frappe.call + remote helper (not frm.call): avoids run_doc_method / TimestampMismatchError
		// when this runs right after save while modified timestamp is updating.
		frappe.call({
			method: 'logistics.transport.doctype.transport_order.transport_order.aggregate_volume_from_packages_remote',
			args: { doc: frm.doc },
			callback: function(r) {
				if (!_transport_order_async_still_for_doc(frm, _aggregate_docname)) {
					return;
				}
				if (r && !r.exc && r.message) {
					if (r.message.total_volume !== undefined && frm.fields_dict.total_volume) {
						frm.set_value('total_volume', r.message.total_volume);
					}
					if (r.message.total_weight !== undefined && frm.fields_dict.total_weight) {
						frm.set_value('total_weight', r.message.total_weight);
					}
					if (r.message.total_packages !== undefined && frm.fields_dict.total_packages) {
						frm.set_value('total_packages', r.message.total_packages);
					}
				}
			}
		});
	},
	after_save(frm) {
		var new_name = frappe.model.new_names && frappe.model.new_names[frm.doc.name];
		if (new_name) {
			frm.docname = new_name;
			frm.doc = (locals[frm.doctype] && locals[frm.doctype][new_name])
				? locals[frm.doctype][new_name]
				: frappe.get_doc(frm.doctype, new_name);
		}
	},

	toggle_vehicle_type_required: function(frm) {
		// Vehicle Type is mandatory only if Consolidate checkbox is not checked
		const is_required = !frm.doc.consolidate;
		frm.set_df_property('vehicle_type', 'reqd', is_required);
	},

	apply_transport_job_type_filters: function(frm, preserve_existing_value) {
		// Show/hide and require container fields based on transport job type
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

		// Validate leg facilities/addresses (mirrors server before_submit _validate_leg_facilities)
		if (frm.doc.legs && frm.doc.legs.length > 0) {
			for (var i = 0; i < frm.doc.legs.length; i++) {
				var leg = frm.doc.legs[i];
				var row_num = leg.idx || (i + 1);
				if (leg.facility_from && leg.facility_to && leg.facility_from === leg.facility_to) {
					if (leg.pick_address === leg.drop_address) {
						var facility_msg = __("Row {0}: Pick facility and drop facility cannot be the same.", [row_num]);
						frappe.msgprint({
							title: __("Validation Error"),
							message: facility_msg,
							indicator: 'red'
						});
						return Promise.reject(facility_msg);
					}
				} else if (leg.pick_address && leg.drop_address && leg.pick_address === leg.drop_address) {
					var address_msg = __("Row {0}: Pick address and drop address cannot be the same.", [row_num]);
					frappe.msgprint({
						title: __("Validation Error"),
						message: address_msg,
						indicator: 'red'
					});
					return Promise.reject(address_msg);
				}
			}
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

	var legIdx = (leg && leg.idx != null) ? leg.idx : '';
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
					message: __("Leg {0}: {1}", [legIdx, r.message.message]),
					indicator: 'orange'
				});
				// Re-fetch row (may be gone after async); guard before using
				var current = frappe.get_doc(cdt, cdn);
				if (current && current.vehicle_type) {
					frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
				}
			}
		}
	});
}

function _transport_order_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, grid_row, 'packages');
}

frappe.ui.form.on('Transport Order', {
	packages_on_form_rendered: function(frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(frm, 'Transport Order Package', 'packages', 'transport_order_volume');
		}
	}
});

// Child table events for Transport Order Package (UOM conversion is in measurements_uom_conversion.js)
frappe.ui.form.on('Transport Order Package', {
	form_render: function(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger('packages_on_form_rendered');
		setTimeout(function() {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === 'function') fn_immediate(frm, cdt, cdn);
			else if (typeof fn_debounced === 'function') fn_debounced(frm, cdt, cdn);
			else _transport_order_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		}, 50);
	},
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
	
	length: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_order_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function() { frm.trigger('aggregate_volume_from_packages'); }, 100);
		}
	},
	width: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_order_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function() { frm.trigger('aggregate_volume_from_packages'); }, 100);
		}
	},
	height: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_order_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function() { frm.trigger('aggregate_volume_from_packages'); }, 100);
		}
	},
	dimension_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_order_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function() { frm.trigger('aggregate_volume_from_packages'); }, 100);
		}
	},
	volume_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_order_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function() { frm.trigger('aggregate_volume_from_packages'); }, 100);
		}
	}
});

// Duplicate / Copy must not carry pricing linkage or charge lines (desk uses frappe.model.copy_doc;
// server-side copy_doc may ignore no_copy — this keeps the duplicated draft clean regardless).
(function () {
	if (frappe.model._logistics_transport_order_copy_doc_patched) {
		return;
	}
	frappe.model._logistics_transport_order_copy_doc_patched = 1;
	var _origCopyDoc = frappe.model.copy_doc;
	frappe.model.copy_doc = function (doc, from_amend, parent_doc, parentfield) {
		var newdoc = _origCopyDoc.apply(this, arguments);
		if (
			from_amend ||
			parent_doc ||
			!doc ||
			!newdoc ||
			doc.doctype !== "Transport Order" ||
			newdoc.doctype !== "Transport Order"
		) {
			return newdoc;
		}
		if (newdoc.charges && newdoc.charges.length) {
			frappe.model.clear_table(newdoc, "charges");
		} else {
			newdoc.charges = [];
		}
		newdoc.sales_quote = null;
		if (frappe.meta.has_field("Transport Order", "quote")) {
			newdoc.quote = null;
		}
		if (frappe.meta.has_field("Transport Order", "quote_type")) {
			newdoc.quote_type = null;
		}
		newdoc.logistics_duplicate_from = doc.name || "";
		return newdoc;
	};
})();