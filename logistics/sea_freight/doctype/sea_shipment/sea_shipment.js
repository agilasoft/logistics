// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Suppress "Sea Shipment X not found" when form is new/unsaved (e.g. child grid triggers API before save)
frappe.ui.form.on('Sea Shipment', {
    onload: function(frm) {
        // Suppress "Sea Shipment X not found" when form is new/unsaved
        if (frm.is_new() || frm.doc.__islocal) {
            if (!frappe._original_msgprint_ss) {
                frappe._original_msgprint_ss = frappe.msgprint;
            }
            frappe.msgprint = function(options) {
                const message = typeof options === 'string' ? options : (options && options.message || '');
                if (message && typeof message === 'string' &&
                    message.includes('Sea Shipment') &&
                    message.includes('not found')) {
                    return;
                }
                return frappe._original_msgprint_ss.apply(this, arguments);
            };
            frm.$wrapper.one('form-refresh', function() {
                if (!frm.is_new() && !frm.doc.__islocal && frappe._original_msgprint_ss) {
                    frappe.msgprint = frappe._original_msgprint_ss;
                }
            });
        }
        // Load default values from settings when creating new document
        if (frm.is_new()) {
            load_defaults_from_settings(frm);
        }
    },
    override_volume_weight: function(frm) {
        if (!frm.doc.override_volume_weight) {
            frm.call({
                method: 'aggregate_volume_from_packages_api',
                doc: frm.doc,
                callback: function(r) {
                    if (r && !r.exc && r.message && r.message.volume !== undefined) {
                        frm.set_value('volume', r.message.volume);
                    }
                }
            });
        }
    },
    
    refresh: function(frm) {
        // Populate Documents from Template
        if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
            frm.add_custom_button(__('Populate from Template'), function() {
                frappe.call({
                    method: 'logistics.document_management.api.populate_documents_from_template',
                    args: { doctype: 'Sea Shipment', docname: frm.doc.name },
                    callback: function(r) {
                        if (r.message && r.message.added !== undefined) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
                        }
                    }
                });
            }, __('Documents'));
        }

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
        
        // Add button to load charges from Sales Quote
        if (frm.doc.sales_quote && !frm.is_new()) {
            frm.add_custom_button(__('Load Charges from Sales Quote'), function() {
                load_charges_from_sales_quote(frm);
            }, __('Actions'));
        }

        // Create Transport Order / Inbound Order from Sea Shipment
        if (!frm.is_new()) {
            frm.add_custom_button(__('Transport Order'), function() {
                frappe.call({
                    method: 'logistics.utils.module_integration.create_transport_order_from_sea_shipment',
                    args: { sea_shipment_name: frm.doc.name },
                    callback: function(r) {
                        if (r.exc) return;
                        if (r.message && r.message.transport_order) {
                            frappe.msgprint(r.message.message);
                            setTimeout(function() {
                                frappe.set_route('Form', 'Transport Order', r.message.transport_order);
                            }, 100);
                        }
                    }
                });
            }, __('Create'));
            frm.add_custom_button(__('Inbound Order'), function() {
                frappe.call({
                    method: 'logistics.utils.module_integration.create_inbound_order_from_sea_shipment',
                    args: { sea_shipment_name: frm.doc.name },
                    callback: function(r) {
                        if (r.exc) return;
                        if (r.message && r.message.inbound_order) {
                            frappe.msgprint(r.message.message);
                            setTimeout(function() {
                                frappe.set_route('Form', 'Inbound Order', r.message.inbound_order);
                            }, 100);
                        }
                    }
                });
            }, __('Create'));
        }

        // Additional Charges: Get Additional Charges and Create Change Request
        if (!frm.is_new()) {
            frm.add_custom_button(__('Get Additional Charges'), function() {
                logistics_additional_charges_show_sales_quote_dialog(frm, 'Sea Shipment');
            }, __('Actions'));
            frm.add_custom_button(__('Create Change Request'), function() {
                frappe.call({
                    method: 'logistics.pricing_center.doctype.change_request.change_request.create_change_request',
                    args: { job_type: 'Sea Shipment', job_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message) frappe.set_route('Form', 'Change Request', r.message);
                    }
                });
            }, __('Actions'));
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

// Sea Freight Packages: ensure global volume-from-dimensions runs and header aggregates
frappe.ui.form.on('Sea Freight Packages', {
    volume: function(frm) {
        if (frm.doc && !frm.doc.override_volume_weight) {
            frm.call({
                method: 'aggregate_volume_from_packages_api',
                doc: frm.doc,
                callback: function(r) {
                    if (r && !r.exc && r.message) {
                        if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
                        if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
                    }
                }
            });
        }
    },
    weight: function(frm) {
        if (frm.doc && !frm.doc.override_volume_weight) {
            frm.call({
                method: 'aggregate_volume_from_packages_api',
                doc: frm.doc,
                callback: function(r) {
                    if (r && !r.exc && r.message) {
                        if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
                        if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
                    }
                }
            });
        }
    },
    length: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
    width: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
    height: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
    dimension_uom: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
    volume_uom: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); }
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

// Function to load charges from Sales Quote
function load_charges_from_sales_quote(frm) {
	if (!frm.doc.sales_quote) {
		frappe.msgprint({
			title: __("Error"),
			message: __("Sales Quote is not set for this Sea Shipment."),
			indicator: "red"
		});
		return;
	}
	
	frappe.confirm(
		__("This will replace all existing charges with charges from Sales Quote. Do you want to continue?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Loading charges from Sales Quote..."));
			
			frm.call({
				method: "populate_charges_from_sales_quote",
				callback: function(r) {
					frm.dashboard.clear_headline();
					
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __("Successfully loaded {0} charges from Sales Quote.", [r.message.charges_added]),
							indicator: "green"
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __("Error"),
							message: r.message && r.message.message ? r.message.message : __("Failed to load charges from Sales Quote."),
							indicator: "red"
						});
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to load charges from Sales Quote. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}
