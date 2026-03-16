// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Quote", {
	setup(frm) {
		// Initialize cache for allowed vehicle types
		frm.allowed_vehicle_types_cache = {};
	},
	
	onload(frm) {
		frm.events.setup_vehicle_type_query(frm);
		// Preload vehicle types cache for load_types in Transport charges
		const transport_charges = (frm.doc.charges || []).filter(c => c.service_type === "Transport");
		if (transport_charges.length) {
			const load_types = [...new Set(transport_charges.map(r => r.load_type).filter(Boolean))];
			load_types.forEach(lt => frm.events.load_allowed_vehicle_types(frm, lt));
		}
		// Default UOMs from Settings per tab when fields are empty (for any visible tab)
		if (frm.is_new()) {
			frm.events.apply_default_uoms_per_tab(frm);
			// Clear converted_to_doc and status when duplicating
			if (frm.doc.converted_to_doc) {
				frm.set_value("converted_to_doc", "");
			}
			if (frm.doc.status) {
				frm.set_value("status", "");
			}
			// Validate and auto-correct naming_series on initial load for new documents
			if (frm.doc.quotation_type && frm.doc.naming_series) {
				setTimeout(() => {
					frm.events._validate_naming_series_quotation_type(frm);
				}, 200);
			}
		}
		
		// Set naming_series and quotation_type read-only for existing documents (name already generated)
		// Allow editing for new documents and draft documents that haven't been saved yet
		if (!frm.is_new() && frm.doc.name) {
			frm.set_df_property("naming_series", "read_only", 1);
			frm.set_df_property("quotation_type", "read_only", 1);
		}
		
		// Listen to form dirty state changes to update primary button
		$(frm.wrapper).on("dirty", function() {
			frm.events.update_primary_button(frm);
		});
		
		// Listen to form clean state (when form becomes not dirty) to update primary button
		$(frm.wrapper).on("clean", function() {
			frm.events.update_primary_button(frm);
		});
		// Sync quotation_type to child table rows so Charge Parameters show when Regular
		frm.events._sync_quotation_type_to_children(frm);
	},

	quotation_type(frm) {
		// Determine the correct naming_series based on quotation_type
		let correct_series = null;
		if (frm.doc.quotation_type === "One-off") {
			correct_series = "OOQ.#####";
		} else if (frm.doc.quotation_type === "Project") {
			correct_series = "PQ.#####";
		} else if (frm.doc.quotation_type === "Regular") {
			correct_series = "SQU.#########";
		}
		
		// For new documents, always set the correct naming_series
		// For existing documents, validate and warn if mismatch
		if (frm.is_new() && correct_series) {
			frm.set_value("naming_series", correct_series);
			// Validate after a short delay to ensure value is set
			setTimeout(() => {
				frm.events._validate_naming_series_quotation_type(frm);
			}, 150);
		} else {
			// For existing documents or when quotation_type is cleared, just validate
			// Use setTimeout to ensure doc values are updated
			setTimeout(() => {
				frm.events._validate_naming_series_quotation_type(frm);
			}, 100);
		}
		
		frm.refresh_field("naming_series");
		frm.refresh_field("status_section");
		frm.refresh_field("status");
		frm.refresh_field("converted_to_doc");
		frm.refresh_field("projects_tab");
		frm.events._set_child_param_readonly(frm);
		frm.events._sync_quotation_type_to_children(frm);
		frm.refresh_field("charges");
	},

	naming_series(frm) {
		// Validate naming_series matches quotation_type when user manually changes it
		frm.events._validate_naming_series_quotation_type(frm);
	},

	_validate_naming_series_quotation_type(frm) {
		// Mapping of quotation_type to allowed naming_series prefixes (dot and hyphen both accepted)
		const allowed_prefixes_mapping = {
			"Regular": ["SQU.", "SQU-"],
			"One-off": ["OOQ.", "OOQ-"],
			"Project": ["PQ.", "PQ-"]
		};

		if (!frm.doc.quotation_type || !frm.doc.naming_series) {
			return; // Skip validation if either field is empty
		}

		const allowed_prefixes = allowed_prefixes_mapping[frm.doc.quotation_type];
		if (!allowed_prefixes) {
			return; // Unknown quotation_type, skip validation
		}

		const is_valid = allowed_prefixes.some(p => frm.doc.naming_series.startsWith(p));
		if (!is_valid) {
			const quotation_type = frm.doc.quotation_type;
			const correct_series = quotation_type === "Regular" ? "SQU.#########"
				: quotation_type === "One-off" ? "OOQ.#####"
				: "PQ.#####";
			const expected_display = allowed_prefixes.join(" / ");

			// Auto-correct for new documents immediately
			if (frm.is_new()) {
				frm.set_value("naming_series", correct_series);
				frappe.show_alert({
					message: __("Naming Series automatically updated to match Quotation Type '{0}'.", [quotation_type]),
					indicator: "blue"
				}, 3);
			} else {
				// For existing documents, show warning but don't auto-correct
				frappe.msgprint({
					title: __("Naming Series Mismatch"),
					message: __("Naming Series '{0}' does not match Quotation Type '{1}'. Expected series starting with '{2}' (e.g., {3}).", [
						frm.doc.naming_series,
						quotation_type,
						expected_display,
						correct_series
					]),
					indicator: "orange"
				});
			}
		}
	},

	_set_child_param_readonly(frm) {
		// Legacy child tables (sea_freight, air_freight, transport) removed in Phase 3; params now on Sales Quote Charge
	},

	_sync_quotation_type_to_children(frm) {
		const qt = frm.doc.quotation_type || "Regular";
		(frm.doc.charges || []).forEach(row => { row.quotation_type = qt; });
	},

	charges_add(frm) {
		frm.events._sync_quotation_type_to_children(frm);
	},
	main_service(frm) {
		if (frm.doc.main_service) {
			const prefix_map = { "Sea": "sea_", "Air": "air_", "Transport": "transport_", "Warehousing": "warehouse_" };
			const prefix = prefix_map[frm.doc.main_service];
			if (prefix) {
				frm.events.apply_default_uoms_for_tab(frm, frm.doc.main_service.toLowerCase(), prefix);
			}
		}
	},

	routing_legs_add(frm, cdt, cdn) {
		// Leg order is determined by child table idx (no separate Leg field).
	},

	refresh(frm) {
		// Set naming_series and quotation_type read-only for existing documents (name already generated)
		if (!frm.is_new() && frm.doc.name) {
			frm.set_df_property("naming_series", "read_only", 1);
			frm.set_df_property("quotation_type", "read_only", 1);
		} else {
			frm.set_df_property("naming_series", "read_only", 0);
			frm.set_df_property("quotation_type", "read_only", 0);
		}
		
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
		// Preload vehicle types cache for load_types in Transport charges
		const transport_charges = (frm.doc.charges || []).filter(c => c.service_type === "Transport");
		if (transport_charges.length) {
			const load_types = [...new Set(transport_charges.map(r => r.load_type).filter(Boolean))];
			load_types.forEach(lt => frm.events.load_allowed_vehicle_types(frm, lt));
		}
		frm.events.setup_vehicle_type_query(frm);

		// Add custom button to create Transport Order if main_service = Transport
		add_create_button(frm, {
			doctype: "Transport Order",
			main_service: "Transport",
			create_label: "Create Transport Order",
			view_label: "View Transport Orders",
			create_function: create_transport_order_from_sales_quote
		});
		
		// Add custom button to create Warehouse Contract if quote is submitted and has warehousing items (unified or legacy)
		const has_warehousing = (frm.doc.charges && frm.doc.charges.some(c => c.service_type === "Warehousing")) ||
			(frm.doc.warehousing && frm.doc.warehousing.length > 0);
		if (frm.doc.docstatus === 1 && has_warehousing && !frm.doc.__islocal) {
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
		
		// Add custom button to create Declaration Order if quote is One-Off and submitted (unified or legacy)
		const has_customs = (frm.doc.charges && frm.doc.charges.some(c => c.service_type === "Customs")) ||
			(frm.doc.customs && frm.doc.customs.length > 0);
		if (frm.doc.quotation_type === "One-off" && has_customs && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			frappe.db.get_value("Declaration Order", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (!r || !r.name) {
					frm.add_custom_button(__("Declaration Order"), function() {
						create_declaration_order_from_sales_quote(frm);
					}, __("Create"));
				} else {
					frm.add_custom_button(__("View Declaration Orders"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Declaration Order");
					}, __("Actions"));
				}
			});
		}
		
		// Add custom button to create Air Booking if main_service = Air
		add_create_button(frm, {
			doctype: "Air Booking",
			main_service: "Air",
			create_label: "Create Air Booking",
			view_label: "View Air Bookings",
			create_function: create_air_booking_from_sales_quote
		});
		
		// Add custom button to create Sea Booking if main_service = Sea
		add_create_button(frm, {
			doctype: "Sea Booking",
			main_service: "Sea",
			create_label: "Create Sea Booking",
			view_label: "View Sea Bookings",
			create_function: create_sea_booking_from_sales_quote
		});

		// Recalculate Charges - show when quote has any charge lines
		const has_charges = frm.doc.charges && frm.doc.charges.length > 0;
		if (has_charges && !frm.is_new()) {
			frm.add_custom_button(__("Calculate Charges"), function() {
				frappe.call({
					method: "logistics.pricing_center.doctype.sales_quote.sales_quote.recalculate_charges",
					args: { docname: frm.doc.name },
					freeze: true,
					freeze_message: __("Recalculating charges..."),
					callback: function(r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: r.message.message, indicator: "green" }, 3);
						}
					}
				});
			}, __("Actions"));
		}

		// Get Rates from Cost Sheet - prompt for charge params, show charge list, fetch selected
		if (has_charges && !frm.is_new()) {
			frm.add_custom_button(__("Get Rates from Cost Sheet"), function() {
				show_get_rates_from_cost_sheet_dialog(frm);
			}, __("Actions"));
		}

		// Add custom button to create Sales Invoice from multimodal quote (when routing legs exist and Main Job has job_no)
		if (frm.doc.routing_legs && frm.doc.routing_legs.length > 0 && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			const main_leg = frm.doc.routing_legs.find(r => r.is_main_job);
			const has_main_job = main_leg && main_leg.job_no;
			if (has_main_job) {
				frm.add_custom_button(__("Create Sales Invoice"), function() {
					create_sales_invoice_from_sales_quote(frm);
				}, __("Post"));
			}
		}
		// Cross-module billing: suggest contributors for a leg (bill transport/warehouse with air/sea)
		const legs_with_job = (frm.doc.routing_legs || []).filter(r => r.job_type && r.job_no);
		if (legs_with_job.length > 0) {
			frm.add_custom_button(__("Suggest contributors for leg"), function() {
				suggest_contributors_for_leg(frm, legs_with_job);
			}, __("Routing"));
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
		// Set up get_query for vehicle_type in Transport services based on row's load_type
		if (frm.fields_dict.services) {
			frm.set_query('vehicle_type', 'services', function(doc, cdt, cdn) {
				const row = frappe.get_doc(cdt, cdn);
				if (row.service_type !== "Transport") return { filters: {} };
				const load_type = row.load_type;
				if (!load_type) return { filters: {} };
				
				if (!frm.allowed_vehicle_types_cache) frm.allowed_vehicle_types_cache = {};
				const allowed = frm.allowed_vehicle_types_cache[load_type];
				if (allowed && allowed.length > 0) {
					return { filters: { name: ["in", allowed] } };
				}
				
				if (!frm._loading_vehicle_types) frm._loading_vehicle_types = {};
				if (!frm._loading_vehicle_types[load_type]) {
					frm._loading_vehicle_types[load_type] = true;
					frm.events.load_allowed_vehicle_types(frm, load_type, function() {
						frm.refresh_field('services');
						if (frm._loading_vehicle_types) delete frm._loading_vehicle_types[load_type];
					});
				}
				return { filters: { name: ["in", []] } };
			});
		}
	},

	apply_default_uoms_per_tab(frm) {
		// Set default weight/volume/chargeable UOM from respective Settings for main_service when fields are empty
		const main = frm.doc.main_service || "";
		const tabs = [
			{ domain: "sea", visible: main === "Sea", prefix: "sea_" },
			{ domain: "air", visible: main === "Air", prefix: "air_" },
			{ domain: "transport", visible: main === "Transport", prefix: "transport_" },
			{ domain: "warehousing", visible: main === "Warehousing", prefix: "warehouse_" }
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

// Get Rates from Cost Sheet: Step 1 = params prompt, Step 2 = charge selection dialog
function show_get_rates_from_cost_sheet_dialog(frm) {
	var defaults = {};
	if (frm.doc.quotation_type === "One-off") {
		defaults = {
			service_type: frm.doc.main_service || undefined,
			origin_port: frm.doc.origin_port || undefined,
			destination_port: frm.doc.destination_port || undefined,
			load_type: frm.doc.load_type || undefined,
			transport_mode: frm.doc.transport_mode || undefined
		};
	}
	frappe.prompt([
		{
			fieldname: "charge_params_section",
			fieldtype: "Section Break",
			label: __("Charge Parameters")
		},
		{
			fieldname: "service_type",
			fieldtype: "Select",
			label: __("Service Type"),
			options: "\nAir\nSea\nTransport\nCustoms\nWarehousing",
			default: defaults.service_type
		},
		{
			fieldname: "charge_group",
			fieldtype: "Select",
			label: __("Charge Group"),
			options: "\nOrigin\nDestination\nFreight\nCustoms\nDocumentation\nStorage\nInsurance\nOther"
		},
		{
			fieldname: "column_break_params",
			fieldtype: "Column Break"
		},
		{
			fieldname: "origin_port",
			fieldtype: "Link",
			label: __("Origin Port"),
			options: "UNLOCO",
			default: defaults.origin_port
		},
		{
			fieldname: "destination_port",
			fieldtype: "Link",
			label: __("Destination Port"),
			options: "UNLOCO",
			default: defaults.destination_port
		},
		{
			fieldname: "load_type",
			fieldtype: "Link",
			label: __("Load Type"),
			options: "Load Type",
			default: defaults.load_type
		},
		{
			fieldname: "transport_mode",
			fieldtype: "Select",
			label: __("Transport Mode"),
			options: "\nFCL\nLCL",
			default: defaults.transport_mode
		},
		{
			fieldname: "cost_sheet_optional",
			fieldtype: "Link",
			label: __("Cost Sheet (optional)"),
			description: __("Leave blank to search across all submitted Cost Sheets"),
			options: "Cost Sheet",
			get_query: function() {
				return { filters: { "docstatus": 1 } };
			}
		}
	], function(values) {
		frappe.call({
			method: "logistics.pricing_center.doctype.sales_quote.sales_quote.get_cost_sheet_charges_for_selection",
			args: {
				sales_quote: frm.doc.name,
				cost_sheet: values.cost_sheet_optional || undefined,
				service_type: values.service_type || undefined,
				charge_group: values.charge_group || undefined,
				origin_port: values.origin_port || undefined,
				destination_port: values.destination_port || undefined,
				load_type: values.load_type || undefined,
				transport_mode: values.transport_mode || undefined
			},
			freeze: true,
			freeze_message: __("Loading charges..."),
			callback: function(r) {
				if (!r.message || !r.message.charges || r.message.charges.length === 0) {
					frappe.msgprint({
						title: __("No Charges Found"),
						message: __("No matching charges found. Try adjusting the parameters."),
						indicator: "orange"
					});
					return;
				}
				show_cost_sheet_charge_selection_dialog(frm, r.message.charges);
			}
		});
	}, __("Get Rates from Cost Sheet"));
}

function show_cost_sheet_charge_selection_dialog(frm, charges) {
	var table_html = [
		'<div class="cost-sheet-charge-selection">',
		'<p class="text-muted">' + __("Select charges to fetch into Sales Quote.") + '</p>',
		'<div class="mb-2">',
		'<button type="button" class="btn btn-xs btn-secondary" id="select_all_charges">' + __("Select All") + '</button> ',
		'<button type="button" class="btn btn-xs btn-secondary" id="deselect_all_charges">' + __("Deselect All") + '</button>',
		'</div>',
		'<div class="table-responsive"><table class="table table-bordered table-sm">',
		'<thead><tr>',
		'<th style="width:40px"><input type="checkbox" id="select_all_checkbox" /></th>',
		'<th>' + __("Cost Sheet") + '</th>',
		'<th>' + __("Provider") + '</th>',
		'<th>' + __("Valid From") + '</th>',
		'<th>' + __("Valid To") + '</th>',
		'<th>' + __("Item") + '</th>',
		'<th>' + __("Service") + '</th>',
		'<th>' + __("Charge Group") + '</th>',
		'<th>' + __("Origin") + '</th>',
		'<th>' + __("Destination") + '</th>',
		'<th>' + __("Load Type") + '</th>',
		'<th>' + __("Mode") + '</th>',
		'<th>' + __("Direction") + '</th>',
		'<th>' + __("Unit Cost") + '</th>',
		'<th>' + __("Currency") + '</th>',
		'</tr></thead>',
		'<tbody id="cost_sheet_charge_tbody"></tbody>',
		'</table></div>',
		'</div>'
	].join("");

	var dialog = new frappe.ui.Dialog({
		title: __("Select Charges to Fetch"),
		size: "extra-large",
		fields: [
			{ fieldname: "charges_section", fieldtype: "Section Break", label: __("Available Charges") },
			{ fieldname: "charges_html", fieldtype: "HTML", options: table_html }
		],
		primary_action_label: __("Fetch Selected"),
		primary_action: function() {
			var tbody = dialog.$wrapper.find("#cost_sheet_charge_tbody");
			var selected = [];
			tbody.find("tr").each(function() {
				var $row = $(this);
				if ($row.find("input.charge-select").is(":checked")) {
					selected.push($row.data("charge-name"));
				}
			});
			if (selected.length === 0) {
				frappe.msgprint({
					title: __("No Selection"),
					message: __("Please select at least one charge to fetch."),
					indicator: "orange"
				});
				return;
			}
			dialog.hide();
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.get_rates_from_cost_sheet",
				args: {
					sales_quote: frm.doc.name,
					selected_charge_names: selected
				},
				freeze: true,
				freeze_message: __("Fetching rates from Cost Sheet..."),
				callback: function(r) {
					if (r.message && r.message.success) {
						frm.reload_doc();
						frappe.show_alert({
							message: r.message.message || __("Cost rates have been populated from Cost Sheet"),
							indicator: "green"
						}, 3);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
					}
				}
			});
		}
	});
	dialog.show();

	var tbody = dialog.$wrapper.find("#cost_sheet_charge_tbody");
	charges.forEach(function(ch) {
		var tr = $('<tr></tr>');
		tr.data("charge-name", ch.name);
		tr.append('<td><input type="checkbox" class="charge-select" checked /></td>');
		var csTitle = ch.cost_sheet_description ? (' title="' + frappe.utils.escape_html(ch.cost_sheet_description) + '"') : '';
		tr.append('<td' + csTitle + '>' + (ch.cost_sheet || "") + '</td>');
		tr.append('<td>' + (ch.provider_name || ch.provider_type || "") + '</td>');
		tr.append('<td>' + (ch.valid_from || "") + '</td>');
		tr.append('<td>' + (ch.valid_to || "") + '</td>');
		tr.append('<td>' + (ch.item_code || "") + (ch.item_name ? " - " + ch.item_name : "") + '</td>');
		tr.append('<td>' + (ch.service_type || "") + '</td>');
		tr.append('<td>' + (ch.charge_group || "") + '</td>');
		tr.append('<td>' + (ch.origin_port || "") + '</td>');
		tr.append('<td>' + (ch.destination_port || "") + '</td>');
		tr.append('<td>' + (ch.load_type || "") + '</td>');
		tr.append('<td>' + (ch.transport_mode || "") + '</td>');
		tr.append('<td>' + (ch.direction || "") + '</td>');
		tr.append('<td>' + (ch.unit_cost != null && ch.unit_cost !== "" ? (typeof frappe.format === "function" ? frappe.format(ch.unit_cost, { fieldtype: "Currency", options: ch.cost_currency || "" }) : ch.unit_cost) : "") + '</td>');
		tr.append('<td>' + (ch.cost_currency || "") + '</td>');
		tbody.append(tr);
	});

	dialog.$wrapper.find("#select_all_charges").on("click", function() {
		tbody.find("input.charge-select").prop("checked", true);
		dialog.$wrapper.find("#select_all_checkbox").prop("checked", true);
	});
	dialog.$wrapper.find("#deselect_all_charges").on("click", function() {
		tbody.find("input.charge-select").prop("checked", false);
		dialog.$wrapper.find("#select_all_checkbox").prop("checked", false);
	});
	dialog.$wrapper.find("#select_all_checkbox").on("change", function() {
		var checked = $(this).is(":checked");
		tbody.find("input.charge-select").prop("checked", checked);
	});
	tbody.on("change", "input.charge-select", function() {
		var total = tbody.find("input.charge-select").length;
		var checked = tbody.find("input.charge-select:checked").length;
		dialog.$wrapper.find("#select_all_checkbox").prop("checked", total === checked);
	});
}

