function get_unloco_populate_payload(message) {
    if (!message) {
        return null;
    }
    if (message.status === 'error') {
        return null;
    }
    if (message.data && typeof message.data === 'object') {
        return message.data;
    }
    if (message.status === 'success' || message.status === 'warning') {
        return null;
    }
    if (message.latitude !== undefined || message.longitude !== undefined || message.location_name !== undefined) {
        return message;
    }
    return null;
}

function apply_unloco_populate_to_form(frm, r) {
    const msg = r.message;
    const data = get_unloco_populate_payload(msg);
    if (data) {
        Object.keys(data).forEach(function (key) {
            if (data[key] !== null && data[key] !== undefined) {
                frm.set_value(key, data[key]);
            }
        });
        frm.refresh_fields();
    }
    if (msg && msg.status === 'success') {
        frappe.show_alert({
            message: __('UNLOCO details populated successfully!'),
            indicator: 'green'
        });
    } else if (msg && msg.status === 'warning') {
        frappe.show_alert({
            message: msg.message || __('Limited UNLOCO data applied.'),
            indicator: 'orange'
        });
    } else if (msg && msg.status === 'error') {
        frappe.show_alert({
            message: msg.message || __('Could not populate UNLOCO.'),
            indicator: 'red'
        });
    } else if (data && Object.keys(data).length) {
        frappe.show_alert({
            message: __('UNLOCO details populated successfully!'),
            indicator: 'green'
        });
    }
}

// Auto-populate UNLOCO details when UNLOCO code is entered
frappe.ui.form.on('UNLOCO', {
    unlocode: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            frappe.call({
                method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                args: {
                    unlocode: frm.doc.unlocode,
                    refresh_external: 1,
                },
                callback: function(r) {
                    apply_unloco_populate_to_form(frm, r);
                }
            });
        }
    },

    auto_populate: function(frm) {
        if (frm.doc.auto_populate && frm.doc.unlocode) {
            frm.trigger('unlocode');
        }
    }
});

frappe.ui.form.on('UNLOCO', {
    refresh: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            frm.add_custom_button('Populate UNLOCO Details', function() {
                frappe.call({
                    method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                    args: {
                        unlocode: frm.doc.unlocode,
                        refresh_external: 1,
                    },
                    callback: function(r) {
                        apply_unloco_populate_to_form(frm, r);
                    }
                });
            }, 'Auto-Populate');
        }
    }
});

frappe.ui.form.on('UNLOCO', {
    validate: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
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
