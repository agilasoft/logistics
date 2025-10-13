// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tariff', {
    refresh: function(frm) {
        // Custom buttons removed as requested
    },
    
    valid_from: function(frm) {
        if (frm.doc.valid_from && frm.doc.valid_to && frm.doc.valid_from > frm.doc.valid_to) {
            frappe.msgprint(__('Valid From date cannot be later than Valid To date'));
            frm.set_value('valid_to', '');
        }
    },
    
    valid_to: function(frm) {
        if (frm.doc.valid_from && frm.doc.valid_to && frm.doc.valid_from > frm.doc.valid_to) {
            frappe.msgprint(__('Valid To date cannot be earlier than Valid From date'));
            frm.set_value('valid_from', '');
        }
    }
});








// Child table events for rate validation
frappe.ui.form.on('Air Freight Rate', {
    calculation_method: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    },
    rate_value: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    }
});

frappe.ui.form.on('Sea Freight Rate', {
    calculation_method: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    },
    rate_value: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    }
});

frappe.ui.form.on('Transport Rate', {
    calculation_method: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    },
    rate_value: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    }
});

frappe.ui.form.on('Customs Rate', {
    calculation_method: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    },
    rate_value: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    }
});

frappe.ui.form.on('Warehousing Rate', {
    calculation_method: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    },
    rate_value: function(frm, cdt, cdn) {
        validate_rate_entry(frm, cdt, cdn);
    }
});

function validate_rate_entry(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    // Validate minimum and maximum charges
    if (row.minimum_charge && row.maximum_charge && row.minimum_charge > row.maximum_charge) {
        frappe.msgprint(__('Minimum charge cannot be greater than maximum charge'));
        frappe.model.set_value(cdt, cdn, 'minimum_charge', '');
    }
    
    // Validate date ranges
    if (row.valid_from && row.valid_to && row.valid_from > row.valid_to) {
        frappe.msgprint(__('Valid From date cannot be later than Valid To date'));
        frappe.model.set_value(cdt, cdn, 'valid_to', '');
    }
}