// Helper function to add create/view buttons for related documents
function add_create_button(frm, config) {
	const {
		doctype,           // e.g., "Transport Order"
		main_service,      // e.g., "Transport"
		create_label,      // e.g., "Create Transport Order"
		view_label,        // e.g., "View Transport Orders"
		create_function    // e.g., create_transport_order_from_sales_quote
	} = config;

	// Check if main_service matches or quote has charges for this service
	const mainMatches = frm.doc.main_service === main_service;
	const hasChargesForService = (frm.doc.charges || []).some(c => c.service_type === main_service);
	if (!mainMatches && !hasChargesForService) return;
	
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

// Child table events for Sales Quote Charge (Transport: vehicle_type, load_type; revenue/cost calculation)
frappe.ui.form.on('Sales Quote Charge', {
	charge_type: function(frm, cdt, cdn) {
		// Refresh charges so Revenue/Cost fields show/hide based on charge_type
		frm.refresh_field('charges');
	},
	load_type: function(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.service_type !== "Transport" || !row.load_type) return;
		if (!frm.allowed_vehicle_types_cache) frm.allowed_vehicle_types_cache = {};
		const previous_vehicle_type = row.vehicle_type;
		if (previous_vehicle_type) frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
		frm.events.load_allowed_vehicle_types(frm, row.load_type, function() {
			if (!frm.allowed_vehicle_types_cache) frm.allowed_vehicle_types_cache = {};
			const allowed = frm.allowed_vehicle_types_cache[row.load_type] || [];
			if (previous_vehicle_type && allowed.length > 0 && allowed.includes(previous_vehicle_type)) {
				frappe.model.set_value(cdt, cdn, 'vehicle_type', previous_vehicle_type);
			}
			frm.refresh_field('charges');
		});
	},
	calculation_method: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	unit_rate: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	quantity: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	unit_type: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	minimum_quantity: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	minimum_charge: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	maximum_charge: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	base_amount: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	cost_calculation_method: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	cost_quantity: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	unit_cost: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	cost_unit_type: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	cost_minimum_quantity: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	cost_minimum_charge: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	cost_maximum_charge: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
	cost_base_amount: function(frm, cdt, cdn) { _calculate_sales_quote_charge_row(frm, cdt, cdn); },
});

