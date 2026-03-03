// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Quote", {
	setup(frm) {
		// Initialize cache for allowed vehicle types
		frm.allowed_vehicle_types_cache = {};
	},
	
	onload(frm) {
		frm.events.setup_vehicle_type_query(frm);
		// Preload vehicle types cache for load_types present in transport table
		if (frm.doc.transport && frm.doc.transport.length) {
			const load_types = [...new Set(frm.doc.transport.map(r => r.load_type).filter(Boolean))];
			load_types.forEach(lt => frm.events.load_allowed_vehicle_types(frm, lt));
		}
		// Default UOMs from Settings per tab when fields are empty (for any visible tab)
		if (frm.is_new()) {
			frm.events.apply_default_uoms_per_tab(frm);
			// Clear converted_to and status when duplicating
			if (frm.doc.converted_to) {
				frm.set_value("converted_to", "");
			}
			if (frm.doc.status) {
				frm.set_value("status", "");
			}
		}
		
		// Listen to form dirty state changes to update primary button
		$(frm.wrapper).on("dirty", function() {
			frm.events.update_primary_button(frm);
		});
		
		// Listen to form clean state (when form becomes not dirty) to update primary button
		$(frm.wrapper).on("clean", function() {
			frm.events.update_primary_button(frm);
		});
	},

	quotation_type(frm) {
		if (frm.doc.quotation_type === "One-off" && frm.is_new()) {
			frm.set_value("naming_series", "OOQ-.#####");
		} else if (frm.doc.quotation_type === "Project" && frm.is_new()) {
			frm.set_value("naming_series", "PQ-.#####");
			frm.set_value("is_multimodal", 1);
		} else if (frm.doc.quotation_type === "Regular" && frm.is_new()) {
			frm.set_value("naming_series", "SQU.#########");
		}
		frm.refresh_field("naming_series");
		frm.refresh_field("status_section");
		frm.refresh_field("status");
		frm.refresh_field("converted_to_doc");
		frm.refresh_field("projects_tab");
		frm.events._set_child_param_readonly(frm);
		frm.refresh_field("sea_freight");
		frm.refresh_field("air_freight");
		frm.refresh_field("transport");
	},

	_set_child_param_readonly(frm) {
		const isOneOff = frm.doc.quotation_type === "One-off";
		const seaParams = ["sea_load_type", "sea_direction", "shipping_line", "freight_agent", "sea_transport_mode", "sea_house_type", "sea_release_type", "sea_entry_type", "origin_port", "destination_port"];
		const airParams = ["air_load_type", "air_direction", "airline", "freight_agent", "air_house_type", "air_release_type", "air_entry_type", "origin_port", "destination_port"];
		const transportParams = ["load_type", "transport_template", "vehicle_type", "container_type", "location_type", "location_from", "location_to", "pick_mode", "drop_mode"];
		if (frm.fields_dict.sea_freight) {
			seaParams.forEach(function(f) {
				frm.set_df_property("sea_freight", f, "read_only", isOneOff);
			});
		}
		if (frm.fields_dict.air_freight) {
			airParams.forEach(function(f) {
				frm.set_df_property("air_freight", f, "read_only", isOneOff);
			});
		}
		if (frm.fields_dict.transport) {
			transportParams.forEach(function(f) {
				frm.set_df_property("transport", f, "read_only", isOneOff);
			});
		}
	},

	sea_freight_add(frm) {
		if (frm.doc.quotation_type === "One-off" && frm.doc.is_sea) {
			frm.events._default_sea_row_from_header(frm);
		}
	},
	air_freight_add(frm) {
		if (frm.doc.quotation_type === "One-off" && frm.doc.is_air) {
			frm.events._default_air_row_from_header(frm);
		}
	},
	transport_add(frm) {
		if (frm.doc.quotation_type === "One-off" && frm.doc.is_transport) {
			frm.events._default_transport_row_from_header(frm);
		}
	},
	is_sea(frm) {
		if (frm.doc.is_sea) {
			frm.events.apply_default_uoms_for_tab(frm, "sea", "sea_");
		}
	},
	is_air(frm) {
		if (frm.doc.is_air) {
			frm.events.apply_default_uoms_for_tab(frm, "air", "air_");
		}
	},
	is_transport(frm) {
		if (frm.doc.is_transport) {
			frm.events.apply_default_uoms_for_tab(frm, "transport", "transport_");
		}
	},
	is_warehousing(frm) {
		if (frm.doc.is_warehousing) {
			frm.events.apply_default_uoms_for_tab(frm, "warehousing", "warehouse_");
		}
	},

	routing_legs_add(frm, cdt, cdn) {
		// Leg order is determined by child table idx (no separate Leg field).
	},

	_default_sea_row_from_header(frm) {
		const rows = frm.doc.sea_freight || [];
		if (rows.length === 0) return;
		const row = rows[rows.length - 1];
		const map = {
			sea_load_type: frm.doc.sea_load_type,
			sea_direction: frm.doc.sea_direction,
			sea_transport_mode: frm.doc.sea_transport_mode,
			shipping_line: frm.doc.shipping_line,
			freight_agent: frm.doc.freight_agent_sea,
			sea_house_type: frm.doc.sea_house_type,
			origin_port: frm.doc.origin_port_sea,
			destination_port: frm.doc.destination_port_sea
		};
		Object.keys(map).forEach(function(k) {
			if (map[k] != null && map[k] !== "") {
				row[k] = map[k];
			}
		});
		frm.refresh_field("sea_freight");
	},
	_default_air_row_from_header(frm) {
		const rows = frm.doc.air_freight || [];
		if (rows.length === 0) return;
		const row = rows[rows.length - 1];
		const map = {
			air_load_type: frm.doc.air_load_type,
			air_direction: frm.doc.air_direction,
			airline: frm.doc.airline,
			freight_agent: frm.doc.freight_agent,
			air_house_type: frm.doc.air_house_type,
			origin_port: frm.doc.origin_port,
			destination_port: frm.doc.destination_port
		};
		Object.keys(map).forEach(function(k) {
			if (map[k] != null && map[k] !== "") {
				row[k] = map[k];
			}
		});
		frm.refresh_field("air_freight");
	},
	_default_transport_row_from_header(frm) {
		const rows = frm.doc.transport || [];
		if (rows.length === 0) return;
		const row = rows[rows.length - 1];
		const map = {
			transport_template: frm.doc.transport_template,
			load_type: frm.doc.load_type,
			vehicle_type: frm.doc.vehicle_type,
			container_type: frm.doc.container_type,
			location_type: frm.doc.location_type,
			location_from: frm.doc.location_from,
			location_to: frm.doc.location_to,
			pick_mode: frm.doc.pick_mode,
			drop_mode: frm.doc.drop_mode
		};
		Object.keys(map).forEach(function(k) {
			if (map[k] != null && map[k] !== "") {
				row[k] = map[k];
			}
		});
		frm.refresh_field("transport");
	},
	
	refresh(frm) {
		// Delegated click handler for Weight/Qty Break buttons (bypasses form event system if needed)
		$(frm.wrapper).off("click.break_buttons").on("click.break_buttons", function (e) {
			const $ctrl = $(e.target).closest(
				'[data-fieldname="selling_weight_break"], [data-fieldname="cost_weight_break"], ' +
				'[data-fieldname="selling_qty_break"], [data-fieldname="cost_qty_break"]'
			);
			if (!$ctrl.length) return;
			const fieldname = $ctrl.attr("data-fieldname");
			const $row = $ctrl.closest(".grid-row");
			if (!$row.length) return;
			let row_doc = $row.data("doc");
			const grid_row = $row.data("grid_row");
			if (grid_row && grid_row.doc) row_doc = grid_row.doc;
			// Fallback: resolve row from grid by docname (data can be stale on wrapper)
			if (!row_doc || !row_doc.doctype) {
				const docname = $row.attr("data-name");
				if (docname && frm.fields_dict) {
					for (const fn of Object.keys(frm.fields_dict)) {
						const grid = frm.fields_dict[fn]?.grid;
						if (grid?.grid_rows_by_docname?.[docname]) {
							row_doc = grid.grid_rows_by_docname[docname].doc;
							break;
						}
					}
				}
			}
			if (!row_doc || !row_doc.doctype) {
				row_doc = frm.selected_doc;
			}
			if (!row_doc || !row_doc.doctype) return;
			e.preventDefault();
			e.stopPropagation();
			const record_type = fieldname.indexOf("cost_") === 0 ? "Cost" : "Selling";
			if (fieldname.indexOf("weight_break") !== -1 && typeof window.open_weight_break_rate_dialog === "function") {
				window.open_weight_break_rate_dialog(frm, row_doc, record_type);
			} else if (fieldname.indexOf("qty_break") !== -1 && typeof window.open_qty_break_rate_dialog === "function") {
				window.open_qty_break_rate_dialog(frm, row_doc, record_type);
			} else {
				frappe.msgprint({ title: __("Error"), message: __("Dialog not loaded. Please refresh the page."), indicator: "red" });
			}
		});
		frm.events._set_child_param_readonly(frm);
		// Update primary button state
		// Use setTimeout to ensure form state is fully updated after refresh
		setTimeout(function() {
			frm.events.update_primary_button(frm);
		}, 50);
		
		// Apply default UOMs from Settings when UOM fields are empty (only for new docs)
		if (frm.is_new()) {
			frm.events.apply_default_uoms_per_tab(frm);
		}
		// Preload vehicle types cache for load_types in transport table
		if (frm.doc.transport && frm.doc.transport.length) {
			const load_types = [...new Set(frm.doc.transport.map(r => r.load_type).filter(Boolean))];
			load_types.forEach(lt => frm.events.load_allowed_vehicle_types(frm, lt));
		}
		frm.events.setup_vehicle_type_query(frm);
		
		// Add custom button to create Transport Order if is_transport = 1
		add_create_button(frm, {
			doctype: "Transport Order",
			flag_field: "is_transport",
			create_label: "Create Transport Order",
			view_label: "View Transport Orders",
			create_function: create_transport_order_from_sales_quote
		});
		
		// Add custom button to create Warehouse Contract if quote is submitted and has warehousing items
		if (frm.doc.docstatus === 1 && frm.doc.warehousing && frm.doc.warehousing.length > 0 && !frm.doc.__islocal) {
			frm.add_custom_button(__("Create Warehouse Contract"), function() {
				create_warehouse_contract_from_sales_quote(frm);
			}, __("Create"));
			
			// Also add a button to view existing Warehouse Contracts if any exist
			frappe.db.get_value("Warehouse Contract", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (r && r.name) {
					frm.add_custom_button(__("View Warehouse Contracts"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Warehouse Contract");
					}, __("Actions"));
				}
			});
		}
		
		// Add custom button to create Declaration if quote is One-Off and submitted
		if (frm.doc.quotation_type === "One-off" && frm.doc.customs && frm.doc.customs.length > 0 && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			// Check if Declaration already exists - restrict multiple orders for one-off quotes
			frappe.db.get_value("Declaration", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (!r || !r.name) {
					// No existing Declaration - show create button
					frm.add_custom_button(__("Create Declaration"), function() {
						create_declaration_from_sales_quote(frm);
					}, __("Create"));
				} else {
					// Declaration exists - only show view button
					frm.add_custom_button(__("View Declarations"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Declaration");
					}, __("Actions"));
				}
			});
		}
		
		// Add custom button to create Air Booking if is_air = 1
		add_create_button(frm, {
			doctype: "Air Booking",
			flag_field: "is_air",
			create_label: "Create Air Booking",
			view_label: "View Air Bookings",
			create_function: create_air_booking_from_sales_quote
		});
		
		// Add custom button to create Sea Booking if is_sea = 1
		add_create_button(frm, {
			doctype: "Sea Booking",
			flag_field: "is_sea",
			create_label: "Create Sea Booking",
			view_label: "View Sea Bookings",
			create_function: create_sea_booking_from_sales_quote
		});

		// Add custom button to create Sales Invoice from multimodal quote (when routing legs exist and Main Job has job_no)
		if (frm.doc.is_multimodal && frm.doc.routing_legs && frm.doc.routing_legs.length > 0 && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			const main_leg = frm.doc.routing_legs.find(r => r.is_main_job);
			const has_main_job = main_leg && main_leg.job_no;
			if (has_main_job) {
				frm.add_custom_button(__("Create Sales Invoice"), function() {
					create_sales_invoice_from_sales_quote(frm);
				}, __("Post"));
			}
		}
	},
	
	after_save(frm) {
		// Update primary button after save to show Submit button if document is saved and not dirty
		// Clear the __unsaved flag immediately to ensure form is considered clean
		if (frm.doc) {
			frm.doc.__unsaved = 0;
		}
		
		// Use multiple timeouts to ensure form state is fully updated after save and refresh
		// First update after a short delay
		setTimeout(function() {
			if (frm.doc) {
				frm.doc.__unsaved = 0;
			}
			frm.events.update_primary_button(frm);
		}, 100);
		
		// Also update after refresh completes (longer delay)
		setTimeout(function() {
			if (frm.doc) {
				frm.doc.__unsaved = 0;
			}
			frm.events.update_primary_button(frm);
		}, 500);
	},
	
	load_allowed_vehicle_types(frm, load_type, callback) {
		// Load allowed vehicle types for the given load_type and cache them
		if (!load_type) {
			if (callback) callback();
			return;
		}
		
		// Ensure cache is initialized
		if (!frm.allowed_vehicle_types_cache) {
			frm.allowed_vehicle_types_cache = {};
		}
		
		// Check cache first
		if (frm.allowed_vehicle_types_cache[load_type]) {
			if (callback) callback();
			return;
		}
		
		// Load from server
		frappe.call({
			method: "logistics.pricing_center.doctype.sales_quote.sales_quote.get_vehicle_types_for_load_type",
			args: {
				load_type: load_type
			},
			callback: function(r) {
				// Ensure cache is still initialized (defensive check)
				if (!frm.allowed_vehicle_types_cache) {
					frm.allowed_vehicle_types_cache = {};
				}
				if (r.message && r.message.vehicle_types) {
					frm.allowed_vehicle_types_cache[load_type] = r.message.vehicle_types;
				} else {
					frm.allowed_vehicle_types_cache[load_type] = [];
				}
				if (callback) callback();
			}
		});
	},
	
	setup_vehicle_type_query(frm) {
		// Set up get_query for vehicle_type in child table (transport) based on row's load_type
		if (frm.fields_dict.transport) {
			frm.set_query('vehicle_type', 'transport', function(doc, cdt, cdn) {
				const row = frappe.get_doc(cdt, cdn);
				const load_type = row.load_type;
				if (!load_type) return { filters: {} };
				
				// Ensure cache is initialized
				if (!frm.allowed_vehicle_types_cache) {
					frm.allowed_vehicle_types_cache = {};
				}
				
				// Check if cache exists and has data
				const allowed = frm.allowed_vehicle_types_cache[load_type];
				
				// If cache exists and has data, return filtered list
				if (allowed && allowed.length > 0) {
					return { filters: { name: ["in", allowed] } };
				}
				
				// If cache doesn't exist or is empty, trigger loading
				if (!frm._loading_vehicle_types) frm._loading_vehicle_types = {};
				
				// Trigger async loading if not already loading
				if (!frm._loading_vehicle_types[load_type]) {
					frm._loading_vehicle_types[load_type] = true;
					
					frm.events.load_allowed_vehicle_types(frm, load_type, function() {
						// After cache is loaded, refresh the transport child table
						// This will cause get_query to be called again with the populated cache
						frm.refresh_field('transport');
						if (frm._loading_vehicle_types) {
							delete frm._loading_vehicle_types[load_type];
						}
					});
				}
				
				// Return empty filter while loading - user will need to click dropdown again after cache loads
				// Or we can show a message, but empty filter is cleaner
				return { filters: { name: ["in", []] } };
			});
		}
	},

	apply_default_uoms_per_tab(frm) {
		// Set default weight/volume/chargeable UOM from respective Settings for all visible tabs when fields are empty
		const tabs = [
			{ domain: "sea", visible: frm.doc.is_sea, prefix: "sea_" },
			{ domain: "air", visible: frm.doc.is_air, prefix: "air_" },
			{ domain: "transport", visible: frm.doc.is_transport, prefix: "transport_" },
			{ domain: "warehousing", visible: frm.doc.is_warehousing, prefix: "warehouse_" }
		];
		tabs.forEach(function (tab) {
			if (tab.visible) {
				frm.events.apply_default_uoms_for_tab(frm, tab.domain, tab.prefix);
			}
		});
	},

	apply_default_uoms_for_tab(frm, domain, prefix) {
		// Set default weight/volume/chargeable UOM from Settings for one tab when fields are empty (header fields removed for Sales Quote; skip if not present)
		if (!frm.fields_dict[prefix + "weight_uom"]) return;
		const needWeight = !frm.doc[prefix + "weight_uom"];
		const needVolume = !frm.doc[prefix + "volume_uom"];
		const needChargeable = !frm.doc[prefix + "chargeable_uom"];
		if (!needWeight && !needVolume && !needChargeable) return;
		frappe.call({
			method: "logistics.utils.default_uom.get_default_uoms_for_domain_api",
			args: { domain: domain, company: frm.doc.company || undefined },
			callback: function (r) {
				if (!r.message) return;
				if (needWeight && r.message.weight_uom) {
					frm.set_value(prefix + "weight_uom", r.message.weight_uom);
				}
				if (needVolume && r.message.volume_uom) {
					frm.set_value(prefix + "volume_uom", r.message.volume_uom);
				}
				if (needChargeable && r.message.chargeable_uom) {
					frm.set_value(prefix + "chargeable_uom", r.message.chargeable_uom);
				}
			}
		});
	},
	
	update_primary_button(frm) {
		// Update primary button based on document state
		if (!frm.page || !frm.page.set_primary_action) {
			return;
		}
		
		// Helper function to check submit permission
		const has_submit_permission = function() {
			// Try multiple ways to check submit permission
			if (frm.has_perm && typeof frm.has_perm === 'function') {
				return frm.has_perm("submit");
			}
			if (frm.perm && frm.perm[0] && frm.perm[0].submit) {
				return true;
			}
			// Check if document is submittable (from meta)
			if (frm.meta && frm.meta.is_submittable) {
				// If document is submittable, show submit button
				// Frappe will handle permission check on actual submit
				return true;
			}
			return false;
		};
		
		// New/unsaved document: Show Save button
		if (frm.is_new() || frm.doc.__islocal) {
			frm.page.set_primary_action(__("Save"), function() {
				frm.save();
			});
		} else if (frm.doc.docstatus === 0) {
			// Saved draft document: Show Submit button if no unsaved changes, otherwise Show Save
			// Check if document is actually saved (not local) and not dirty
			const is_saved = !frm.doc.__islocal && frm.doc.name;
			
			// Check dirty state - be more lenient: if document is saved, assume it's clean unless explicitly dirty
			let is_dirty = false;
			if (frm.is_dirty && typeof frm.is_dirty === 'function') {
				is_dirty = frm.is_dirty();
			}
			// Only consider __unsaved if it's explicitly set to 1 (not 0 or undefined)
			if (frm.doc.__unsaved === 1) {
				is_dirty = true;
			}
			
			// For saved documents that are not dirty, show Submit button
			if (is_saved && !is_dirty) {
				// Document is saved and has no unsaved changes: Show Submit button
				if (has_submit_permission()) {
					frm.page.set_primary_action(__("Submit"), function() {
						frm.savesubmit();
					});
					return; // Exit early to prevent showing Save button
				}
			}
			
			// Has unsaved changes or not yet saved: Show Save button
			frm.page.set_primary_action(__("Save"), function() {
				frm.save();
			});
		} else if (frm.doc.docstatus === 1) {
			// Submitted document: Handle Update button if there are unsaved changes
			// For cancel, let Frappe handle it with default behavior (no primary cancel button)
			let is_dirty = false;
			if (frm.is_dirty && typeof frm.is_dirty === 'function') {
				is_dirty = frm.is_dirty();
			}
			if (frm.doc.__unsaved === 1) {
				is_dirty = true;
			}
			
			// If document has unsaved changes, show Update button
			if (is_dirty) {
				if (has_submit_permission()) {
					frm.page.set_primary_action(__("Update"), function() {
						frm.save("Update");
					});
					return;
				}
			}
			
			// No unsaved changes: Clear primary action to let Frappe handle cancel via default behavior
			// This removes the black primary cancel button
			if (frm.page.clear_primary_action && typeof frm.page.clear_primary_action === 'function') {
				frm.page.clear_primary_action();
			} else if (frm.page.btn_primary) {
				frm.page.btn_primary.addClass("hide");
			}
		}
	}
	
});

