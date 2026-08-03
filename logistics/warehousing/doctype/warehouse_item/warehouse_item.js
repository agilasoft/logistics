// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Item', {
    setup: function(frm) {
        frm._code_manual = false;
        frm._updating_code = false;
        frm._last_auto_code = null;
    },
    refresh: function(frm) {
        update_uom_fields(frm);
        // Bind change events directly to input fields for more reliable triggering
        _setup_dimension_listeners(frm);
        // Saved documents keep their Code unless the user clears it (rename risk).
        if (!frm.is_new() && frm.doc.code) {
            frm._code_manual = true;
            frm._last_auto_code = frm.doc.code;
        } else if (frm.is_new() && !frm._code_manual) {
            maybe_generate_item_code(frm);
        }
    },
    length: function(frm) {
        // Use setTimeout to ensure value is committed to doc
        setTimeout(function() {
            calculate_volume(frm);
        }, 100);
    },
    width: function(frm) {
        // Use setTimeout to ensure value is committed to doc
        setTimeout(function() {
            calculate_volume(frm);
        }, 100);
    },
    height: function(frm) {
        // Use setTimeout to ensure value is committed to doc
        setTimeout(function() {
            calculate_volume(frm);
        }, 100);
    },
    weight: function(frm) {
        validate_weight(frm);
    },
    batch_tracking: function(frm) {
        validate_tracking_exclusivity(frm, 'batch_tracking', 'serial_tracking');
    },
    serial_tracking: function(frm) {
        validate_tracking_exclusivity(frm, 'serial_tracking', 'batch_tracking');
    },
    customer: function(frm) {
        set_customer_code(frm);
    },
    item_name: function(frm) {
        maybe_generate_item_code(frm);
    },
    customer_code: function(frm) {
        maybe_generate_item_code(frm);
    },
    code: function(frm) {
        if (frm._updating_code) {
            return;
        }
        // Treat any user edit as manual so subsequent Customer / Item Name
        // changes do not overwrite a custom code.
        const current = (frm.doc.code || '').trim();
        frm._code_manual = current !== '' && current !== (frm._last_auto_code || '');
        if (!current) {
            frm._code_manual = false;
            maybe_generate_item_code(frm);
        }
    }
});

function set_customer_code(frm) {
    if (!frm.doc.customer) {
        frm.set_value('customer_code', '');
        return;
    }
    frappe.db.get_value('Customer', frm.doc.customer, 'logistics_party_code', (r) => {
        frm.set_value('customer_code', (r && r.logistics_party_code) || '');
    });
}

function maybe_generate_item_code(frm) {
    if (frm._code_manual) {
        return;
    }
    if (!frm.doc.item_name || !frm.doc.customer) {
        return;
    }
    // Wait for customer_code when it is still being fetched
    if (!frm.doc.customer_code) {
        return;
    }

    frappe.call({
        method: 'logistics.warehousing.doctype.warehouse_item.warehouse_item.suggest_warehouse_item_code',
        args: {
            item_name: frm.doc.item_name,
            customer: frm.doc.customer,
            customer_code: frm.doc.customer_code,
            doc_name: frm.doc.name
        },
        callback: function(r) {
            if (frm._code_manual || !r.message) {
                return;
            }
            frm._last_auto_code = r.message;
            frm._updating_code = true;
            frm.set_value('code', r.message).then(function() {
                frm._updating_code = false;
            });
        }
    });
}

function _setup_dimension_listeners(frm) {
    // Setup direct event listeners on dimension fields for more reliable triggering
    ['length', 'width', 'height'].forEach(function(fieldname) {
        if (frm.fields_dict[fieldname] && frm.fields_dict[fieldname].$input) {
            frm.fields_dict[fieldname].$input.off('change.volume_calc').on('change.volume_calc', function() {
                setTimeout(function() {
                    calculate_volume(frm);
                }, 100);
            });
        }
    });
}

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
    if (!frm || !frm.doc) {
        return;
    }
    
    // Get dimension values - use doc directly for more reliable access in event handlers
    const length = flt(frm.doc.length || 0);
    const width = flt(frm.doc.width || 0);
    const height = flt(frm.doc.height || 0);
    
    // Validate dimensions
    if (length < 0 || width < 0 || height < 0) {
        frappe.msgprint(__("Dimensions cannot be negative. Please enter valid values."));
        return;
    }
    
    // Calculate volume if all dimensions are provided
    if (length > 0 && width > 0 && height > 0) {
        // Get UOMs from form or warehouse settings - use doc directly
        const dimension_uom = frm.doc.dimension_uom;
        const volume_uom = frm.doc.volume_uom;
        const company = frappe.defaults.get_user_default("Company");
        
        // Call server-side method to calculate volume with UOM conversion
        frappe.call({
            method: "logistics.warehousing.utils.volume_conversion.calculate_volume_from_dimensions_api",
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
                    const volume = r.message.volume;
                    frm.set_value('volume', volume);
                    
                    // Validate reasonable volume (prevent unrealistic values)
                    if (volume > 1000000) { // 1 million cubic units
                        frappe.msgprint(__("Warning: Calculated volume seems unusually large. Please verify dimensions."));
                    }
                }
            },
            error: function(r) {
                // Do not set raw L×W×H when volume_uom is a volume unit (e.g. Cubic Meter)
                frm.set_value('volume', 0);
            }
        });
    } else {
        // Clear volume if dimensions are incomplete
        frm.set_value('volume', 0);
    }
}

function validate_weight(frm) {
    const weight = flt(frm.get_value('weight') || 0);
    
    // Validate weight
    if (weight < 0) {
        frappe.msgprint(__("Weight cannot be negative. Please enter a valid value."));
        frm.set_value('weight', 0);
        return;
    }
    
    // Validate reasonable weight (prevent unrealistic values)
    if (weight > 10000) { // 10,000 weight units
        frappe.msgprint(__("Warning: Weight seems unusually high. Please verify the value."));
    }
    
}

function validate_tracking_exclusivity(frm, current_field, other_field) {
    if (!frm || !frm.doc) {
        return;
    }
    
    // Get values directly from the document
    const current_value = frm.doc[current_field];
    const other_value = frm.doc[other_field];
    
    // Check if current field is checked (true, 1, or any truthy value)
    // and other field is also checked
    const current_checked = current_value == 1 || current_value === true || current_value == '1';
    const other_checked = other_value == 1 || other_value === true || other_value == '1';
    
    if (current_checked && other_checked) {
        const current_label = current_field === 'batch_tracking' ? 'Batch Tracking' : 'Serial Tracking';
        const other_label = other_field === 'batch_tracking' ? 'Batch Tracking' : 'Serial Tracking';
        
        // Event message
        frappe.show_alert({
            message: __("{0} and {1} cannot both be enabled. {2} has been unchecked.", [current_label, other_label, other_label]),
            indicator: 'orange'
        }, 5);
        
        // Uncheck the other field
        frm.set_value(other_field, 0);
    }
}