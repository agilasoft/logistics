// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sea Shipment', {
    onload: function(frm) {
        // Load default values from settings when creating new document
        if (frm.is_new()) {
            load_defaults_from_settings(frm);
        }
    },
    
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

// Load default values from Sea Freight Settings
function load_defaults_from_settings(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Sea Freight Settings',
            name: 'Sea Freight Settings',
            fieldname: [
                'default_company', 'default_branch', 'default_cost_center', 'default_profit_center',
                'default_currency', 'default_incoterm', 'default_service_level',
                'default_origin_port', 'default_destination_port',
                'default_shipping_line', 'default_freight_agent'
            ]
        },
        callback: function(r) {
            if (r.message) {
                const settings = r.message;
                
                // Set accounting dimensions if not already set
                if (!frm.doc.company && settings.default_company) {
                    frm.set_value('company', settings.default_company);
                }
                if (!frm.doc.branch && settings.default_branch) {
                    frm.set_value('branch', settings.default_branch);
                }
                if (!frm.doc.cost_center && settings.default_cost_center) {
                    frm.set_value('cost_center', settings.default_cost_center);
                }
                if (!frm.doc.profit_center && settings.default_profit_center) {
                    frm.set_value('profit_center', settings.default_profit_center);
                }
                
                // Set currency and incoterm
                if (!frm.doc.currency && settings.default_currency) {
                    frm.set_value('currency', settings.default_currency);
                }
                if (!frm.doc.incoterm && settings.default_incoterm) {
                    frm.set_value('incoterm', settings.default_incoterm);
                }
                if (!frm.doc.service_level && settings.default_service_level) {
                    frm.set_value('service_level', settings.default_service_level);
                }
                
                // Set location defaults
                if (!frm.doc.origin_port && settings.default_origin_port) {
                    frm.set_value('origin_port', settings.default_origin_port);
                }
                if (!frm.doc.destination_port && settings.default_destination_port) {
                    frm.set_value('destination_port', settings.default_destination_port);
                }
                
                // Set business defaults
                if (!frm.doc.shipping_line && settings.default_shipping_line) {
                    frm.set_value('shipping_line', settings.default_shipping_line);
                }
                if (!frm.doc.freight_agent && settings.default_freight_agent) {
                    frm.set_value('freight_agent', settings.default_freight_agent);
                }
            }
        }
    });
}

function compute_chargeable(frm) {
    const weight = frm.doc.weight || 0;
    const volume = frm.doc.volume || 0;
    
    // Get settings for volume to weight factor
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Sea Freight Settings',
            name: 'Sea Freight Settings',
            fieldname: ['volume_to_weight_factor', 'chargeable_weight_calculation']
        },
        callback: function(r) {
            if (r.message) {
                const volume_factor = r.message.volume_to_weight_factor || 1000;
                const calculation_method = r.message.chargeable_weight_calculation || 'Higher of Both';
                const direction = frm.doc.direction || "";
                
                // Fallback to direction-based if settings not available
                const factor = r.message.volume_to_weight_factor 
                    ? volume_factor 
                    : (direction === "Domestic" ? 333 : 1000);
                
                const volume_weight = volume * factor;
                
                let chargeable;
                if (calculation_method === "Actual Weight") {
                    chargeable = weight;
                } else if (calculation_method === "Volume Weight") {
                    chargeable = volume_weight;
                } else {  // Higher of Both (default)
                    chargeable = Math.max(weight, volume_weight);
                }
                
                frm.set_value('chargeable', chargeable);
            } else {
                // Fallback calculation
                const direction = frm.doc.direction || "";
                const volume_weight = direction === "Domestic"
                    ? volume * 333
                    : volume * 1000;

                frm.set_value('chargeable', Math.max(weight, volume_weight));
            }
        }
    });
}