// Helper function to add create/view buttons for related documents
function add_create_button(frm, config) {
	const {
		doctype,           // e.g., "Transport Order"
		flag_field,        // e.g., "is_transport"
		create_label,      // e.g., "Create Transport Order"
		view_label,        // e.g., "View Transport Orders"
		create_function    // e.g., create_transport_order_from_sales_quote
	} = config;
	
	// Check if flag is set to 1
	if (frm.doc[flag_field] !== 1) return;
	
	// Common conditions
	const isSubmitted = !frm.doc.__islocal && frm.doc.docstatus === 1;
	const isOneOff = frm.doc.quotation_type === "One-off";
	
	if (!isOneOff || !isSubmitted) return;
	
	// Check if document exists
	frappe.db.get_value(doctype, {"sales_quote": frm.doc.name}, "name", function(r) {
		if (!r || !r.name) {
			// Show create button
			frm.add_custom_button(__(create_label), function() {
				create_function(frm);
			}, __("Create"));
		} else {
			// Show view button
			frm.add_custom_button(__(view_label), function() {
				frappe.route_options = {"sales_quote": frm.doc.name};
				frappe.set_route("List", doctype);
			}, __("Actions"));
		}
	});
}

// Child table events for Sales Quote Transport
frappe.ui.form.on('Sales Quote Transport', {
	load_type: function(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.load_type) {
			// Ensure cache is initialized
			if (!frm.allowed_vehicle_types_cache) {
				frm.allowed_vehicle_types_cache = {};
			}
			
			// Store previous vehicle_type to potentially restore it if still valid
			const previous_vehicle_type = row.vehicle_type;
			
			// Clear vehicle_type immediately when load_type changes
			// This prevents showing invalid options in dropdown
			if (previous_vehicle_type) {
				frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
			}
			
			// Load vehicle types and refresh vehicle_type field after loading
			frm.events.load_allowed_vehicle_types(frm, row.load_type, function() {
				// Ensure cache is initialized (defensive check)
				if (!frm.allowed_vehicle_types_cache) {
					frm.allowed_vehicle_types_cache = {};
				}
				// Check if previous vehicle_type is still valid for the new load_type
				if (previous_vehicle_type) {
					const allowed = frm.allowed_vehicle_types_cache[row.load_type] || [];
					if (allowed.length > 0 && allowed.includes(previous_vehicle_type)) {
						// Restore vehicle_type if it's still valid
						frappe.model.set_value(cdt, cdn, 'vehicle_type', previous_vehicle_type);
					}
				}
				// Refresh transport child table to update vehicle_type dropdown with new options
				frm.refresh_field('transport');
			});
		} else {
			// If load_type is cleared, clear vehicle_type and refresh
			if (row.vehicle_type) {
				frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
			}
			frm.refresh_field('transport');
		}
	},
	quantity: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	cost_quantity: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	calculation_method: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	unit_rate: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	unit_type: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	minimum_quantity: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	minimum_charge: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	maximum_charge: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	base_amount: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	cost_calculation_method: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	unit_cost: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	cost_unit_type: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_quantity: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_charge: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	cost_maximum_charge: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	},
	
	cost_base_amount: function(frm, cdt, cdn) {
		trigger_transport_calculation(frm, cdt, cdn);
	}
});

