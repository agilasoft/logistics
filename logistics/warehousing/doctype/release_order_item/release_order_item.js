// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Release Order Item', {
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
    },
    dimension_uom: function(frm) {
        calculate_volume(frm);
    },
    volume_uom: function(frm) {
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
            fieldname: ["default_volume_uom", "default_weight_uom", "default_dimension_uom"]
        },
        callback: function(r) {
            if (r.message) {
                const volume_uom = r.message.default_volume_uom;
                const weight_uom = r.message.default_weight_uom;
                const dimension_uom = r.message.default_dimension_uom;
                
                // Auto-populate volume UOM field
                if (frm.fields_dict.volume_uom && volume_uom) {
                    frm.set_value("volume_uom", volume_uom);
                }
                
                // Auto-populate weight UOM field
                if (frm.fields_dict.weight_uom && weight_uom) {
                    frm.set_value("weight_uom", weight_uom);
                }
                
                // Auto-populate dimension UOM field
                if (frm.fields_dict.dimension_uom && dimension_uom) {
                    frm.set_value("dimension_uom", dimension_uom);
                }
            }
        }
    });
}

// Calculate volume from dimensions
function calculate_volume(frm) {
    const length = parseFloat(frm.doc.length) || 0;
    const width = parseFloat(frm.doc.width) || 0;
    const height = parseFloat(frm.doc.height) || 0;
    
    if (length > 0 && width > 0 && height > 0) {
        // Get UOMs from form or warehouse settings
        const dimension_uom = frm.get_value('dimension_uom');
        const volume_uom = frm.get_value('volume_uom');
        const company = frappe.defaults.get_user_default("Company");
        
        // Call server-side method to calculate volume with UOM conversion
        frappe.call({
            method: "logistics.warehousing.doctype.warehouse_settings.warehouse_settings.calculate_volume_from_dimensions",
            args: {
                length: length,
                width: width,
                height: height,
                dimension_uom: dimension_uom,
                volume_uom: volume_uom,
                company: company
            },
            callback: function(r) {
                if (r.message && r.message.volume !== undefined) {
                    frm.set_value("volume", r.message.volume);
                }
            },
            error: function(r) {
                const volume = 0;
                frm.set_value("volume", volume);
            }
        });
    } else {
        frm.set_value("volume", 0);
    }
}