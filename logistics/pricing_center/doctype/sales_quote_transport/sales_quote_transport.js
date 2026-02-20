// Sales Quote Transport Client Script

// Cache key for Vehicle Type list by (load_type, hazardous, reefer) - used for load_type-based filter only
function vehicle_type_cache_key(load_type, hazardous, reefer) {
	return (load_type || "") + "|" + (hazardous ? "1" : "0") + "|" + (reefer ? "1" : "0");
}

// Helper function to apply load_type filters based on transport_job_type from parent
function apply_load_type_filters_for_transport(frm, preserve_existing_value) {
	// Filter load types based on transport job type and boolean columns
	// preserve_existing_value: if true, don't clear load_type even if not in filtered list (used during refresh)
	// Get transport_job_type from parent Sales Quote
	var transport_job_type = frm.doc.transport_job_type;
	
	if (!transport_job_type) {
		// Clear filters if no job type selected - show all transport load types
		// Filters will be applied via get_query
		return;
	}

	// Build filters based on job type
	var filters = {
		transport: 1
	};
	
	// Map transport_job_type to Load Type boolean field
	if (transport_job_type === "Container") {
		filters.container = 1;
	} else if (transport_job_type === "Non-Container") {
		filters.non_container = 1;
	} else if (transport_job_type === "Special") {
		filters.special = 1;
	} else if (transport_job_type === "Oversized") {
		filters.oversized = 1;
	} else if (transport_job_type === "Heavy Haul") {
		filters.heavy_haul = 1;
	} else if (transport_job_type === "Multimodal") {
		filters.multimodal = 1;
	}

	// Filters are applied via get_query in setup_load_type_query_for_transport
}

