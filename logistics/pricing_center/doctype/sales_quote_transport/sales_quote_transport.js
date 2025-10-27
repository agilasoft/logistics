// Sales Quote Transport Client Script
frappe.ui.form.on('Sales Quote Transport', {
    refresh: function(frm) {
        // Add custom buttons or functionality if needed
        console.log('Sales Quote Transport form refreshed');
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
        frm.refresh_field('transport_rates');
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
        frm.refresh_field('transport_rates');
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
                        frm.refresh_field('transport_rates');
                        
                        // Force calculation by triggering a save (this will call the Python validate method)
                        frm.save();
                    } else {
                        frappe.msgprint(__('No matching transport rate found in tariff {0}', [row.tariff]));
                    }
                }
            });
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
                    frm.refresh_field('transport_rates');
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
