// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Settings', {
    refresh: function(frm) {
        // Update field descriptions when form loads
        update_volume_weight_fields(frm);
    },
    
    default_volume_uom: function(frm) {
        // Update volume-related fields when volume UOM changes
        update_volume_weight_fields(frm);
    },
    
    default_weight_uom: function(frm) {
        // Update weight-related fields when weight UOM changes
        update_volume_weight_fields(frm);
    }
});

function update_volume_weight_fields(frm) {
    // Get the selected UOM values
    const volume_uom = frm.doc.default_volume_uom || 'm³';
    const weight_uom = frm.doc.default_weight_uom || 'kg';
    
    // Update volume field descriptions
    if (frm.fields_dict.default_pallet_volume) {
        frm.fields_dict.default_pallet_volume.df.description = `Enter volume in ${volume_uom}`;
        frm.fields_dict.default_pallet_volume.refresh();
    }
    
    if (frm.fields_dict.default_box_volume) {
        frm.fields_dict.default_box_volume.df.description = `Enter volume in ${volume_uom}`;
        frm.fields_dict.default_box_volume.refresh();
    }
    
    // Update weight field descriptions
    if (frm.fields_dict.default_pallet_weight) {
        frm.fields_dict.default_pallet_weight.df.description = `Enter weight in ${weight_uom}`;
        frm.fields_dict.default_pallet_weight.refresh();
    }
    
    if (frm.fields_dict.default_box_weight) {
        frm.fields_dict.default_box_weight.df.description = `Enter weight in ${weight_uom}`;
        frm.fields_dict.default_box_weight.refresh();
    }
}