// Function to trigger transport calculations
function trigger_transport_calculation(frm, cdt, cdn) {
	// Get row data from the form
	let row = null;
	if (frm.doc.transport) {
		row = frm.doc.transport.find(function(r) { return r.name === cdn; });
	}
	
	if (!row) {
		// Fallback: use the first transport row
		if (frm.doc.transport && frm.doc.transport.length > 0) {
			row = frm.doc.transport[0];
		} else {
			return;
		}
	}
	
	// Debounce the calculation to avoid too many calls
	if (row._calculation_timeout) {
		clearTimeout(row._calculation_timeout);
	}
	
	row._calculation_timeout = setTimeout(function() {
		// Get current row data
		let line_data = {
			item_code: row.item_code,
			item_name: row.item_name,
			calculation_method: row.calculation_method,
			quantity: row.quantity,
			unit_rate: row.unit_rate,
			unit_type: row.unit_type,
			minimum_quantity: row.minimum_quantity,
			minimum_charge: row.minimum_charge,
			maximum_charge: row.maximum_charge,
			base_amount: row.base_amount,
			cost_calculation_method: row.cost_calculation_method,
			cost_quantity: row.cost_quantity,
			unit_cost: row.unit_cost,
			cost_unit_type: row.cost_unit_type,
			cost_minimum_quantity: row.cost_minimum_quantity,
			cost_minimum_charge: row.cost_minimum_charge,
			cost_maximum_charge: row.cost_maximum_charge,
			cost_base_amount: row.cost_base_amount,
			use_tariff_in_revenue: row.use_tariff_in_revenue,
			use_tariff_in_cost: row.use_tariff_in_cost,
			tariff: row.tariff
		};
		
		// Call the calculation API
		frappe.call({
			method: 'logistics.pricing_center.doctype.sales_quote_transport.sales_quote_transport.trigger_calculations_for_line',
			args: {
				line_data: JSON.stringify(line_data)
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					// Update the row with calculated values
					frappe.model.set_value(cdt, cdn, 'estimated_revenue', r.message.estimated_revenue || 0);
					frappe.model.set_value(cdt, cdn, 'estimated_cost', r.message.estimated_cost || 0);
					frappe.model.set_value(cdt, cdn, 'revenue_calc_notes', r.message.revenue_calc_notes || '');
					frappe.model.set_value(cdt, cdn, 'cost_calc_notes', r.message.cost_calc_notes || '');
					
					// Refresh the field to show updated values
					frm.refresh_field('transport');
				}
			}
		});
	}, 500); // 500ms debounce
}