function _calculate_sales_quote_charge_row(frm, cdt, cdn) {
	if (!cdn) return;
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) return;
	frappe.call({
		method: "logistics.utils.charges_calculation.calculate_charge_row",
		args: {
			doctype: "Sales Quote Charge",
			parenttype: "Sales Quote",
			parent: frm.doc.name || "new",
			row_data: JSON.stringify(row)
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				frappe.model.set_value(cdt, cdn, "estimated_revenue", r.message.estimated_revenue);
				frappe.model.set_value(cdt, cdn, "estimated_cost", r.message.estimated_cost);
				if (r.message.quantity != null) {
					frappe.model.set_value(cdt, cdn, "quantity", r.message.quantity);
				}
				if (r.message.cost_quantity != null) {
					frappe.model.set_value(cdt, cdn, "cost_quantity", r.message.cost_quantity);
				}
				frappe.model.set_value(cdt, cdn, "revenue_calc_notes", r.message.revenue_calc_notes || "");
				frappe.model.set_value(cdt, cdn, "cost_calc_notes", r.message.cost_calc_notes || "");
			}
		}
	});
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

function suggest_contributors_for_leg(frm, legs_with_job) {
	let leg;
	if (legs_with_job.length === 1) {
		leg = legs_with_job[0];
		do_suggest_contributors(frm, leg);
		return;
	}
	const option_labels = legs_with_job.map((r, i) => __("Leg {0}: {1} {2}").format((i + 1), r.job_type || "", r.job_no || ""));
	frappe.prompt({
		fieldname: "leg_idx",
		fieldtype: "Select",
		label: __("Select leg to suggest contributors for"),
		options: option_labels.join("\n"),
		reqd: 1
	}, function(values) {
		const idx = option_labels.indexOf(values.leg_idx);
		leg = legs_with_job[idx >= 0 ? idx : 0];
		do_suggest_contributors(frm, leg);
	}, __("Suggest contributors"));
}

