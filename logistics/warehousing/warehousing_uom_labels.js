// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Global UOM Labels for Warehousing Module
// This script adds dynamic UOM labels to all volume and weight fields

frappe.ready(function() {
    // Initialize UOM labels for all warehousing forms
    initialize_uom_labels();
});

function initialize_uom_labels() {
    // Check if we're on a warehousing doctype
    const current_doctype = frappe.get_route()[1];
    if (!current_doctype || !is_warehousing_doctype(current_doctype)) {
        return;
    }
    
    // Wait for form to be ready
    frappe.ui.form.on(current_doctype, {
        refresh: function(frm) {
            update_all_uom_labels(frm);
        }
    });
}

function is_warehousing_doctype(doctype) {
    const warehousing_doctypes = [
        'Warehouse Settings',
        'Warehouse Item', 
        'Warehouse Job Item',
        'Warehouse Job Order Items',
        'VAS Order Item',
        'Inbound Order Item',
        'Storage Type',
        'Handling Unit',
        'Handling Unit Type'
    ];
    return warehousing_doctypes.includes(doctype);
}

function update_all_uom_labels(frm) {
    // Get UOM values from Warehouse Settings
    get_warehouse_uom_values().then(function(uom_values) {
        update_volume_weight_labels(frm, uom_values);
    });
}

function get_warehouse_uom_values() {
    return new Promise(function(resolve) {
        const company = frappe.defaults.get_user_default("Company");
        
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Warehouse Settings",
                name: company,
                field: ["default_volume_uom", "default_weight_uom"]
            },
            callback: function(r) {
                if (r.message) {
                    resolve({
                        volume_uom: r.message.default_volume_uom || 'm³',
                        weight_uom: r.message.default_weight_uom || 'kg'
                    });
                } else {
                    resolve({
                        volume_uom: 'm³',
                        weight_uom: 'kg'
                    });
                }
            }
        });
    });
}

function update_volume_weight_labels(frm, uom_values) {
    // Update volume fields
    const volume_fields = ['volume', 'default_pallet_volume', 'default_box_volume'];
    volume_fields.forEach(function(fieldname) {
        if (frm.fields_dict[fieldname]) {
            update_field_label(frm, fieldname, uom_values.volume_uom);
        }
    });
    
    // Update weight fields  
    const weight_fields = ['weight', 'default_pallet_weight', 'default_box_weight'];
    weight_fields.forEach(function(fieldname) {
        if (frm.fields_dict[fieldname]) {
            update_field_label(frm, fieldname, uom_values.weight_uom);
        }
    });
}

function update_field_label(frm, fieldname, uom) {
    const field = frm.fields_dict[fieldname];
    if (field && field.df) {
        // Store original label
        if (!field.df.original_label) {
            field.df.original_label = field.df.label;
        }
        
        // Update label with UOM
        field.df.label = `${field.df.original_label} (${uom})`;
        field.refresh();
    }
}