// Load Vehicle Type names for load_type + hazardous + reefer (for get_query; load_type filter cannot be done in link_filters)
function load_vehicle_types_for_load_type_transport(frm, load_type, callback) {
	if (!load_type) {
		if (callback) callback();
		return;
	}
	// Get hazardous and reefer from parent Sales Quote
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

frappe.ui.form.on('Sales Quote Transport', {
    refresh: function(frm) {
        // Set up load_type and vehicle_type queries
        setup_load_type_query_for_transport(frm);
        setup_vehicle_type_query_for_transport(frm);
        // Apply load_type filters based on parent transport_job_type
        apply_load_type_filters_for_transport(frm, true);
    },
    
    use_tariff_in_revenue: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.use_tariff_in_revenue) {
            // Clear revenue fields when using tariff
            frappe.model.set_value(cdt, cdn, 'calculation_method', '');
            frappe.model.set_value(cdt, cdn, 'unit_rate', 0);
            frappe.model.set_value(cdt, cdn, 'unit_type', '');
            frappe.model.set_value(cdt, cdn, 'minimum_quantity', 0);
            frappe.model.set_value(cdt, cdn, 'minimum_charge', 0);
            frappe.model.set_value(cdt, cdn, 'maximum_charge', 0);
            frappe.model.set_value(cdt, cdn, 'base_amount', 0);
        }
        // Trigger calculation
        frm.refresh_field('transport');
    },
    
    use_tariff_in_cost: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.use_tariff_in_cost) {
            // Clear cost fields when using tariff
            frappe.model.set_value(cdt, cdn, 'cost_calculation_method', '');
            frappe.model.set_value(cdt, cdn, 'unit_cost', 0);
            frappe.model.set_value(cdt, cdn, 'cost_unit_type', '');
            frappe.model.set_value(cdt, cdn, 'cost_minimum_quantity', 0);
            frappe.model.set_value(cdt, cdn, 'cost_minimum_charge', 0);
            frappe.model.set_value(cdt, cdn, 'cost_maximum_charge', 0);
            frappe.model.set_value(cdt, cdn, 'cost_base_amount', 0);
        }
        // Trigger calculation
        frm.refresh_field('transport');
    },
    
    tariff: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.tariff && (row.use_tariff_in_revenue || row.use_tariff_in_cost)) {
            // Fetch tariff data and populate fields
            frappe.call({
                method: 'logistics.pricing_center.doctype.sales_quote_transport.sales_quote_transport.get_tariff_rates',
                args: {
                    tariff_name: row.tariff,
                    item_code: row.item_code
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let tariff_rate = r.message[0];
                        
                        if (row.use_tariff_in_revenue) {
                            // Populate revenue fields
                            frappe.model.set_value(cdt, cdn, 'calculation_method', tariff_rate.calculation_method || 'Per Unit');
                            frappe.model.set_value(cdt, cdn, 'unit_rate', tariff_rate.rate || 0);
                            frappe.model.set_value(cdt, cdn, 'unit_type', tariff_rate.unit_type || '');
                            frappe.model.set_value(cdt, cdn, 'currency', tariff_rate.currency || 'USD');
                            frappe.model.set_value(cdt, cdn, 'minimum_quantity', tariff_rate.minimum_quantity || 0);
                            frappe.model.set_value(cdt, cdn, 'minimum_charge', tariff_rate.minimum_charge || 0);
                            frappe.model.set_value(cdt, cdn, 'maximum_charge', tariff_rate.maximum_charge || 0);
                            frappe.model.set_value(cdt, cdn, 'base_amount', tariff_rate.base_amount || 0);
                            frappe.model.set_value(cdt, cdn, 'uom', tariff_rate.uom || '');
                        }
                        
                        if (row.use_tariff_in_cost) {
                            // Populate cost fields
                            frappe.model.set_value(cdt, cdn, 'cost_calculation_method', tariff_rate.calculation_method || 'Per Unit');
                            frappe.model.set_value(cdt, cdn, 'unit_cost', tariff_rate.rate || 0);
                            frappe.model.set_value(cdt, cdn, 'cost_unit_type', tariff_rate.unit_type || '');
                            frappe.model.set_value(cdt, cdn, 'cost_currency', tariff_rate.currency || 'USD');
                            frappe.model.set_value(cdt, cdn, 'cost_minimum_quantity', tariff_rate.minimum_quantity || 0);
                            frappe.model.set_value(cdt, cdn, 'cost_minimum_charge', tariff_rate.minimum_charge || 0);
                            frappe.model.set_value(cdt, cdn, 'cost_maximum_charge', tariff_rate.maximum_charge || 0);
                            frappe.model.set_value(cdt, cdn, 'cost_base_amount', tariff_rate.base_amount || 0);
                            frappe.model.set_value(cdt, cdn, 'cost_uom', tariff_rate.uom || '');
                        }
                        
                        // Trigger calculations by refreshing the form
                        frm.refresh_field('transport');
                        
                        // Force calculation by triggering a save (this will call the Python validate method)
                        frm.save();
                    } else {
                        frappe.msgprint(__('No matching transport rate found in tariff {0}', [row.tariff]));
                    }
                }
            });
        }
    },
    
    load_type: function(frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.load_type) {
            // Store previous vehicle_type to potentially restore it if still valid
            const previous_vehicle_type = row.vehicle_type;
            
            // Clear vehicle_type immediately when load_type changes
            // This prevents showing invalid options in dropdown
            if (previous_vehicle_type) {
                frappe.model.set_value(cdt, cdn, 'vehicle_type', '');
            }
            
            // Load vehicle types and refresh vehicle_type field after loading
            // Use the same pattern as transport_order.js with hazardous and reefer from parent
            load_vehicle_types_for_load_type_transport(frm, row.load_type, function() {
                // Check if previous vehicle_type is still valid for the new load_type
                if (previous_vehicle_type) {
                    var hazardous = frm.doc.hazardous ? 1 : 0;
                    var reefer = frm.doc.reefer ? 1 : 0;
                    var key = vehicle_type_cache_key(row.load_type, hazardous, reefer);
                    var names = frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key];
                    if (names && names.length > 0 && names.includes(previous_vehicle_type)) {
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
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.tariff && (row.use_tariff_in_revenue || row.use_tariff_in_cost)) {
            // Re-fetch tariff data when item code changes
            frappe.trigger(cdt, cdn, 'tariff');
        }
    },
    
    quantity: function(frm, cdt, cdn) {
        // Trigger calculation when quantity changes
        console.log('Quantity field changed!', cdt, cdn);
        trigger_calculation(frm, cdt, cdn);
    },
    
    cost_quantity: function(frm, cdt, cdn) {
        // Trigger calculation when cost quantity changes
        trigger_calculation(frm, cdt, cdn);
    },
    
    // Revenue calculation triggers
    calculation_method: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    unit_rate: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    unit_type: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    minimum_quantity: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    minimum_charge: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    maximum_charge: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    base_amount: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    // Cost calculation triggers
    cost_calculation_method: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    unit_cost: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    cost_unit_type: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    cost_minimum_quantity: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    cost_minimum_charge: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    cost_maximum_charge: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    },
    
    cost_base_amount: function(frm, cdt, cdn) {
        trigger_calculation(frm, cdt, cdn);
    }
});

