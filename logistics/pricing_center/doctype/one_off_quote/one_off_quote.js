// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("One-Off Quote", {
	onload(frm) {
		// Clear status and converted_to_doc when duplicating
		if (frm.is_new() && (frm.doc.status || frm.doc.converted_to_doc)) {
			frm.set_value('status', '');
			frm.set_value('converted_to_doc', '');
		}
	},
	
	refresh(frm) {
		// Check if Transport Order was deleted and reset converted_to_doc and status
		if (frm.doc.is_transport && !frm.doc.__islocal) {
			// Check if converted_to_doc references a Transport Order
			if (frm.doc.converted_to_doc && frm.doc.converted_to_doc.startsWith("Transport Order:")) {
				// Extract Transport Order name from converted_to_doc
				let transport_order_name = frm.doc.converted_to_doc.replace("Transport Order: ", "").trim();
				
				// Check if Transport Order still exists
				frappe.db.get_value("Transport Order", transport_order_name, "name", function(r) {
					if (!r || !r.name) {
						// Transport Order has been deleted - reset fields
						frm.set_value('converted_to_doc', '');
						frm.set_value('status', '');
						frm.save();
					}
				});
			}
			// Also check if status is "Converted" but no converted_to_doc or Transport Order exists
			else if (frm.doc.status === "Converted" && frm.doc.is_transport) {
				// Check if any Transport Order exists for this quote
				frappe.db.get_value("Transport Order", {"quote": frm.doc.name, "quote_type": "One-Off Quote"}, "name", function(r) {
					if (!r || !r.name) {
						// No Transport Order exists - reset fields
						frm.set_value('converted_to_doc', '');
						frm.set_value('status', '');
						frm.save();
					}
				});
			}
		}
		
		// Create Transport Order button - only show after document submission
		if (frm.doc.is_transport && frm.doc.status !== "Converted" && !frm.doc.converted_to_doc && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			// For submitted documents, check if Transport Order already exists
			frappe.db.get_value("Transport Order", {"quote": frm.doc.name, "quote_type": "One-Off Quote"}, "name", function(r) {
				if (!r || !r.name) {
					// No existing Transport Order - show create button
					frm.add_custom_button(__("Create Transport Order"), () => {
						frappe.call({
							method: "create_transport_order",
							doc: frm.doc,
							callback(r) {
								if (r.exc) return;
								if (r.message && r.message.success && r.message.transport_order) {
									frappe.msgprint(r.message.message, { indicator: "green" });
									frm.reload_doc();
									setTimeout(function() {
										frappe.set_route("Form", "Transport Order", r.message.transport_order);
									}, 100);
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: r.message?.message || __("Failed to create Transport Order"),
										indicator: "red"
									});
								}
							},
							error(r) {
								frappe.msgprint({
									title: __("Error"),
									message: r.message || __("An error occurred while creating Transport Order"),
									indicator: "red"
								});
							}
						});
					});
				} else {
					// Transport Order exists - show view button
					frm.add_custom_button(__("View Transport Order"), () => {
						frappe.set_route("Form", "Transport Order", r.name);
					}, __("View"));
				}
			});
		}
		
		// Create Air Booking button (one conversion per quote; require saved doc)
		if (frm.doc.is_air && frm.doc.status !== "Converted" && !frm.doc.converted_to_doc && !frm.doc.__islocal) {
			frappe.db.get_value("Air Booking", {"quote": frm.doc.name, "quote_type": "One-Off Quote"}, "name", function(r) {
					if (!r || !r.name) {
						// No existing Air Booking - show create button
						frm.add_custom_button(__("Create Air Booking"), () => {
							frappe.call({
								method: "create_air_booking",
								doc: frm.doc,
								callback(r) {
									if (r.exc) return;
									if (r.message && r.message.success && r.message.air_booking) {
										frappe.msgprint(r.message.message, { indicator: "green" });
										frm.reload_doc();
										setTimeout(function() {
											frappe.set_route("Form", "Air Booking", r.message.air_booking);
										}, 100);
									} else {
										frappe.msgprint({
											title: __("Error"),
											message: r.message?.message || __("Failed to create Air Booking"),
											indicator: "red"
										});
									}
								},
								error(r) {
									frappe.msgprint({
										title: __("Error"),
										message: r.message || __("An error occurred while creating Air Booking"),
										indicator: "red"
									});
								}
							});
						});
					} else {
						// Air Booking exists - show view button
						frm.add_custom_button(__("View Air Booking"), () => {
							frappe.set_route("Form", "Air Booking", r.name);
						}, __("View"));
					}
				});
		}
		
		// Create Sea Booking button (one conversion per quote; require saved doc)
		if (frm.doc.is_sea && frm.doc.status !== "Converted" && !frm.doc.converted_to_doc && !frm.doc.__islocal) {
			frappe.db.get_value("Sea Booking", {"quote": frm.doc.name, "quote_type": "One-Off Quote"}, "name", function(r) {
				if (!r || !r.name) {
					frm.add_custom_button(__("Create Sea Booking"), () => {
						frappe.call({
							method: "create_sea_booking",
							doc: frm.doc,
							callback(r) {
								if (r.exc) return;
								if (r.message && r.message.success && r.message.sea_booking) {
									frappe.msgprint(r.message.message, { indicator: "green" });
									frm.reload_doc();
									setTimeout(function() {
										frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
									}, 100);
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: r.message?.message || __("Failed to create Sea Booking"),
										indicator: "red"
									});
								}
							},
							error(r) {
								frappe.msgprint({
									title: __("Error"),
									message: r.message || __("An error occurred while creating Sea Booking"),
									indicator: "red"
								});
							}
						});
					});
				} else {
					frm.add_custom_button(__("View Sea Booking"), () => {
						frappe.set_route("Form", "Sea Booking", r.name);
					}, __("View"));
				}
			});
		}
	}
});

