// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Job', {
    refresh: function(frm) {
        // Add Create Sales Invoice button when job is submitted and has legs
        if (frm.doc.docstatus === 1 && frm.doc.legs && frm.doc.legs.length > 0) {
            frm.add_custom_button(__('Create Sales Invoice'), function() {
                frappe.confirm(
                    __('Are you sure you want to create a Sales Invoice for this Transport Job?'),
                    function() {
                        frappe.call({
                            method: 'logistics.transport.doctype.transport_job.transport_job.create_sales_invoice',
                            args: {
                                job_name: frm.doc.name
                            },
                            callback: function(r) {
                                if (r.message && r.message.ok) {
                                    frappe.msgprint({
                                        title: __('Success'),
                                        message: r.message.message,
                                        indicator: 'green'
                                    });
                                    
                                    // Refresh the form to show updated data
                                    frm.reload_doc();
                                    
                                    // Open the created Sales Invoice
                                    if (r.message.sales_invoice) {
                                        frappe.set_route('Form', 'Sales Invoice', r.message.sales_invoice);
                                    }
                                } else {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        message: r.message || __('Failed to create Sales Invoice'),
                                        indicator: 'red'
                                    });
                                }
                            },
                            error: function(err) {
                                frappe.msgprint({
                                    title: __('Error'),
                                    message: err.message || __('Failed to create Sales Invoice'),
                                    indicator: 'red'
                                });
                            }
                        });
                    }
                );
            }, __('Actions'));
        }
    }
});