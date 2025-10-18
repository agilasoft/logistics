// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Job Item', {
    refresh: function(frm) {
        update_uom_fields(frm);
    },
    length: function(frm) {
        calculate_volume(frm);
    },
    width: function(frm) {
        calculate_volume(frm);
    },
    height: function(frm) {
        calculate_volume(frm);
    }
});

function update_uom_fields(frm) {
    // Get UOM values from Warehouse Settings
    const company = frappe.defaults.get_user_default("Company");
    
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Warehouse Settings",
            name: company,
            fieldname: ["default_volume_uom", "default_weight_uom"]
        },
        callback: function(r) {
            if (r.message) {
                const volume_uom = r.message.default_volume_uom;
                const weight_uom = r.message.default_weight_uom;
                
                // Auto-populate volume UOM field
                if (frm.fields_dict.volume_uom && volume_uom) {
                    frm.set_value("volume_uom", volume_uom);
                }
                
                // Auto-populate weight UOM field
                if (frm.fields_dict.weight_uom && weight_uom) {
                    frm.set_value("weight_uom", weight_uom);
                }
            }
        }
    });
}

function calculate_volume(frm) {
    
    // Get dimension values
    const length = flt(frm.get_value('length') || 0);
    const width = flt(frm.get_value('width') || 0);
    const height = flt(frm.get_value('height') || 0);
    
    console.log("Dimensions - Length:", length, "Width:", width, "Height:", height);
    
    // Calculate volume if all dimensions are provided
    if (length > 0 && width > 0 && height > 0) {
        const volume = length * width * height;
        console.log("Calculated volume:", volume);
        frm.set_value('volume', volume);
    } else {
        // Clear volume if dimensions are incomplete
        console.log("Incomplete dimensions, clearing volume");
        frm.set_value('volume', 0);
    }
}