// Child table events for Sales Quote Air Freight
frappe.ui.form.on('Sales Quote Air Freight', {
	quantity: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	cost_quantity: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	calculation_method: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	unit_rate: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	unit_type: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	minimum_quantity: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	minimum_charge: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	maximum_charge: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	base_amount: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	cost_calculation_method: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	unit_cost: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	cost_unit_type: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_quantity: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_charge: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	cost_maximum_charge: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	},
	
	cost_base_amount: function(frm, cdt, cdn) {
		trigger_air_freight_calculation(frm, cdt, cdn);
	}
});

// Function to trigger air freight calculations
function trigger_air_freight_calculation(frm, cdt, cdn) {
	// Get row data from the form
	let row = null;
	if (frm.doc.air_freight) {
		row = frm.doc.air_freight.find(function(r) { return r.name === cdn; });
	}
	
	if (!row) {
		// Fallback: use the first air freight row
		if (frm.doc.air_freight && frm.doc.air_freight.length > 0) {
			row = frm.doc.air_freight[0];
		} else {
			return;
		}
	}
	
	// Debounce the calculation to avoid too many calls
	if (row._calculation_timeout) {
		clearTimeout(row._calculation_timeout);
	}
	
	row._calculation_timeout = setTimeout(function() {
		// Get current row data
		let line_data = {
			item_code: row.item_code,
			item_name: row.item_name,
			calculation_method: row.calculation_method,
			quantity: row.quantity,
			unit_rate: row.unit_rate,
			unit_type: row.unit_type,
			minimum_quantity: row.minimum_quantity,
			minimum_charge: row.minimum_charge,
			maximum_charge: row.maximum_charge,
			base_amount: row.base_amount,
			cost_calculation_method: row.cost_calculation_method,
			cost_quantity: row.cost_quantity,
			unit_cost: row.unit_cost,
			cost_unit_type: row.cost_unit_type,
			cost_minimum_quantity: row.cost_minimum_quantity,
			cost_minimum_charge: row.cost_minimum_charge,
			cost_maximum_charge: row.cost_maximum_charge,
			cost_base_amount: row.cost_base_amount,
			use_tariff_in_revenue: row.use_tariff_in_revenue,
			use_tariff_in_cost: row.use_tariff_in_cost,
			tariff: row.tariff
		};
		
		// Call the calculation API
		frappe.call({
			method: 'logistics.pricing_center.doctype.sales_quote_air_freight.sales_quote_air_freight.trigger_air_freight_calculations_for_line',
			args: {
				line_data: JSON.stringify(line_data)
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					// Update the row with calculated values
					frappe.model.set_value(cdt, cdn, 'estimated_revenue', r.message.estimated_revenue || 0);
					frappe.model.set_value(cdt, cdn, 'estimated_cost', r.message.estimated_cost || 0);
					frappe.model.set_value(cdt, cdn, 'revenue_calc_notes', r.message.revenue_calc_notes || '');
					frappe.model.set_value(cdt, cdn, 'cost_calc_notes', r.message.cost_calc_notes || '');
					
					// Refresh the field to show updated values
					frm.refresh_field('air_freight');
				}
			}
		});
	}, 500); // 500ms debounce
}

