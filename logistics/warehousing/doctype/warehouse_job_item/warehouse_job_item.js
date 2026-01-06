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

function calculate_volume(frm) {
    // Get dimension values
    const length = flt(frm.get_value('length') || 0);
    const width = flt(frm.get_value('width') || 0);
    const height = flt(frm.get_value('height') || 0);
    
    // Calculate volume if all dimensions are provided
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
                    frm.set_value('volume', r.message.volume);
                }
            },
            error: function(r) {
                // Fallback to raw calculation on error
                const volume = length * width * height;
                frm.set_value('volume', volume);
            }
        });
    } else {
        // Clear volume if dimensions are incomplete
        frm.set_value('volume', 0);
    }
}