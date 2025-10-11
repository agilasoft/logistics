// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tariff', {
    refresh: function(frm) {
        // Add custom buttons
        frm.add_custom_button(__('Calculate Rate'), function() {
            show_rate_calculator(frm);
        });
        
        frm.add_custom_button(__('Copy Rates'), function() {
            show_copy_rates_dialog(frm);
        });
        
        frm.add_custom_button(__('Deactivate Expired'), function() {
            deactivate_expired_rates(frm);
        });
        
        frm.add_custom_button(__('Activate Future'), function() {
            activate_future_rates(frm);
        });
        
        // Add rate summary
        if (frm.doc.name) {
            show_rate_summary(frm);
        }
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

// Rate calculation dialog
function show_rate_calculator(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Rate Calculator'),
        fields: [
            {
                'fieldtype': 'Select',
                'fieldname': 'service_type',
                'label': __('Service Type'),
                'options': 'Air Freight\nSea Freight\nTransport\nCustoms\nWarehousing',
                'reqd': 1
            },
            {
                'fieldtype': 'Select',
                'fieldname': 'calculation_method',
                'label': __('Calculation Method'),
                'options': 'Per Volume\nPer Weight\nPer Package\nPer Shipment\nFixed Amount\nPercentage\nPer TEU\nPer Container Type\nFixed Plus Per Unit\nMinimum Charge\nMaximum Charge\nPer Distance\nPer Pallet\nPer Trip (FTL)\nPer Value\nPer Day\nPer Month',
                'reqd': 1
            },
            {
                'fieldtype': 'Currency',
                'fieldname': 'rate_value',
                'label': __('Rate Value'),
                'reqd': 1
            },
            {
                'fieldtype': 'Float',
                'fieldname': 'quantity',
                'label': __('Quantity')
            },
            {
                'fieldtype': 'Float',
                'fieldname': 'weight',
                'label': __('Weight')
            },
            {
                'fieldtype': 'Float',
                'fieldname': 'volume',
                'label': __('Volume')
            },
            {
                'fieldtype': 'Float',
                'fieldname': 'distance',
                'label': __('Distance (KM)')
            },
            {
                'fieldtype': 'Currency',
                'fieldname': 'value',
                'label': __('Value')
            },
            {
                'fieldtype': 'Int',
                'fieldname': 'days',
                'label': __('Days')
            },
            {
                'fieldtype': 'Int',
                'fieldname': 'months',
                'label': __('Months')
            },
            {
                'fieldtype': 'Select',
                'fieldname': 'container_type',
                'label': __('Container Type'),
                'options': '20ft\n40ft\n45ft\nLCL'
            },
            {
                'fieldtype': 'Data',
                'fieldname': 'vehicle_type',
                'label': __('Vehicle Type')
            },
            {
                'fieldtype': 'Data',
                'fieldname': 'commodity_code',
                'label': __('Commodity Code')
            },
            {
                'fieldtype': 'Select',
                'fieldname': 'warehouse_type',
                'label': __('Warehouse Type'),
                'options': 'General\nCold Storage\nHazardous\nBonded\nFree Trade Zone'
            }
        ],
        primary_action_label: __('Calculate'),
        primary_action: function(values) {
            calculate_rate(frm, values);
        }
    });
    
    d.show();
}

function calculate_rate(frm, values) {
    frappe.call({
        method: 'logistics.pricing_center.doctype.tariff.tariff.calculate_tariff_rate',
        args: {
            tariff_name: frm.doc.name,
            service_type: values.service_type,
            calculation_method: values.calculation_method,
            rate_value: values.rate_value,
            quantity: values.quantity || 0,
            weight: values.weight || 0,
            volume: values.volume || 0,
            distance: values.distance || 0,
            value: values.value || 0,
            days: values.days || 0,
            months: values.months || 0,
            container_type: values.container_type,
            vehicle_type: values.vehicle_type,
            commodity_code: values.commodity_code,
            warehouse_type: values.warehouse_type
        },
        callback: function(r) {
            if (r.message) {
                show_calculation_result(r.message);
            }
        }
    });
}