// Child table events for One-Off Quote Transport
frappe.ui.form.on('One-Off Quote Transport', {
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
			method: 'logistics.pricing_center.doctype.one_off_quote_transport.one_off_quote_transport.trigger_calculations_for_line',
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

// Child table events for One-Off Quote Air Freight
frappe.ui.form.on('One-Off Quote Air Freight', {
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
		// Get current row data - read values directly from model to ensure we have the latest values
		// This is important because the value might not be committed to row object yet on first input
		// Get the grid field to access field controls directly
		let grid_field = frm.get_field('air_freight');
		let grid_row = grid_field && grid_field.grid ? grid_field.grid.get_row(cdn) : null;
		
		// Helper function to get value from grid field control or fallback to model/row
		function get_field_value(fieldname) {
			// First try to get value from grid field control (most up-to-date)
			// This ensures we get the value even if it hasn't been committed to the model yet
			if (grid_row && grid_row.on_grid_fields_dict && grid_row.on_grid_fields_dict[fieldname]) {
				let field_control = grid_row.on_grid_fields_dict[fieldname];
				if (field_control && typeof field_control.get_value === 'function') {
					let val = field_control.get_value();
					// Return value if it's defined (0 and false are valid values, only skip undefined/null/empty string)
					if (val !== undefined && val !== null && val !== '') {
						return val;
					}
					// Return 0 or false explicitly (they are falsy but valid)
					if (val === 0 || val === false) {
						return val;
					}
				}
			}
			// Fallback to model value
			let model_val = frappe.model.get_value(cdt, cdn, fieldname);
			if (model_val !== undefined && model_val !== null && model_val !== '') {
				return model_val;
			}
			if (model_val === 0 || model_val === false) {
				return model_val;
			}
			// Final fallback to row value
			return row[fieldname];
		}
		
		let line_data = {
			item_code: get_field_value('item_code') || row.item_code,
			item_name: get_field_value('item_name') || row.item_name,
			calculation_method: get_field_value('calculation_method') || row.calculation_method,
			quantity: get_field_value('quantity') !== undefined ? get_field_value('quantity') : row.quantity,
			unit_rate: get_field_value('unit_rate') !== undefined ? get_field_value('unit_rate') : row.unit_rate,
			unit_type: get_field_value('unit_type') || row.unit_type,
			minimum_quantity: get_field_value('minimum_quantity') !== undefined ? get_field_value('minimum_quantity') : row.minimum_quantity,
			minimum_charge: get_field_value('minimum_charge') !== undefined ? get_field_value('minimum_charge') : row.minimum_charge,
			maximum_charge: get_field_value('maximum_charge') !== undefined ? get_field_value('maximum_charge') : row.maximum_charge,
			base_amount: get_field_value('base_amount') !== undefined ? get_field_value('base_amount') : row.base_amount,
			cost_calculation_method: get_field_value('cost_calculation_method') || row.cost_calculation_method,
			cost_quantity: get_field_value('cost_quantity') !== undefined ? get_field_value('cost_quantity') : row.cost_quantity,
			unit_cost: get_field_value('unit_cost') !== undefined ? get_field_value('unit_cost') : row.unit_cost,
			cost_unit_type: get_field_value('cost_unit_type') || row.cost_unit_type,
			cost_minimum_quantity: get_field_value('cost_minimum_quantity') !== undefined ? get_field_value('cost_minimum_quantity') : row.cost_minimum_quantity,
			cost_minimum_charge: get_field_value('cost_minimum_charge') !== undefined ? get_field_value('cost_minimum_charge') : row.cost_minimum_charge,
			cost_maximum_charge: get_field_value('cost_maximum_charge') !== undefined ? get_field_value('cost_maximum_charge') : row.cost_maximum_charge,
			cost_base_amount: get_field_value('cost_base_amount') !== undefined ? get_field_value('cost_base_amount') : row.cost_base_amount,
			use_tariff_in_revenue: get_field_value('use_tariff_in_revenue') !== undefined ? get_field_value('use_tariff_in_revenue') : row.use_tariff_in_revenue,
			use_tariff_in_cost: get_field_value('use_tariff_in_cost') !== undefined ? get_field_value('use_tariff_in_cost') : row.use_tariff_in_cost,
			tariff: get_field_value('tariff') || row.tariff
		};
		
		// Call the calculation API
		frappe.call({
			method: 'logistics.pricing_center.doctype.one_off_quote_air_freight.one_off_quote_air_freight.trigger_air_freight_calculations_for_line',
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

// Child table events for One-Off Quote Sea Freight
frappe.ui.form.on('One-Off Quote Sea Freight', {
	quantity: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	cost_quantity: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	calculation_method: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	unit_rate: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	unit_type: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	minimum_quantity: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	minimum_charge: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	maximum_charge: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	base_amount: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	cost_calculation_method: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	unit_cost: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	cost_unit_type: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_quantity: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_charge: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	cost_maximum_charge: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	},
	
	cost_base_amount: function(frm, cdt, cdn) {
		trigger_sea_freight_calculation(frm, cdt, cdn);
	}
});

// Function to trigger sea freight calculations
function trigger_sea_freight_calculation(frm, cdt, cdn) {
	// Get row data from the form
	let row = null;
	if (frm.doc.sea_freight) {
		row = frm.doc.sea_freight.find(function(r) { return r.name === cdn; });
	}
	
	if (!row) {
		// Fallback: use the first sea freight row
		if (frm.doc.sea_freight && frm.doc.sea_freight.length > 0) {
			row = frm.doc.sea_freight[0];
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
			method: 'logistics.pricing_center.doctype.one_off_quote_sea_freight.one_off_quote_sea_freight.trigger_one_off_sea_freight_calculations_for_line',
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
					frm.refresh_field('sea_freight');
				}
			}
		});
	}, 500); // 500ms debounce
}
