// Auto-populate UNLOCO details when UNLOCO code is entered
frappe.ui.form.on('UNLOCO', {
    unlocode: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            // Call server method to populate details
            frappe.call({
                method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                args: {
                    'unlocode': frm.doc.unlocode
                },
                callback: function(r) {
                    if (r.message) {
                        // Update form with populated data
                        Object.keys(r.message).forEach(function(key) {
                            if (r.message[key] !== null && r.message[key] !== undefined) {
                                frm.set_value(key, r.message[key]);
                            }
                        });
                        frm.refresh_fields();
                        frappe.show_alert({
                            message: 'UNLOCO details populated successfully!',
                            indicator: 'green'
                        });
                    } else {
                        frappe.show_alert({
                            message: 'No UNLOCO details found for this code.',
                            indicator: 'orange'
                        });
                    }
                }
            });
        }
    },
    
    auto_populate: function(frm) {
        if (frm.doc.auto_populate && frm.doc.unlocode) {
            // Trigger auto-populate if UNLOCO code exists
            frm.trigger('unlocode');
        }
    }
});

// Add custom button for manual populate
frappe.ui.form.on('UNLOCO', {
    refresh: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            frm.add_custom_button('Populate UNLOCO Details', function() {
                frappe.call({
                    method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                    args: {
                        'unlocode': frm.doc.unlocode
                    },
                    callback: function(r) {
                        if (r.message) {
                            Object.keys(r.message).forEach(function(key) {
                                if (r.message[key] !== null && r.message[key] !== undefined) {
                                    frm.set_value(key, r.message[key]);
                                }
                            });
                            frm.refresh_fields();
                            frappe.show_alert({
                                message: 'UNLOCO details populated successfully!',
                                indicator: 'green'
                            });
                        } else {
                            frappe.show_alert({
                                message: 'No UNLOCO details found for this code.',
                                indicator: 'orange'
                            });
                        }
                    }
                });
            }, 'Auto-Populate');
        }
    }
});

// Add form validation
frappe.ui.form.on('UNLOCO', {
    validate: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            // Validate UNLOCO code format
            if (frm.doc.unlocode.length !== 5) {
                frappe.msgprint({
                    title: 'Invalid UNLOCO Code',
                    message: 'UNLOCO code must be exactly 5 characters long',
                    indicator: 'red'
                });
                frappe.validated = false;
            }
        }
    }
});