function show_calculation_result(result) {
    let d = new frappe.ui.Dialog({
        title: __('Rate Calculation Result'),
        fields: [
            {
                'fieldtype': 'HTML',
                'fieldname': 'result_html',
                'options': `
                    <div style="padding: 20px;">
                        <h4>Calculation Result</h4>
                        <table class="table table-bordered">
                            <tr>
                                <td><strong>Method:</strong></td>
                                <td>${result.method}</td>
                            </tr>
                            <tr>
                                <td><strong>Calculation:</strong></td>
                                <td>${result.calculation}</td>
                            </tr>
                            <tr>
                                <td><strong>Amount:</strong></td>
                                <td><strong>${result.currency} ${result.amount}</strong></td>
                            </tr>
                            <tr>
                                <td><strong>Base Rate:</strong></td>
                                <td>${result.base_rate}</td>
                            </tr>
                            <tr>
                                <td><strong>Quantity:</strong></td>
                                <td>${result.quantity} ${result.unit}</td>
                            </tr>
                        </table>
                    </div>
                `
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            d.hide();
        }
    });
    
    d.show();
}

// Copy rates dialog
function show_copy_rates_dialog(frm) {
    frappe.prompt([
        {
            'fieldtype': 'Link',
            'fieldname': 'source_tariff',
            'label': __('Source Tariff'),
            'options': 'Tariff',
            'reqd': 1
        },
        {
            'fieldtype': 'MultiSelect',
            'fieldname': 'service_types',
            'label': __('Service Types'),
            'options': 'Air Freight\nSea Freight\nTransport\nCustoms\nWarehousing',
            'default': ['Air Freight', 'Sea Freight', 'Transport', 'Customs', 'Warehousing']
        }
    ], function(values) {
        frappe.call({
            method: 'logistics.pricing_center.doctype.tariff.tariff.copy_rates_from_tariff',
            args: {
                target_tariff: frm.doc.name,
                source_tariff: values.source_tariff,
                service_types: values.service_types
            },
            callback: function(r) {
                if (r.message.status === 'success') {
                    frappe.msgprint(__('Rates copied successfully'));
                    frm.reload_doc();
                }
            }
        });
    }, __('Copy Rates'), __('Copy'));
}

// Deactivate expired rates
function deactivate_expired_rates(frm) {
    frappe.confirm(__('Are you sure you want to deactivate all expired rates?'), function() {
        frappe.call({
            method: 'logistics.pricing_center.doctype.tariff.tariff.deactivate_expired_rates',
            args: {
                tariff_name: frm.doc.name
            },
            callback: function(r) {
                if (r.message.status === 'success') {
                    frappe.msgprint(__('Expired rates deactivated'));
                    frm.reload_doc();
                }
            }
        });
    });
}

// Activate future rates
function activate_future_rates(frm) {
    frappe.confirm(__('Are you sure you want to activate all future rates?'), function() {
        frappe.call({
            method: 'logistics.pricing_center.doctype.tariff.tariff.activate_future_rates',
            args: {
                tariff_name: frm.doc.name
            },
            callback: function(r) {
                if (r.message.status === 'success') {
                    frappe.msgprint(__('Future rates activated'));
                    frm.reload_doc();
                }
            }
        });
    });
}

// Show rate summary
function show_rate_summary(frm) {
    frappe.call({
        method: 'logistics.pricing_center.doctype.tariff.tariff.get_tariff_summary',
        args: {
            tariff_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let summary_html = '<div style="padding: 10px;"><h5>Rate Summary</h5><table class="table table-sm">';
                summary_html += '<tr><th>Service Type</th><th>Total Rates</th><th>Active Rates</th><th>Methods</th></tr>';
                
                for (let service in r.message) {
                    let data = r.message[service];
                    summary_html += `<tr>
                        <td>${service.charAt(0).toUpperCase() + service.slice(1)}</td>
                        <td>${data.total_rates}</td>
                        <td>${data.active_rates}</td>
                        <td>${data.calculation_methods.join(', ')}</td>
                    </tr>`;
                }
                
                summary_html += '</table></div>';
                
                frm.dashboard.add_section(
                    frappe.render_template(summary_html, {}),
                    __('Rate Summary')
                );
            }
        }
    });
}

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