function do_suggest_contributors(frm, leg) {
	frappe.call({
		method: "logistics.billing.cross_module_billing.get_suggested_contributors_for_anchor",
		args: {
			anchor_doctype: leg.job_type,
			anchor_name: leg.job_no,
			sales_quote: frm.doc.name || undefined
		},
		callback: function(r) {
			if (!r.message || r.message.length === 0) {
				frappe.msgprint({ message: __("No linked jobs found to bill with this leg."), indicator: "blue" });
				return;
			}
			const existing = (leg.bill_with_contributors || []).map(c => c.contributor_job_type + "|" + c.contributor_job_no);
			let added = 0;
			(r.message || []).forEach(function(s) {
				const key = (s.job_type || s.contributor_job_type) + "|" + (s.job_no || s.contributor_job_no);
				if (existing.indexOf(key) >= 0) return;
				existing.push(key);
				if (!leg.bill_with_contributors) leg.bill_with_contributors = [];
				leg.bill_with_contributors.push({
					contributor_job_type: s.job_type || s.contributor_job_type,
					contributor_job_no: s.job_no || s.contributor_job_no
				});
				added++;
			});
			frm.refresh_field("routing_legs");
			frappe.msgprint({ message: __("Added {0} contributor(s) to leg. Save the document to keep changes.").format(added), indicator: "green" });
		}
	});
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

					var air_booking_name = (r.message && r.message.air_booking) ? r.message.air_booking : null;
					if (!air_booking_name) {
						if (r.message && r.message.success) {
							frappe.msgprint({
								title: __("Air Booking Created"),
								message: __("Air Booking has been created successfully."),
								indicator: "green"
							});
						} else if (r.message && r.message.message) {
							frappe.msgprint({
								title: __("Information"),
								message: r.message.message,
								indicator: "blue"
							});
						}
						return;
					}

					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("Air Booking Created"),
							message: __("Air Booking {0} has been created successfully.", [air_booking_name]),
							indicator: "green"
						});
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
					}

					// Poll until doc is visible on server, then navigate (avoids "Air Booking ... not found" on form load)
					function try_navigate(attempt) {
						var max_attempts = 15;
						if (attempt > max_attempts) {
							frappe.set_route("Form", "Air Booking", air_booking_name);
							return;
						}
						frappe.call({
							method: "logistics.air_freight.doctype.air_booking.air_booking.air_booking_exists",
							args: { docname: air_booking_name },
							callback: function(res) {
								if (res.message === true) {
									frappe.set_route("Form", "Air Booking", air_booking_name);
								} else {
									setTimeout(function() { try_navigate(attempt + 1); }, 300);
								}
							},
							error: function() {
								setTimeout(function() { try_navigate(attempt + 1); }, 300);
							}
						});
					}
					try_navigate(1);
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
					const msg = (r && r.message) || __("Failed to create Sea Booking. Please try again.");
					frappe.msgprint({
						title: __("Error"),
						message: msg,
						indicator: "red"
					});
				}
			});
		}
	);
}