// Function to trigger calculations
function trigger_calculation(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
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
        console.log('Triggering calculation with data:', line_data);
        
        frappe.call({
            method: 'logistics.pricing_center.doctype.sales_quote_transport.sales_quote_transport.trigger_calculations_for_line',
            args: {
                line_data: JSON.stringify(line_data)
            },
            callback: function(r) {
                console.log('Calculation API response:', r);
                
                if (r.message && r.message.success) {
                    console.log('Calculation successful:', r.message);
                    
                    // Update the row with calculated values
                    frappe.model.set_value(cdt, cdn, 'estimated_revenue', r.message.estimated_revenue || 0);
                    frappe.model.set_value(cdt, cdn, 'estimated_cost', r.message.estimated_cost || 0);
                    frappe.model.set_value(cdt, cdn, 'revenue_calc_notes', r.message.revenue_calc_notes || '');
                    frappe.model.set_value(cdt, cdn, 'cost_calc_notes', r.message.cost_calc_notes || '');
                    
                    // Refresh the field to show updated values
                    frm.refresh_field('transport');
                } else {
                    console.log('Calculation failed:', r.message);
                }
            },
            error: function(err) {
                console.log('Calculation API error:', err);
            }
        });
    }, 500); // 500ms debounce
}

// Set up get_query for load_type in child table based on parent transport_job_type
function setup_load_type_query_for_transport(frm) {
    // Set up get_query for load_type in child table (transport) based on parent transport_job_type
    if (frm.fields_dict && frm.fields_dict.transport) {
        frm.set_query('load_type', 'transport', function(doc, cdt, cdn) {
            var transport_job_type = doc.transport_job_type;
            
            if (!transport_job_type) {
                return { filters: { transport: 1 } };
            }
            
            var filters = { transport: 1 };
            if (transport_job_type === "Container") {
                filters.container = 1;
            } else if (transport_job_type === "Non-Container") {
                filters.non_container = 1;
            } else if (transport_job_type === "Special") {
                filters.special = 1;
            } else if (transport_job_type === "Oversized") {
                filters.oversized = 1;
            } else if (transport_job_type === "Heavy Haul") {
                filters.heavy_haul = 1;
            } else if (transport_job_type === "Multimodal") {
                filters.multimodal = 1;
            }
            return { filters: filters };
        });
    }
}

// Set up get_query for vehicle_type in child table based on row's load_type + parent hazardous + reefer
function setup_vehicle_type_query_for_transport(frm) {
    // Set up get_query for vehicle_type in child table (transport) based on row's load_type + parent hazardous + reefer
    if (frm.fields_dict && frm.fields_dict.transport) {
        frm.set_query('vehicle_type', 'transport', function(doc, cdt, cdn) {
            const row = frappe.get_doc(cdt, cdn);
            const load_type = row.load_type;
            
            // Get hazardous and reefer from parent Sales Quote
            var hazardous = doc.hazardous ? 1 : 0;
            var reefer = doc.reefer ? 1 : 0;
            var filters = {
                hazardous: hazardous,
                reefer: reefer
            };
            
            if (!load_type) {
                return { filters: filters };
            }
            
            var key = vehicle_type_cache_key(load_type, doc.hazardous, doc.reefer);
            var names = frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[key];
            if (!names) {
                load_vehicle_types_for_load_type_transport(frm, load_type);
                return { filters: Object.assign({ name: ["in", []] }, filters) };
            }
            filters.name = ["in", names];
            return { filters: filters };
        });
    }
}

// Add custom CSS for disabled fields
frappe.ready(function() {
    $('<style>')
        .prop('type', 'text/css')
        .html(`
            .form-control[readonly] {
                background-color: #f8f9fa !important;
                opacity: 0.7;
            }
        `)
        .appendTo('head');
});
