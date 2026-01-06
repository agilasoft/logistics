// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stocktake Order Item', {
    refresh: function(frm) {
        update_uom_fields(frm);
    },
    item: function(frm) {
        // When item is selected, dimensions, weight, and volume are fetched via fetch_from
        // Update UOM fields first, then check if volume needs to be calculated
        update_uom_fields(frm);
        // Use retry logic to wait for fields to be populated
        let retryCount = 0;
        const maxRetries = 5;
        const checkAndCalculate = function() {
            const volume = parseFloat(frm.doc.volume) || 0;
            const length = parseFloat(frm.doc.length) || 0;
            const width = parseFloat(frm.doc.width) || 0;
            const height = parseFloat(frm.doc.height) || 0;
            
            // If volume was fetched from item, don't recalculate
            if (volume > 0) {
                return;
            }
            
            // If volume not fetched but dimensions are available, calculate volume
            if (length > 0 && width > 0 && height > 0) {
                calculate_volume(frm);
            } else if (retryCount < maxRetries) {
                // Fields not yet populated, retry after delay
                retryCount++;
                setTimeout(checkAndCalculate, 150);
            }
        };
        setTimeout(checkAndCalculate, 200);
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

// Calculate volume from dimensions (only if volume is not already set)
function calculate_volume(frm) {
    // Check if volume is already set (fetched from item)
    const existingVolume = parseFloat(frm.doc.volume) || 0;
    if (existingVolume > 0) {
        // Volume already fetched from item, don't recalculate
        return;
    }
    
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
                // Fallback to raw calculation on error
                const volume = length * width * height;
                frm.set_value("volume", volume);
            }
        });
    } else {
        frm.set_value("volume", 0);
    }
}