function create_transport_order_from_sales_quote(frm) {
	// Check if one-off and order already exists
	if (frm.doc.quotation_type === "One-off") {
		frappe.db.get_value("Transport Order", {"sales_quote": frm.doc.name}, "name", function(r) {
			if (r && r.name) {
				frappe.msgprint({
					title: __("Cannot Create Multiple Orders"),
					message: __("This is a One-Off Sales Quote and a Transport Order already exists. Only one order can be created from a One-Off quote."),
					indicator: "orange"
				});
				// Show existing order
				frappe.set_route("Form", "Transport Order", r.name);
				return;
			}
			// No existing order - proceed with creation
			show_transport_order_confirmation(frm);
		});
	} else {
		// Not one-off - allow multiple orders
		show_transport_order_confirmation(frm);
	}
}

function show_transport_order_confirmation(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Transport Order from this Sales Quote?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Transport Order..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_transport_order_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					if (r.exc) return;
					
					if (r.message && r.message.success && r.message.transport_order) {
						frappe.msgprint({
							title: __("Transport Order Created"),
							message: __("Transport Order {0} has been created successfully.", [r.message.transport_order]),
							indicator: "green"
						});
						frappe.route_options = { "__clear_scheduled_date": true };
						setTimeout(function() {
							frappe.set_route("Form", "Transport Order", r.message.transport_order);
						}, 100);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.transport_order) {
							setTimeout(function() {
								frappe.set_route("Form", "Transport Order", r.message.transport_order);
							}, 100);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Transport Order. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}

function create_warehouse_contract_from_sales_quote(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Warehouse Contract from this Sales Quote?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Warehouse Contract..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_warehouse_contract_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					if (r.exc) return;
					
					if (r.message && r.message.success && r.message.warehouse_contract) {
						frappe.msgprint({
							title: __("Warehouse Contract Created"),
							message: __("Warehouse Contract {0} has been created successfully.", [r.message.warehouse_contract]),
							indicator: "green"
						});
						setTimeout(function() {
							frappe.set_route("Form", "Warehouse Contract", r.message.warehouse_contract);
						}, 100);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.warehouse_contract) {
							setTimeout(function() {
								frappe.set_route("Form", "Warehouse Contract", r.message.warehouse_contract);
							}, 100);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Warehouse Contract. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}

function create_sales_invoice_from_sales_quote(frm) {
	frappe.confirm(
		__("Create Sales Invoice from this multimodal Sales Quote?"),
		function() {
			frm.dashboard.set_headline_alert(__("Creating Sales Invoice..."));
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_sales_invoice_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("Sales Invoice Created"),
							message: r.message.message,
							indicator: "green"
						});
						const inv = r.message.sales_invoice || (r.message.sales_invoices && r.message.sales_invoices[0]);
						if (inv) {
							frappe.set_route("Form", "Sales Invoice", inv);
						}
					}
				},
				error: function() {
					frm.dashboard.clear_headline();
				}
			});
		}
	);
}

