// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Quote", {
	refresh(frm) {
		
		
		// Add custom button to create Transport Order if quote is One-Off and submitted
		if (frm.doc.one_off && frm.doc.transport && frm.doc.transport.length > 0 && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			// Always show create button - allow multiple Transport Orders from same Sales Quote
			frm.add_custom_button(__("Create Transport Order"), function() {
				create_transport_order_from_sales_quote(frm);
			}, __("Create"));
			
			// Also add a button to view existing Transport Orders if any exist
			frappe.db.get_value("Transport Order", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (r && r.name) {
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
	},
	
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

function create_transport_order_from_sales_quote(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Transport Order from this Sales Quote? You can create multiple orders from the same Sales Quote."),
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
						
						// Open the created Transport Order
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
