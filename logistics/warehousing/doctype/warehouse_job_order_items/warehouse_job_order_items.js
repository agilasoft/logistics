// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Job Order Items', {
    refresh: function(frm, cdt, cdn) {
        update_uom_fields(frm);
        if (cdt && cdn) calculate_volume(frm, cdt, cdn);
    },
    length: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    width: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    height: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    dimension_uom: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    volume_uom: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
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

function calculate_volume(frm, cdt, cdn) {
    if (!cdt || !cdn) return;
    const doc = frappe.get_doc(cdt, cdn);
    const length = flt(doc.length) || 0;
    const width = flt(doc.width) || 0;
    const height = flt(doc.height) || 0;

    if (length > 0 && width > 0 && height > 0) {
        const dimension_uom = doc.dimension_uom;
        const volume_uom = doc.volume_uom;
        const company = (frm && frm.doc && frm.doc.company) || frappe.defaults.get_user_default("Company");

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
                    frappe.model.set_value(cdt, cdn, 'volume', r.message.volume);
                }
            },
            error: function() {
                frappe.model.set_value(cdt, cdn, 'volume', 0);
            }
        });
    } else {
        frappe.model.set_value(cdt, cdn, 'volume', 0);
    }
}