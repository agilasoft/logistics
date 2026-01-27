// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Quote", {
	setup(frm) {
		// Initialize cache for allowed vehicle types
		frm.allowed_vehicle_types_cache = {};
	},
	
	onload(frm) {
		// Set up vehicle_type query filter based on load_type
		if (frm.doc.load_type) {
			frm.events.load_allowed_vehicle_types(frm, frm.doc.load_type);
		}
		frm.events.setup_vehicle_type_query(frm);
	},
	
	refresh(frm) {
		// Re-apply vehicle_type filter on refresh
		if (frm.doc.load_type) {
			frm.events.load_allowed_vehicle_types(frm, frm.doc.load_type);
		}
		frm.events.setup_vehicle_type_query(frm);
		
		// Add custom button to create Transport Order if quote is One-Off and submitted
		if (frm.doc.one_off && frm.doc.transport && frm.doc.transport.length > 0 && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			// Check if Transport Order already exists - restrict multiple orders for one-off quotes
			frappe.db.get_value("Transport Order", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (!r || !r.name) {
					// No existing Transport Order - show create button
					frm.add_custom_button(__("Create Transport Order"), function() {
						create_transport_order_from_sales_quote(frm);
					}, __("Create"));
				} else {
					// Transport Order exists - only show view button
					frm.add_custom_button(__("View Transport Orders"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Transport Order");
					}, __("View"));
				}
			});
		}
		
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
					}, __("View"));
				}
			});
		}
		
		// Add custom button to create Declaration if quote is One-Off and submitted
		if (frm.doc.one_off && frm.doc.customs && frm.doc.customs.length > 0 && !frm.doc.__islocal && frm.doc.docstatus === 1) {
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
					}, __("View"));
				}
			});
		}
		
		// Add custom button to create Air Shipment if quote is One-Off and has air freight
		if (frm.doc.one_off && frm.doc.air_freight && frm.doc.air_freight.length > 0 && !frm.doc.__islocal) {
			// Check if Air Shipment already exists - restrict multiple orders for one-off quotes
			frappe.db.get_value("Air Shipment", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (!r || !r.name) {
					// No existing Air Shipment - show create button
					frm.add_custom_button(__("Create Air Shipment"), function() {
						create_air_shipment_from_sales_quote(frm);
					}, __("Create"));
				} else {
					// Air Shipment exists - only show view button
					frm.add_custom_button(__("View Air Shipments"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Air Shipment");
					}, __("View"));
				}
			});
		}
		
		// Add custom button to create Sea Shipment if quote is One-Off and has sea freight
		if (frm.doc.one_off && frm.doc.sea_freight && frm.doc.sea_freight.length > 0 && !frm.doc.__islocal) {
			// Check if Sea Shipment already exists - restrict multiple orders for one-off quotes
			frappe.db.get_value("Sea Shipment", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (!r || !r.name) {
					// No existing Sea Shipment - show create button
					frm.add_custom_button(__("Create Sea Shipment"), function() {
						create_sea_shipment_from_sales_quote(frm);
					}, __("Create"));
				} else {
					// Sea Shipment exists - only show view button
					frm.add_custom_button(__("View Sea Shipments"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Sea Shipment");
					}, __("View"));
				}
			});
		}
		
		// Add custom button to create Air Booking from current Sales Quote (only when air_freight has data and is One-Off)
		if (frm.doc.one_off && frm.doc.air_freight && frm.doc.air_freight.length > 0 && !frm.doc.__islocal) {
			// Check if Air Booking already exists - restrict multiple orders for one-off quotes
			frappe.db.get_value("Air Booking", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (!r || !r.name) {
					// No existing Air Booking - show create button
					frm.add_custom_button(__("Create Air Booking"), function() {
						create_air_booking_from_sales_quote(frm);
					}, __("Create"));
				} else {
					// Air Booking exists - only show view button
					frm.add_custom_button(__("View Air Bookings"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Air Booking");
					}, __("View"));
				}
			});
		}
		
		// Add custom button to create Sea Booking from current Sales Quote (only when sea_freight has data and is One-Off)
		if (frm.doc.one_off && frm.doc.sea_freight && frm.doc.sea_freight.length > 0 && !frm.doc.__islocal) {
			// Check if Sea Booking already exists - restrict multiple orders for one-off quotes
			frappe.db.get_value("Sea Booking", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (!r || !r.name) {
					// No existing Sea Booking - show create button
					frm.add_custom_button(__("Sea Booking"), function() {
						create_sea_booking_from_sales_quote(frm);
					}, __("Create"));
				} else {
					// Sea Booking exists - only show view button
					frm.add_custom_button(__("View Sea Bookings"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Sea Booking");
					}, __("View"));
				}
			});
		}
	},
	
	load_type(frm) {
		// When load_type changes, load allowed vehicle types and filter vehicle_type
		if (frm.doc.load_type) {
			frm.events.load_allowed_vehicle_types(frm, frm.doc.load_type, function() {
				// After loading, check if current vehicle_type is still valid
				if (frm.doc.vehicle_type) {
					const allowed = frm.allowed_vehicle_types_cache[frm.doc.load_type] || [];
					if (allowed.length > 0 && !allowed.includes(frm.doc.vehicle_type)) {
						// Current vehicle_type is not in the allowed list, clear it
						frm.set_value('vehicle_type', '');
					}
				}
				// Refresh the vehicle_type field to apply new filter
				frm.refresh_field('vehicle_type');
			});
		} else {
			// If load_type is cleared, also clear vehicle_type and remove filter
			frm.set_value('vehicle_type', '');
			frm.events.setup_vehicle_type_query(frm);
		}
	},
	
	load_allowed_vehicle_types(frm, load_type, callback) {
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
			method: "logistics.pricing_center.doctype.sales_quote.sales_quote.get_vehicle_types_for_load_type",
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
	},
	
	setup_vehicle_type_query(frm) {
		// Set up get_query for vehicle_type to filter based on load_type
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
	}
	
});