function create_air_booking_from_sales_quote(frm) {
	// Check if one-off and booking already exists
	if (frm.doc.quotation_type === "One-off") {
		frappe.db.get_value("Air Booking", {"sales_quote": frm.doc.name}, "name", function(r) {
			if (r && r.name) {
				frappe.msgprint({
					title: __("Cannot Create Multiple Orders"),
					message: __("This is a One-Off Sales Quote and an Air Booking already exists. Only one booking can be created from a One-Off quote."),
					indicator: "orange"
				});
				// Show existing booking
				frappe.set_route("Form", "Air Booking", r.name);
				return;
			}
			// No existing booking - proceed with creation
			show_air_booking_confirmation(frm);
		});
	} else {
		// Not one-off - allow multiple bookings
		show_air_booking_confirmation(frm);
	}
}

function show_air_booking_confirmation(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create an Air Booking from this Sales Quote?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Air Booking..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_air_booking_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					if (r.exc) return;
					
					if (r.message && r.message.success && r.message.air_booking) {
						frappe.msgprint({
							title: __("Air Booking Created"),
							message: __("Air Booking {0} has been created successfully.", [r.message.air_booking]),
							indicator: "green"
						});
						setTimeout(function() {
							frappe.set_route("Form", "Air Booking", r.message.air_booking);
						}, 100);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.air_booking) {
							setTimeout(function() {
								frappe.set_route("Form", "Air Booking", r.message.air_booking);
							}, 100);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Air Booking. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}

function create_sea_booking_from_sales_quote(frm) {
	// Check if one-off and booking already exists
	if (frm.doc.quotation_type === "One-off") {
		frappe.db.get_value("Sea Booking", {"sales_quote": frm.doc.name}, "name", function(r) {
			if (r && r.name) {
				frappe.msgprint({
					title: __("Cannot Create Multiple Orders"),
					message: __("This is a One-Off Sales Quote and a Sea Booking already exists. Only one booking can be created from a One-Off quote."),
					indicator: "orange"
				});
				// Show existing booking
				frappe.set_route("Form", "Sea Booking", r.name);
				return;
			}
			// No existing booking - proceed with creation
			show_sea_booking_confirmation(frm);
		});
	} else {
		// Not one-off - allow multiple bookings
		show_sea_booking_confirmation(frm);
	}
}

function show_sea_booking_confirmation(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Sea Booking from this Sales Quote?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Sea Booking..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_sea_booking_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					if (r.exc) return;
					
					if (r.message && r.message.success && r.message.sea_booking) {
						frappe.msgprint({
							title: __("Sea Booking Created"),
							message: __("Sea Booking {0} has been created successfully.", [r.message.sea_booking]),
							indicator: "green"
						});
						setTimeout(function() {
							frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
						}, 100);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.sea_booking) {
							setTimeout(function() {
								frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
							}, 100);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Sea Booking. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}

function create_declaration_from_sales_quote(frm) {
	// Check if one-off and declaration already exists
	if (frm.doc.quotation_type === "One-off") {
		frappe.db.get_value("Declaration", {"sales_quote": frm.doc.name}, "name", function(r) {
			if (r && r.name) {
				frappe.msgprint({
					title: __("Cannot Create Multiple Orders"),
					message: __("This is a One-Off Sales Quote and a Declaration already exists. Only one declaration can be created from a One-Off quote."),
					indicator: "orange"
				});
				// Show existing declaration
				frappe.set_route("Form", "Declaration", r.name);
				return;
			}
			// No existing declaration - proceed with creation
			show_declaration_confirmation(frm);
		});
	} else {
		// Not one-off - allow multiple declarations
		show_declaration_confirmation(frm);
	}
}

function show_declaration_confirmation(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Declaration from this Sales Quote?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Declaration..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.customs.doctype.declaration.declaration.create_declaration_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					if (r.exc) return;
					
					if (r.message && r.message.success && r.message.declaration) {
						frappe.msgprint({
							title: __("Declaration Created"),
							message: __("Declaration {0} has been created successfully.", [r.message.declaration]),
							indicator: "green"
						});
						setTimeout(function() {
							frappe.set_route("Form", "Declaration", r.message.declaration);
						}, 100);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.declaration) {
							setTimeout(function() {
								frappe.set_route("Form", "Declaration", r.message.declaration);
							}, 100);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Declaration. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}