function create_declaration_order_from_sales_quote(frm) {
	if (frm.doc.quotation_type === "One-off") {
		frappe.db.get_value("Declaration Order", {"sales_quote": frm.doc.name}, "name", function(r) {
			if (r && r.name) {
				frappe.msgprint({
					title: __("Already Created"),
					message: __("A Declaration Order already exists for this One-Off Sales Quote."),
					indicator: "orange"
				});
				frappe.set_route("Form", "Declaration Order", r.name);
				return;
			}
			show_declaration_order_confirmation(frm);
		});
	} else {
		show_declaration_order_confirmation(frm);
	}
}

function show_declaration_order_confirmation(frm) {
	frappe.confirm(
		__("Create a Declaration Order from this Sales Quote?"),
		function() {
			frm.dashboard.set_headline_alert(__("Creating Declaration Order..."));
			frappe.call({
				method: "logistics.customs.doctype.declaration_order.declaration_order.create_declaration_order_from_sales_quote",
				args: { sales_quote_name: frm.doc.name },
				callback: function(r) {
					frm.dashboard.clear_headline();
					if (r.exc) return;
					if (r.message && r.message.success && r.message.declaration_order) {
						frappe.msgprint({
							title: __("Declaration Order Created"),
							message: __("Declaration Order {0} has been created. Sales Quote status and Converted To have been updated.", [r.message.declaration_order]),
							indicator: "green"
						});
						frm.reload_doc();
						setTimeout(function() {
							frappe.set_route("Form", "Declaration Order", r.message.declaration_order);
						}, 100);
					} else if (r.message && r.message.message) {
						frappe.msgprint({ title: __("Information"), message: r.message.message, indicator: "blue" });
						if (r.message.declaration_order) {
							frm.reload_doc();
							setTimeout(function() { frappe.set_route("Form", "Declaration Order", r.message.declaration_order); }, 100);
						}
					}
				},
				error: function() {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Declaration Order. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}