// Child table events for Sales Quote Transport
frappe.ui.form.on('Sales Quote Transport', {
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
	if (frm.doc.one_off) {
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
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Transport Order Created"),
							message: __("Transport Order {0} has been created successfully.", [r.message.transport_order]),
							indicator: "green"
						});
						
						// Open the created Transport Order and clear scheduled_date for user to fill
						frappe.route_options = { "__clear_scheduled_date": true };
						frappe.set_route("Form", "Transport Order", r.message.transport_order);
					} else if (r.message && r.message.message) {
						// Show info message (e.g., Transport Order already exists)
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Transport Order if available
						if (r.message.transport_order) {
							frappe.set_route("Form", "Transport Order", r.message.transport_order);
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

function create_air_shipment_from_sales_quote(frm) {
	// Check if one-off and shipment already exists
	if (frm.doc.one_off) {
		frappe.db.get_value("Air Shipment", {"sales_quote": frm.doc.name}, "name", function(r) {
			if (r && r.name) {
				frappe.msgprint({
					title: __("Cannot Create Multiple Orders"),
					message: __("This is a One-Off Sales Quote and an Air Shipment already exists. Only one shipment can be created from a One-Off quote."),
					indicator: "orange"
				});
				// Show existing shipment
				frappe.set_route("Form", "Air Shipment", r.name);
				return;
			}
			// No existing shipment - proceed with creation
			show_air_shipment_confirmation(frm);
		});
	} else {
		// Not one-off - allow multiple shipments
		show_air_shipment_confirmation(frm);
	}
}

function show_air_shipment_confirmation(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create an Air Shipment from this Sales Quote?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Air Shipment..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_air_shipment_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Air Shipment Created"),
							message: __("Air Shipment {0} has been created successfully.", [r.message.air_shipment]),
							indicator: "green"
						});
						
						// Open the created Air Shipment
						frappe.set_route("Form", "Air Shipment", r.message.air_shipment);
					} else if (r.message && r.message.message) {
						// Show info message (e.g., Air Shipment already exists)
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Air Shipment if available
						if (r.message.air_shipment) {
							frappe.set_route("Form", "Air Shipment", r.message.air_shipment);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Air Shipment. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}

function create_sea_shipment_from_sales_quote(frm) {
	// Check if one-off and shipment already exists
	if (frm.doc.one_off) {
		frappe.db.get_value("Sea Shipment", {"sales_quote": frm.doc.name}, "name", function(r) {
			if (r && r.name) {
				frappe.msgprint({
					title: __("Cannot Create Multiple Orders"),
					message: __("This is a One-Off Sales Quote and a Sea Shipment already exists. Only one shipment can be created from a One-Off quote."),
					indicator: "orange"
				});
				// Show existing shipment
				frappe.set_route("Form", "Sea Shipment", r.name);
				return;
			}
			// No existing shipment - proceed with creation
			show_sea_shipment_confirmation(frm);
		});
	} else {
		// Not one-off - allow multiple shipments
		show_sea_shipment_confirmation(frm);
	}
}

function show_sea_shipment_confirmation(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Sea Shipment from this Sales Quote?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Sea Shipment..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_sea_shipment_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Sea Shipment Created"),
							message: __("Sea Shipment {0} has been created successfully.", [r.message.sea_shipment]),
							indicator: "green"
						});
						
						// Open the created Sea Shipment
						frappe.set_route("Form", "Sea Shipment", r.message.sea_shipment);
					} else if (r.message && r.message.message) {
						// Show info message (e.g., Sea Shipment already exists)
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Sea Shipment if available
						if (r.message.sea_shipment) {
							frappe.set_route("Form", "Sea Shipment", r.message.sea_shipment);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Sea Shipment. Please try again."),
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
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Warehouse Contract Created"),
							message: __("Warehouse Contract {0} has been created successfully.", [r.message.warehouse_contract]),
							indicator: "green"
						});
						
						// Open the created Warehouse Contract
						frappe.set_route("Form", "Warehouse Contract", r.message.warehouse_contract);
					} else if (r.message && r.message.message) {
						// Show info message
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Warehouse Contract if available
						if (r.message.warehouse_contract) {
							frappe.set_route("Form", "Warehouse Contract", r.message.warehouse_contract);
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

function create_air_booking_from_sales_quote(frm) {
	// Check if one-off and booking already exists
	if (frm.doc.one_off) {
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
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Air Booking Created"),
							message: __("Air Booking {0} has been created successfully.", [r.message.air_booking]),
							indicator: "green"
						});
						
						// Open the created Air Booking
						frappe.set_route("Form", "Air Booking", r.message.air_booking);
					} else if (r.message && r.message.message) {
						// Show info message
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Air Booking if available
						if (r.message.air_booking) {
							frappe.set_route("Form", "Air Booking", r.message.air_booking);
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
	if (frm.doc.one_off) {
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
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Sea Booking Created"),
							message: __("Sea Booking {0} has been created successfully.", [r.message.sea_booking]),
							indicator: "green"
						});
						
						// Open the created Sea Booking
						frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
					} else if (r.message && r.message.message) {
						// Show info message
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Sea Booking if available
						if (r.message.sea_booking) {
							frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
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
	if (frm.doc.one_off) {
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
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Declaration Created"),
							message: __("Declaration {0} has been created successfully.", [r.message.declaration]),
							indicator: "green"
						});
						
						// Open the created Declaration
						frappe.set_route("Form", "Declaration", r.message.declaration);
					} else if (r.message && r.message.message) {
						// Show info message (e.g., Declaration already exists)
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Declaration if available
						if (r.message.declaration) {
							frappe.set_route("Form", "Declaration", r.message.declaration);
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
