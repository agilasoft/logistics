// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Rate', {
    vehicle_type: function(frm) {
        // Check if the selected vehicle type is containerized
        if (frm.doc.vehicle_type) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Vehicle Type',
                    name: frm.doc.vehicle_type,
                    fieldname: 'containerized'
                },
                callback: function(r) {
                    if (r.message && r.message.containerized) {
                        // Show container_type field
                        frm.set_df_property('container_type', 'hidden', 0);
                    } else {
                        // Hide container_type field and clear its value
                        frm.set_df_property('container_type', 'hidden', 1);
                        frm.set_value('container_type', '');
                    }
                }
            });
        } else {
            // Hide container_type field when no vehicle type is selected
            frm.set_df_property('container_type', 'hidden', 1);
            frm.set_value('container_type', '');
        }
    }
});
