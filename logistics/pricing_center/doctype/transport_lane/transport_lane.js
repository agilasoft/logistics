frappe.ui.form.on('Transport Lane', {
    refresh: function(frm) {
        // Set field dependencies
        set_field_dependencies(frm);
    },
    
    origin: function(frm) {
        // Update origin zone when origin changes
        update_origin_zone(frm);
    },
    
    destination: function(frm) {
        // Update destination zone when destination changes
        update_destination_zone(frm);
    },
    
    billing_method: function(frm) {
        // Update field visibility based on billing method
        update_field_visibility(frm);
        
        // Recalculate rates
        calculate_rates(frm);
    },
    
    quantity: function(frm) {
        // Recalculate rates when quantity changes
        calculate_rates(frm);
    },
    
    rate: function(frm) {
        // Recalculate rates when rate changes
        calculate_rates(frm);
    },
    
    discount_percentage: function(frm) {
        // Recalculate rates when discount changes
        calculate_rates(frm);
    },
    
    surcharge_amount: function(frm) {
        // Recalculate rates when surcharge changes
        calculate_rates(frm);
    }
});

function set_field_dependencies(frm) {
    // Set field dependencies based on billing method
    update_field_visibility(frm);
}

function update_field_visibility(frm) {
    // Show/hide fields based on billing method
    let billing_method = frm.doc.billing_method;
    
    // Hide all quantity-related fields first
    frm.set_df_property('volume', 'hidden', 1);
    frm.set_df_property('volume_uom', 'hidden', 1);
    frm.set_df_property('weight', 'hidden', 1);
    frm.set_df_property('weight_uom', 'hidden', 1);
    frm.set_df_property('pallets', 'hidden', 1);
    frm.set_df_property('distance_km', 'hidden', 1);
    
    // Show relevant fields based on billing method
    if (billing_method === 'Per Volume') {
        frm.set_df_property('volume', 'hidden', 0);
        frm.set_df_property('volume_uom', 'hidden', 0);
    } else if (billing_method === 'Per Weight') {
        frm.set_df_property('weight', 'hidden', 0);
        frm.set_df_property('weight_uom', 'hidden', 0);
    } else if (billing_method === 'Per Pallet') {
        frm.set_df_property('pallets', 'hidden', 0);
    } else if (billing_method === 'Per Distance') {
        frm.set_df_property('distance_km', 'hidden', 0);
    }
}

function update_origin_zone(frm) {
    if (frm.doc.origin) {
        frappe.call({
            method: "logistics.pricing_center.api_parts.zone.zone_manager.get_zone_from_location",
            args: {
                location_name: frm.doc.origin
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('origin_zone', r.message);
                }
            }
        });
    }
}

function update_destination_zone(frm) {
    if (frm.doc.destination) {
        frappe.call({
            method: "logistics.pricing_center.api_parts.zone.zone_manager.get_zone_from_location",
            args: {
                location_name: frm.doc.destination
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('destination_zone', r.message);
                }
            }
        });
    }
}

function calculate_rates(frm) {
    // Calculate transport rates
    frappe.call({
        method: "logistics.pricing_center.api_parts.transport.transport_calculator.calculate_transport_rates",
        args: {
            sales_quote_transport_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && !r.message.error) {
                frm.set_value('rate', r.message.rate);
                frm.set_value('base_amount', r.message.base_amount);
                frm.set_value('discount_amount', r.message.discount_amount);
                frm.set_value('surcharge_amount', r.message.surcharge_amount);
                frm.set_value('total_amount', r.message.total_amount);
                frm.refresh_fields(['rate', 'base_amount', 'discount_amount', 'surcharge_amount', 'total_amount']);
            }
        }
    });
}

