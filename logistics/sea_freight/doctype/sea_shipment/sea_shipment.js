// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sea Shipment', {
    refresh: function(frm) {
        // Load milestone HTML if milestone_html field exists
        if (frm.fields_dict.milestone_html) {
            if (!frm._milestone_html_called) {
                frm._milestone_html_called = true;
                frm.call('get_milestone_html').then(r => {
                    if (r.message) {
                        const html = r.message || '';
                        const $wrapper = frm.get_field('milestone_html').$wrapper;
                        if ($wrapper) {
                            $wrapper.html(html);
                        }
                    }
                }).catch(err => {
                    console.error("Error calling get_milestone_html:", err);
                });
                
                // Reset flag after 2 seconds
                setTimeout(() => {
                    frm._milestone_html_called = false;
                }, 2000);
            }
        }
        
        frm.add_custom_button(__('Create Sales Invoice'), function() {
            const d = new frappe.ui.Dialog({
                title: 'Create Sales Invoice',
                fields: [
                    {
                        label: 'Invoice Type',
                        fieldname: 'invoice_type',
                        fieldtype: 'Link',
                        options: 'Invoice Type',
                        reqd: 1
                    },
                    {
                        label: 'Posting Date',
                        fieldname: 'posting_date',
                        fieldtype: 'Date',
                        default: frappe.datetime.get_today(),
                        reqd: 1
                    },
                    {
                        label: 'Customer',
                        fieldname: 'customer',
                        fieldtype: 'Link',
                        options: 'Customer',
                        default: frm.doc.local_customer,
                        reqd: 1
                    },
                    {
                        label: 'Job Number',
                        fieldname: 'job_number',
                        fieldtype: 'Data',
                        default: frm.doc.name,
                        read_only: 1
                    },
                    {
                        label: 'Tax Category',
                        fieldname: 'tax_category',
                        fieldtype: 'Link',
                        options: 'Tax Category'
                    }
                ],
                primary_action_label: 'Create',
                primary_action(values) {
                    frappe.call({
                        method: 'logistics.sea_freight.doctype.sea_shipment.sea_shipment.create_sales_invoice',
                        args: {
                            shipment_name: frm.doc.name,
                            posting_date: values.posting_date,
                            customer: values.customer,
                            tax_category: values.tax_category,
                            invoice_type: values.invoice_type
                        },
                        callback: function(r) {
                            if (r.message) {
                                frappe.msgprint(__('Sales Invoice Created: ') + r.message.name);
                                frappe.set_route('Form', 'Sales Invoice', r.message.name);
                            }
                            d.hide();
                        }
                    });
                }
            });

            d.show();
        }, __('Posting'));
    },
    shipper_address: function(frm) {
        if (frm.doc.shipper_address) {
            frappe.call({
                method: 'logistics.sea_freight.doctype.sea_freight_booking.api.get_formatted_address',
                args: {
                    address_name: frm.doc.shipper_address
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('shipper_address_display', r.message);
                    } else {
                        frm.set_value('shipper_address_display', '');
                    }
                }
            });
        } else {
            frm.set_value('shipper_address_display', '');
        }
    },
    weight: function(frm) {
        compute_chargeable(frm);
    },
    volume: function(frm) {
        compute_chargeable(frm);
    },
    direction: function(frm) {
        compute_chargeable(frm);
    },
    origin_port: function(frm) {
        // Refresh milestone view when origin port changes
        if (frm.fields_dict.milestone_html) {
            frm.call('get_milestone_html').then(r => {
                if (r.message) {
                    const $wrapper = frm.get_field('milestone_html').$wrapper;
                    if ($wrapper) {
                        $wrapper.html(r.message);
                    }
                }
            });
        }
    },
    destination_port: function(frm) {
        // Refresh milestone view when destination port changes
        if (frm.fields_dict.milestone_html) {
            frm.call('get_milestone_html').then(r => {
                if (r.message) {
                    const $wrapper = frm.get_field('milestone_html').$wrapper;
                    if ($wrapper) {
                        $wrapper.html(r.message);
                    }
                }
            });
        }
    }
});

// Function to refresh milestone view
function refresh_milestone_view(frm) {
    if (frm.fields_dict.milestone_html) {
        frm.call('get_milestone_html').then(r => {
            if (r.message) {
                const $wrapper = frm.get_field('milestone_html').$wrapper;
                if ($wrapper) {
                    $wrapper.html(r.message);
                }
            }
        }).catch(err => {
            console.error("Error refreshing milestone view:", err);
        });
    }
}

function compute_chargeable(frm) {
    const weight = frm.doc.weight || 0;
    const volume = frm.doc.volume || 0;
    const direction = frm.doc.direction || "";
    
    const volume_weight = direction === "Domestic"
        ? volume * 333
        : volume * 1000;

    frm.set_value('chargeable', Math.max(weight, volume_weight));
}
